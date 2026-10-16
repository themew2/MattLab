# To-do

1. **More screenshots for the README** (optional). The sign-in screen is in
   (`docs/MattLab_1.png`); retake it now that "Switch player" no longer shows there. Could add
   a question with a geometry figure.

## Done

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
