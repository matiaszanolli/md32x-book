# Developer credits shown on screen

Captured 7 October 2026 for the developer columns of `src/appendices/sample-code.md`. Every frame here comes from the game's attract loop, reached with no input at all: power on and wait. Frame numbers count from power-on in the headless PicoDrive frontend (`notes/games/tools/README.md`, "Running a game headless"), with the VRD project's `picodrive_libretro.so`:

```sh
mkdir DUMP && VRD_VIDEO_DUMP_DIR=$PWD/DUMP VRD_VIDEO_DUMP_START=0 VRD_VIDEO_DUMP_END=10790 \
  VRD_VIDEO_DUMP_EVERY=150 ./frontend ROM 10800
python3 notes/games/tools/frame2png.py DUMP OUT.png FRAME [FRAME ...]
```

ROMs are the 32X-ROMSET files (MD5s in `notes/games/romset-us.md`). Attract loops repeat, so each screen also appears later; the frame given is its first capture at a 150-frame interval, so the screen is up for some frames around it. Emulator timing, so a console may differ by a few frames.

| File | Game | Frame | What the screen says |
|------|------|-------|----------------------|
| `virtua-fighter-0300.png` | Virtua Fighter | 300 | AM2 logo, "AM R&D DEPT. #2" |
| `kolibri-0300-0600.png` | Kolibri | 300, 600 | "AMOEBA PRESENTS"; Novotrade International logo |
| `golf-magazine-0600.png` | Golf Magazine: 36 Great Holes | 600 | Flashpoint Productions logo; "Portions of code, copyright 1994 Flashpoint Productions, Inc." |
| `nfl-qb-club-0300.png` | NFL Quarterback Club | 300 | "Code ©1995 Iguana Entertainment, Inc. / Programmed By Iguana Entertainment, Inc." |
| `pitfall-0300-0450.png` | Pitfall: The Mayan Adventure | 300, 450 | Activision copyright; Big Bang Software and Zombie Virtual Reality Entertainment logos |
| `brutal-0750.png` | Brutal: Above the Claw | 750 | "Developed By" Alternative Reality Technologies (after GameTek's logo at 600) |
| `spider-man-0900.png` | The Amazing Spider-Man: Web of Fire | 900 | Blue Sky logo (no Zono credit seen in the loop) |
| `blackthorne-0450-0600.png` | Blackthorne | 450, 600 | Blizzard Entertainment logo; Paradox Development logo (Interplay's at 300) |
| `toughman-0750-0900.png` | Toughman Contest | 750, 900 | "High Score Productions and Visual Concepts present" |
| `toughman-2400-3150.png` | Toughman Contest | 2400, 2700, 3000, 3150 | Credit roll: "Developed by Visual Concepts Entertainment, Inc."; "Programming by Tim Meekins"; "32X programming by Roderick L. Mann" |

Not reached headless:

| File | Game | Result |
|------|------|--------|
| `virtua-racing-deluxe-attract.png` (frames 120, 240, 3840) | Virtua Racing Deluxe | 7,200 frames of attract loop show only the Sega and Sega Sports logos, demo races and the title. No staff screen. A relative search for staff words (`relsearch.py`) found no text, so any credits are graphics or compressed |
| `metal-head-attract.png` (150, 3300) | Metal Head | 10,800 frames: Sega logo, story, title. No developer credit |
| `shadow-squadron-attract.png` (300, 1500) | Shadow Squadron | 10,800 frames: Sega logo, title, demo. No developer credit |

Their credit rolls, if any, come after play that a scripted input run would have to win, so they stay with WP-32XLIST as a secondary source.
