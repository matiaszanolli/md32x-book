#!/usr/bin/env python3
"""Checks the book before publishing.

  python3 tools/check.py            links and citations
  python3 tools/check.py --verbatim also compare text against the original manuals in sources/

Exit code is 1 if anything fails.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC, SOURCES = ROOT / "src", ROOT / "sources"
SHINGLE = 12  # this many identical words in a row counts as copied text

def heading_id(text):
    text = re.sub(r"<[^>]+>", "", text).strip().lower()
    return re.sub(r"[^a-z0-9_\- ]", "", text).replace(" ", "-")

def anchors(path):
    return {heading_id(m.group(1)) for m in re.finditer(r"^#{1,6}\s+(.+)$", path.read_text(), re.M)}

def strip_code(text):
    return re.sub(r"```.*?```", "", text, flags=re.S)

def check_links():
    errors = []
    bib_keys = anchors(SRC / "appendices/bibliography.md")
    for page in SRC.rglob("*.md"):
        text = strip_code(page.read_text())
        for target in re.findall(r"\]\(([^)\s]+)\)", text):
            if re.match(r"[a-z]+://", target):
                continue
            file, _, anchor = target.partition("#")
            dest = (page.parent / file).resolve() if file else page
            if not dest.exists():
                errors.append(f"{page.relative_to(ROOT)}: missing file {target}")
            elif anchor and dest.suffix == ".md" and anchor not in anchors(dest):
                errors.append(f"{page.relative_to(ROOT)}: missing anchor {target}")
        # inline citations like [SH7604 §8.3] must use a known key
        for key in re.findall(r"\[([A-Z0-9][A-Z0-9-]+)(?:[ ,][^\]]*)?\](?!\()", text):
            if key.lower() not in bib_keys:
                errors.append(f"{page.relative_to(ROOT)}: unknown source key [{key}]")
    return errors

def check_disputed():
    """A disputed tag must sit in the same block as a link to discrepancies.md."""
    errors = []
    for page in SRC.rglob("*.md"):
        if page.name in ("conventions.md", "discrepancies.md"):
            continue
        for block in re.split(r"\n\s*\n", strip_code(page.read_text())):
            if 'tag disputed' in block and 'discrepancies.md' not in block:
                errors.append(f"{page.relative_to(ROOT)}: disputed tag without a discrepancies.md link: {block.strip()[:60]!r}")
    return errors

def words(text):
    return re.findall(r"[a-z0-9]+", strip_code(text).lower())

def check_verbatim():
    files = [p for p in SOURCES.rglob("*") if p.suffix in {".md", ".txt"} and p.name != "README.md"]
    if not files:
        return ["sources/ is empty: copy the converted manuals there to run this check"]
    seen = {}
    for f in files:
        w = words(f.read_text(errors="ignore"))
        for i in range(len(w) - SHINGLE + 1):
            seen.setdefault(" ".join(w[i:i + SHINGLE]), f.name)
    errors = []
    for page in SRC.rglob("*.md"):
        if page.name == "bibliography.md":  # document titles are quoted on purpose
            continue
        w = words(page.read_text())
        i = 0
        while i <= len(w) - SHINGLE:
            hit = seen.get(" ".join(w[i:i + SHINGLE]))
            if hit:
                j = i + SHINGLE
                while j < len(w) and " ".join(w[j - SHINGLE + 1:j + 1]) in seen:
                    j += 1
                errors.append(f"{page.relative_to(ROOT)}: {j - i} words copied from {hit}: \"{' '.join(w[i:i + 15])}...\"")
                i = j
            else:
                i += 1
    return errors

if __name__ == "__main__":
    problems = check_links() + check_disputed()
    if "--verbatim" in sys.argv:
        problems += check_verbatim()
    print("\n".join(problems) or "All checks passed.")
    sys.exit(1 if problems else 0)
