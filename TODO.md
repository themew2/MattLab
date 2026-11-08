# To-do

1. **More screenshots for the README** (optional). The sign-in screen is in
   (`docs/MattLab_1.png`); retake it now that "Switch player" no longer shows there. Could add
   a question with a geometry figure.

## Done

- [x] Domain and range, positive and negative slope, and horizontal and vertical lines
      (fundamentals, several with a coordinate-grid picture). Drawn 3x as often as older
      topics (`FOCUS` in questions.py).

- [x] Separate install instructions for Linux, Mac, and Windows (Docker and plain Python),
      plus finding the IP and opening the firewall on each.
- [x] Troubleshooting section, with `manage.py` commands to reset a player's round, reset a
      wrong question, rename a player, and see a player's answers.
- [x] Screenshot of the app in the README.
- [x] Daily reset at 4pm UTC (`RESET_HOUR_UTC` in docker-compose.yml). New questions arrive
      at noon EDT / 11am EST.
- [x] 100-point geometry bonus after a perfect day (all 10 correct, no skips). One try, no
      skip, doesn't count toward the 10. Identify-the-concept multiple choice with a
      server-drawn picture: triangles (by sides and by angles), angles, angle pairs,
      quadrilaterals, polygons, parts of a circle, lines, and solids. A wrong answer shows
      the explanation right away.
- [x] Temperature conversion word problems (Celsius to Fahrenheit and back). Each question
      states the formula, in either the 9/5 or the 1.8 form.
- [x] "Names for x and y" fundamentals questions, covering the other names for x and y:

      | x                       | y                     | Where you'll see it                              |
      |-------------------------|-----------------------|--------------------------------------------------|
      | x-coordinate            | y-coordinate          | Plotting points, ordered pairs (x, y)            |
      | Horizontal (left/right) | Vertical (up/down)    | Describing direction on the graph                |
      | Abscissa                | Ordinate              | Formal or older math texts                       |
      | Input                   | Output                | Functions                                        |
      | Independent variable    | Dependent variable    | Science and data, where y depends on x           |
      | Domain values           | Range values          | Sets of all possible x's and y's in a function   |
      | Run                     | Rise                  | Slope (rise over run)                            |
- [x] Each attempt saves the question as the player saw it (prompt, choices, answer,
      steps) in `attempts.question`. The blitz uses this copy; the day screens still
      rebuild questions from the seed.
- [x] Question Blitz after the 2 rounds. Offered 25% of the time on a day with a miss
      (wrong or skipped), once the player has 5+ missed questions saved. Retries missed
      questions, with the explanation available before answering, 10 points each; a right answer takes the question
      off the missed list. Ends at the first miss or when the list is empty. Misses from
      before questions were saved don't count. Never on a bonus day.
