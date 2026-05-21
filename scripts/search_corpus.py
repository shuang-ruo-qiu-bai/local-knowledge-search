#!/usr/bin/env python3
"""Search the local knowledge base corpus with context snippets."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


DEFAULT_ROOT = Path(os.environ.get("KB_ROOT", str(Path.home() / "knowledge-base")))
SEARCH_DIRS = (
    Path("raw"),
    Path("books"),
    Path("notes"),
    Path("topics"),
    Path("index"),
)
EXTS = {".txt", ".md", ".json"}


def iter_files(root: Path):
    for rel_dir in SEARCH_DIRS:
        base = root / rel_dir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in EXTS:
                yield path


def line_matches(line: str, terms: list[str], any_term: bool) -> bool:
    folded = line.casefold()
    hits = [term.casefold() in folded for term in terms]
    return any(hits) if any_term else all(hits)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terms", nargs="+", help="terms to search; default requires all terms on one line")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--any", action="store_true", help="match any term instead of all terms")
    parser.add_argument("--context", type=int, default=2, help="context lines around each hit")
    parser.add_argument("--limit", type=int, default=80, help="maximum hits to print")
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    shown = 0
    for path in iter_files(root):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for idx, line in enumerate(lines):
            if not line_matches(line, args.terms, args.any):
                continue
            start = max(0, idx - args.context)
            end = min(len(lines), idx + args.context + 1)
            rel = path.relative_to(root)
            print(f"\n## {rel}:{idx + 1}")
            for line_no in range(start, end):
                marker = ">" if line_no == idx else " "
                print(f"{marker} {line_no + 1}: {lines[line_no]}")
            shown += 1
            if shown >= args.limit:
                return


if __name__ == "__main__":
    main()
