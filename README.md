# Daily Algebra

Self-hosted Algebra 1 practice for the LAN. Flask + SQLite, no external assets
(works with no internet once the image is built).

## Run

    docker compose up -d --build

Then browse to `http://<host-ip>:8080`. If the host runs firewalld:

    sudo firewall-cmd --permanent --add-port=8080/tcp && sudo firewall-cmd --reload

Without Docker: `pip install -r requirements.txt && DATA_DIR=./data python app.py`. Both ways
use the same `data/` folder, so you can switch between them without losing scores; just don't
run both at once.

## How it works

- Each day is two rounds of 5 questions, 10 max. Finishing round 1 offers "Play again"
  for round 2. The day resets at midnight in `TZ` (UTC by default).
- Every round has at least one fundamentals question and one word problem. Topics don't
  repeat within a day. There are 20 topic generators:
  - Fundamentals (always multiple choice): order of operations, integer operations,
    naming the property, like terms, translating words to expressions, fraction operations.
  - Word problems: rate, consecutive integers, distance.
  - Core: two-step equations, variables on both sides, distributive property,
    inequalities, slope, slope-intercept form, evaluating expressions, combining like
    terms, exponent rules, factoring trinomials, systems.
- Questions are regenerated from a seed keyed with the server's secret plus (player, date),
  so the server can grade without storing them. Answers and solutions never reach the
  browser until the question is answered or skipped.
- One attempt per question. Correct = full points; wrong = 0. The first skip in each round
  earns half points; later skips earn 0. Wrong or skipped questions unlock the
  step-by-step walkthrough. For fundamentals, a wrong answer shows the explanation right
  away, including why the picked choice is wrong.
- Leaderboard with stars, on the sign-in screen and after each round. Stars roll up:
  silver = 100 points, 3 silver = 1 gold (300), 3 gold = 1 platinum (900),
  3 platinum = 1 diamond (2,700).
- Numeric answers accept `7`, `-2.5`, `3/4`, `1 1/2`, `x = 4`, `- 4`, `$12`. Rounded decimals
  within 0.01 are accepted only for answers with no exact decimal, like 2/3.

## Notes

- Players are name-only — no passwords. Fine for a home LAN; don't expose it to
  the internet as-is.
- Data lives in the project's `data/` folder (`algebra.db`, plus the session key), mounted at
  `/data` in the container. Back up that folder to keep players and scores.
  Changing `SECRET_KEY` or deleting the key file logs everyone out and reshuffles questions.
- Add a topic: write a generator in `questions.py` returning `inp(...)` or `mc(...)` and
  add it to `FUNDAMENTALS`, `WORD_PROBLEMS`, or the core part of `GENERATORS`.
  `mc` distractors can be `(choice, mistake)` pairs to explain a wrong pick.
- Reset a player's day: `DELETE FROM attempts WHERE user_id=? AND day='YYYY-MM-DD';`
- Delete a player: `DELETE FROM users WHERE id=?;` The app enables foreign keys so their
  attempts cascade, but the `sqlite3` CLI doesn't by default. Any leftover attempts are
  cleaned up the next time the app starts.
- Changing a generator, the generator lists, `ROUND_SIZE`/`ROUNDS`, `SHARED_QUESTIONS`, the
  secret key, or the Python version changes the questions already issued for today. Deploy
  those changes right after the daily reset, before anyone has started.
# MattLab
