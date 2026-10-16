"""Admin commands for Daily Algebra. Run from the project folder:

    python manage.py players
    python manage.py today "Name"
    python manage.py reset-round "Name" 2
    python manage.py reset-question "Name" 1 3
    python manage.py rename "Old name" "New name"

With Docker, run the same commands inside the container:

    docker compose exec algebra python manage.py players

Changes apply to the current game day unless --day YYYY-MM-DD is given. The app can stay running.
"""
import argparse
import sqlite3
import sys

import app as A
import questions as Q

N = Q.ROUND_SIZE


def connect():
    con = sqlite3.connect(A.DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def find_player(con, name):
    row = con.execute("SELECT id, name FROM users WHERE name=?", (name,)).fetchone()
    if not row:
        names = ", ".join(r["name"] for r in con.execute("SELECT name FROM users ORDER BY name"))
        sys.exit(f'No player named "{name}". Players: {names or "none yet"}.')
    return row


def label(idx):
    return "Bonus" if idx == Q.BONUS_IDX else f"Round {idx // N + 1}, question {idx % N + 1}"


def delete(con, player, day, idxs, what):
    """Delete the given attempts. The bonus goes too: it was only unlocked because every earlier
    answer was correct, so it can't stand once one of them is undone."""
    idxs = sorted(set(idxs) | {Q.BONUS_IDX})
    rows = con.execute(f"SELECT idx, status, points FROM attempts WHERE user_id=? AND day=? "
                       f"AND idx IN ({','.join('?' * len(idxs))})", (player["id"], day, *idxs)).fetchall()
    if not rows:
        sys.exit(f"Nothing to reset: {player['name']} hasn't answered {what} on {day}.")
    con.executemany("DELETE FROM attempts WHERE user_id=? AND day=? AND idx=?",
                    [(player["id"], day, r["idx"]) for r in rows])
    con.commit()
    for r in rows:
        print(f"  reset {label(r['idx'])} (was {r['status']}, {r['points']} pts)")
    lost = sum(r["points"] for r in rows)
    print(f"{player['name']}: {len(rows)} answer(s) reset for {day}" + (f", {lost} points removed." if lost else "."))
    print("They get the same questions back. Reload the page to see them.")


def cmd_players(con, args):
    rows = con.execute("""SELECT u.name, COALESCE(SUM(a.points),0) AS total,
                                 COALESCE(SUM(CASE WHEN a.day=? THEN a.points END),0) AS today
                          FROM users u LEFT JOIN attempts a ON a.user_id=u.id
                          GROUP BY u.id ORDER BY total DESC, u.name""", (args.day,)).fetchall()
    if not rows:
        print("No players yet.")
    for r in rows:
        print(f"{r['name']:<32} {r['today']:>5} today {r['total']:>7} all time")


def cmd_today(con, args):
    player = find_player(con, args.name)
    rows = con.execute("SELECT idx, topic, status, given, points FROM attempts WHERE user_id=? AND day=? "
                       "ORDER BY idx", (player["id"], args.day)).fetchall()
    print(f"{player['name']} on {args.day}:")
    if not rows:
        print("  nothing answered yet")
    for r in rows:
        print(f"  {label(r['idx']):<22} {r['status']:<8} {r['points']:>4} pts  {r['topic']}"
              + (f"  (answered {r['given']})" if r["status"] == "wrong" else ""))


def cmd_reset_round(con, args):
    if not 1 <= args.round <= Q.ROUNDS:
        sys.exit(f"Round must be 1 to {Q.ROUNDS}.")
    start = (args.round - 1) * N
    delete(con, find_player(con, args.name), args.day, range(start, start + N), f"round {args.round}")


def cmd_reset_question(con, args):
    if not 1 <= args.round <= Q.ROUNDS or not 1 <= args.question <= N:
        sys.exit(f"Round must be 1 to {Q.ROUNDS} and question 1 to {N}.")
    idx = (args.round - 1) * N + args.question - 1
    delete(con, find_player(con, args.name), args.day, [idx], label(idx).lower())


def cmd_rename(con, args):
    new = " ".join(args.new.split())
    if not A.NAME_RE.match(new):
        sys.exit("Use 1-32 letters, numbers, spaces, or . ' - in the new name.")
    player = find_player(con, args.old)
    try:
        con.execute("UPDATE users SET name=? WHERE id=?", (new, player["id"]))
        con.commit()
    except sqlite3.IntegrityError:
        sys.exit(f'There is already a player named "{new}".')
    print(f'Renamed "{player["name"]}" to "{new}". Points and history stay with them.')


def main():
    ap = argparse.ArgumentParser(description="Daily Algebra admin commands.")
    ap.add_argument("--day", default=A.today(), help="game day as YYYY-MM-DD (default: the current one)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("players", help="list players and points")
    p = sub.add_parser("today", help="show a player's answers for the day")
    p.add_argument("name")
    p = sub.add_parser("reset-round", help="reset a player's whole round for the day")
    p.add_argument("name")
    p.add_argument("round", type=int)
    p = sub.add_parser("reset-question", help="reset one of a player's answers for the day")
    p.add_argument("name")
    p.add_argument("round", type=int)
    p.add_argument("question", type=int)
    p = sub.add_parser("rename", help="rename a player")
    p.add_argument("old")
    p.add_argument("new")
    args = ap.parse_args()
    with connect() as con:
        globals()["cmd_" + args.cmd.replace("-", "_")](con, args)


if __name__ == "__main__":
    main()
