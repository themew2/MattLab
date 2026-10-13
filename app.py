import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime, time, timedelta
from functools import lru_cache, wraps
from zoneinfo import ZoneInfo

from flask import Flask, g, jsonify, request, send_from_directory, session

import questions as Q

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "algebra.db")
TZ = ZoneInfo(os.environ.get("TZ", "UTC"))
POINTS = int(os.environ.get("POINTS_PER_CORRECT", 10))
HALF_SKIP = POINTS // 2  # the first skip in each round earns this; later skips earn 0
# stars roll up like coins: 3 silvers make a gold, 3 golds a platinum, 3 platinums a diamond
STAR_LEVELS = [("diamond", 2700), ("platinum", 900), ("gold", 300), ("silver", 100)]
SHARED = os.environ.get("SHARED_QUESTIONS", "0") == "1"
NAME_RE = re.compile(r"^[\w .'-]{1,32}$")


def _secret_key():
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    path = os.path.join(DATA_DIR, "secret_key")
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
        os.chmod(path, 0o600)
    with open(path) as f:
        return f.read().strip()


app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = _secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=365),
)


def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS attempts (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            day TEXT NOT NULL,
            idx INTEGER NOT NULL,
            topic TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('correct','wrong','skipped')),
            given TEXT,
            points INTEGER NOT NULL DEFAULT 0,
            ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, day, idx)
        );
        -- users deleted from the sqlite3 CLI (where foreign keys are off) leave attempts behind,
        -- and SQLite can hand a deleted id to the next new user
        DELETE FROM attempts WHERE user_id NOT IN (SELECT id FROM users);
    """)
    con.close()


_init_db()


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")  # per-connection; makes ON DELETE CASCADE work
    return g.db


@app.teardown_appcontext
def _close_db(_):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def today():
    return datetime.now(TZ).date().isoformat()


def require_user(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        uid = session.get("uid")
        user = uid and db().execute("SELECT id, name FROM users WHERE id=?", (uid,)).fetchone()
        if not user:
            session.clear()
            return jsonify(error="Sign in to continue."), 401
        g.user = user
        return fn(*a, **kw)
    return wrapper


def next_reset():
    now = datetime.now(TZ)
    return datetime.combine(now.date() + timedelta(days=1), time(), TZ).isoformat()


def stars(points):
    out = {}
    for level, size in STAR_LEVELS:
        out[level], points = divmod(points, size)
    return out


@lru_cache(maxsize=256)
def _question_set(owner, day):
    # keyed with the secret so nobody can regenerate a player's questions from the source
    seed = hmac.new(app.secret_key.encode(), f"{owner}:{day}".encode(), hashlib.sha256).hexdigest()
    return Q.daily_questions(seed)


def todays_set(uid, day):
    return _question_set("all" if SHARED else uid, day)


def day_attempts(uid, day):
    return {r["idx"]: r for r in db().execute(
        "SELECT * FROM attempts WHERE user_id=? AND day=?", (uid, day))}


def unlocked(atts):
    """How many of today's questions are playable: the next round opens once every question in
    the round before it is answered or skipped."""
    n = Q.ROUND_SIZE
    for r in range(Q.ROUNDS):
        if any(i not in atts for i in range(r * n, (r + 1) * n)):
            return (r + 1) * n
    return Q.ROUNDS * n


def stale_day(day):
    """The browser sends the day its questions came from. Without this, an answer sent just after
    midnight would be graded against (and recorded on) the new day's question at the same index."""
    if day != today():
        return jsonify(error="A new day has started. Loading today's questions.", stale=True), 409
    return None


def get_question(idx, day):
    """Returns (question, today's attempts by idx), or (None, error response)."""
    qs = todays_set(g.user["id"], day)
    if not isinstance(idx, int) or isinstance(idx, bool) or not 0 <= idx < len(qs):
        return None, (jsonify(error="That question isn't in today's set."), 404)
    atts = day_attempts(g.user["id"], day)
    if idx >= unlocked(atts):
        return None, (jsonify(error="Finish this round first."), 403)
    return qs[idx], atts


def attempt(uid, day, idx):
    return db().execute("SELECT * FROM attempts WHERE user_id=? AND day=? AND idx=?",
                        (uid, day, idx)).fetchone()


def totals(uid):
    row = db().execute("""
        SELECT COALESCE(SUM(points),0) AS total,
               COALESCE(SUM(CASE WHEN day=? THEN points END),0) AS today,
               COUNT(DISTINCT CASE WHEN status='correct' THEN day||':'||idx END) AS correct_all
        FROM attempts WHERE user_id=?""", (today(), uid)).fetchone()
    return {"total": row["total"], "today": row["today"], "correct_all": row["correct_all"],
            "stars": stars(row["total"])}


def public(i, q, att):
    d = {"idx": i, "topic": q["topic"], "kind": q["kind"], "prompt": q["prompt"], "hint": q.get("hint"),
         "category": q["category"]}
    if q["kind"] == "mc":
        d["choices"] = q["choices"]
    if att:
        d.update(status=att["status"], given=att["given"], points=att["points"],
                 correct_answer=q["answer_text"], step_count=len(q["steps"]),
                 # fundamentals explain a wrong answer right away instead of waiting for "Walk me through it"
                 auto_explain=q["category"] == "fundamentals" and att["status"] == "wrong")
        if att["status"] == "wrong":
            d["mistake"] = q.get("mistakes", {}).get(att["given"])
    else:
        d["status"] = "open"
    return d


def record(day, idx, q, status, given, pts):
    try:
        db().execute("INSERT INTO attempts (user_id, day, idx, topic, status, given, points) "
                     "VALUES (?,?,?,?,?,?,?)",
                     (g.user["id"], day, idx, q["topic"], status, given, pts))
        db().commit()
        return True
    except sqlite3.IntegrityError:
        return False


# ---------------------------------------------------------------- routes

@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/players")
def players():
    rows = db().execute("""
        SELECT u.name, COALESCE(SUM(a.points),0) AS total,
               COALESCE(SUM(CASE WHEN a.day=? THEN a.points END),0) AS today
        FROM users u LEFT JOIN attempts a ON a.user_id=u.id
        GROUP BY u.id ORDER BY total DESC, u.name""", (today(),)).fetchall()
    return jsonify([{**r, "stars": stars(r["total"])} for r in map(dict, rows)])


@app.post("/api/login")
def login():
    name = " ".join(((request.get_json(silent=True) or {}).get("name") or "").split())
    if not NAME_RE.match(name):
        return jsonify(error="Use 1–32 letters, numbers, spaces, or . ' - in your name."), 400
    con = db()
    con.execute("INSERT OR IGNORE INTO users (name) VALUES (?)", (name,))
    con.commit()
    user = con.execute("SELECT id, name FROM users WHERE name=?", (name,)).fetchone()
    session.clear()
    session.permanent = True
    session["uid"] = user["id"]
    return jsonify(name=user["name"])


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/today")
@require_user
def today_view():
    day = today()
    qs = todays_set(g.user["id"], day)
    atts = day_attempts(g.user["id"], day)
    return jsonify(name=g.user["name"], day=day, points_per_correct=POINTS, half_skip=HALF_SKIP,
                   round_size=Q.ROUND_SIZE, rounds=Q.ROUNDS, next_reset=next_reset(),
                   questions=[public(i, q, atts.get(i)) for i, q in enumerate(qs[:unlocked(atts)])],
                   totals=totals(g.user["id"]))


@app.post("/api/answer")
@require_user
def answer():
    body = request.get_json(silent=True) or {}
    day, idx = body.get("day"), body.get("idx")
    if (resp := stale_day(day)):
        return resp
    q, atts = get_question(idx, day)
    if q is None:
        return atts
    if idx in atts:
        return jsonify(error="You already finished this question."), 409

    if q["kind"] == "mc":
        choice = body.get("choice")
        if not isinstance(choice, int) or isinstance(choice, bool) or not 0 <= choice < len(q["choices"]):
            return jsonify(error="Pick one of the choices."), 400
        correct = choice == q["answer_index"]
        given = q["choices"][choice]
    else:
        given = str(body.get("answer") or "").strip()[:64]
        correct = Q.check_input(q, given)
        if correct is None:
            return jsonify(error="Enter a number, like 7, -2.5, or 3/4."), 400

    pts = POINTS if correct else 0
    if not record(day, idx, q, "correct" if correct else "wrong", given, pts):
        return jsonify(error="You already finished this question."), 409
    return jsonify(question=public(idx, q, attempt(g.user["id"], day, idx)), totals=totals(g.user["id"]))


@app.post("/api/skip")
@require_user
def skip():
    body = request.get_json(silent=True) or {}
    day, idx = body.get("day"), body.get("idx")
    if (resp := stale_day(day)):
        return resp
    q, atts = get_question(idx, day)
    if q is None:
        return atts
    start = idx - idx % Q.ROUND_SIZE
    used = any(atts[i]["status"] == "skipped" and atts[i]["points"] > 0
               for i in range(start, start + Q.ROUND_SIZE) if i in atts)
    if not record(day, idx, q, "skipped", None, 0 if used else HALF_SKIP):
        return jsonify(error="You already finished this question."), 409
    return jsonify(question=public(idx, q, attempt(g.user["id"], day, idx)), totals=totals(g.user["id"]))


@app.get("/api/explain/<int:idx>")
@require_user
def explain(idx):
    day = request.args.get("day")
    if (resp := stale_day(day)):
        return resp
    q, atts = get_question(idx, day)
    if q is None:
        return atts
    if idx not in atts:
        return jsonify(error="Answer or skip the question to see how it's solved."), 403
    return jsonify(steps=q["steps"], correct_answer=q["answer_text"])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
