# The Mega Drive & 32X Book

A complete technical reference and programming guide for the Sega Mega Drive / Genesis, the Sega 32X and the Hitachi SH-2 (SH7604), with how-tos and patterns for getting the most out of the hardware.

## Building

Install [mdBook](https://rust-lang.github.io/mdBook/) (`cargo install mdbook --version 0.4.40 --locked`), then:

```sh
mdbook serve --open        # live preview at http://localhost:3000
python3 tools/check.py     # links and citations
```

Pushing to `main` builds and publishes to GitHub Pages (enable Pages with "GitHub Actions" as the source in the repo settings).

## Layout

```
src/SUMMARY.md      table of contents (mdBook builds the sidebar from it)
src/megadrive/      Part I
src/sh2/            Part II
src/32x/            Part III
src/howto/          Part IV
src/patterns/       Part V
src/techniques/     Part VI
src/appendices/     memory maps, registers, timing, discrepancies, glossary, sources
theme/tags.css      styling for the tested / manual / emulator / disputed tags
tools/check.py      link, citation and copied-text checks
sources/            your local copies of the original manuals (not committed)
notes/techniques/   harvested techniques per chapter (working material, not published)
```

## Writing rules

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

To be decided.
