# Contributing

## The three rules

1. **Write it in your own words.** Never paste text from Sega, Hitachi or Motorola manuals, or from other people's documents. Register layouts, addresses, bit meanings and timings are facts and can go in tables; explanations must be original. Run `python3 tools/check.py --verbatim` before sending a change.
2. **Cite everything that affects code.** Put the source key in brackets after the claim, with a section or page when you have one: `[SH7604 §8.3]`. New sources go in `src/appendices/bibliography.md` first.
3. **Say how you know.** Tag claims that matter with `tested`, `manual`, `emulator` or `disputed` (see `src/conventions.md`). A `tested` tag needs the console model, and a test ROM link if one exists.

## When sources disagree

Add a row to `src/appendices/discrepancies.md`, tag the claim `disputed` where it appears, and link to the row.

## Style

Plain words over jargon. If a term needs explaining, explain it the first time and add it to the glossary. Prefer a table over a paragraph for register bits.
