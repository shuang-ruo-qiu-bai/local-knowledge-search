#!/usr/bin/env python3
"""Dynamically inventory the local Cultural Revolution research corpus."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from pathlib import Path


DEFAULT_ROOT = Path(os.environ.get("WENGE_KB_ROOT", str(Path.home() / "wenge-knowledge-base")))
BOOK_EXTS = {".pdf", ".epub"}
TEXT_EXTS = {".txt", ".md", ".json"}


def norm_stem(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"-cleaned$", "", stem, flags=re.I)
    stem = re.sub(r"\s+", "", stem)
    stem = re.sub(r"[【】\[\]（）()《》「」“”\"':：,，.。_\-—·\s]", "", stem)
    return stem.lower()


def scan(root: Path) -> dict:
    books_dir = root / "books" / "文革"
    raw_dir = root / "raw" / "文革"
    notes_dir = root / "notes"
    topics_dir = root / "topics"
    index_dir = root / "index"

    books = [p for p in books_dir.rglob("*") if p.is_file() and p.suffix.lower() in BOOK_EXTS] if books_dir.exists() else []
    standalone_text_books = [
        p
        for p in books_dir.rglob("*")
        if p.is_file()
        and p.suffix.lower() in {".txt", ".md"}
        and not p.stem.endswith("-cleaned")
    ] if books_dir.exists() else []
    books.extend(standalone_text_books)
    raw_texts = [p for p in raw_dir.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_EXTS] if raw_dir.exists() else []
    book_texts = [p for p in books_dir.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_EXTS] if books_dir.exists() else []
    notes = [p for p in notes_dir.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_EXTS] if notes_dir.exists() else []
    topics = [p for p in topics_dir.rglob("*") if p.is_file()] if topics_dir.exists() else []
    indexes = [p for p in index_dir.rglob("*") if p.is_file()] if index_dir.exists() else []

    text_by_key = defaultdict(list)
    for p in raw_texts + book_texts:
        text_by_key[norm_stem(p)].append(p)

    note_by_key = defaultdict(list)
    for p in notes:
        note_by_key[norm_stem(p)].append(p)

    records = []
    for p in sorted(books):
        key = norm_stem(p)
        exact_texts = text_by_key.get(key, [])
        fuzzy_texts = [t for k, vals in text_by_key.items() for t in vals if key and (key in k or k in key)]
        texts = sorted(set(exact_texts + fuzzy_texts))
        fuzzy_notes = [n for k, vals in note_by_key.items() for n in vals if key and (key in k or k in key)]
        records.append(
            {
                "book": str(p.relative_to(root)),
                "type": p.suffix.lower().lstrip("."),
                "text_files": [str(t.relative_to(root)) for t in texts],
                "note_files": [str(n.relative_to(root)) for n in sorted(set(fuzzy_notes))],
            }
        )

    loose_texts = []
    book_text_set = {item for r in records for item in r["text_files"]}
    for p in sorted(raw_texts + book_texts):
        rel = str(p.relative_to(root))
        if rel not in book_text_set:
            loose_texts.append(rel)

    return {
        "root": str(root),
        "counts": {
            "books": len(books),
            "text_files": len(raw_texts) + len(book_texts),
            "notes": len(notes),
            "topics": len(topics),
            "indexes": len(indexes),
        },
        "books": records,
        "unmatched_text_files": loose_texts,
        "topic_files": [str(p.relative_to(root)) for p in sorted(topics)],
        "index_files": [str(p.relative_to(root)) for p in sorted(indexes)],
    }


def print_markdown(data: dict) -> None:
    print(f"# 文革资料库盘点\n\nRoot: `{data['root']}`\n")
    counts = data["counts"]
    print(
        f"- books: {counts['books']}\n"
        f"- text files: {counts['text_files']}\n"
        f"- notes: {counts['notes']}\n"
        f"- topics: {counts['topics']}\n"
        f"- indexes: {counts['indexes']}\n"
    )
    print("| Book | Type | Text | Notes |")
    print("| --- | --- | --- | --- |")
    for record in data["books"]:
        text = "<br>".join(record["text_files"]) if record["text_files"] else "MISSING"
        notes = "<br>".join(record["note_files"]) if record["note_files"] else ""
        print(f"| `{record['book']}` | {record['type']} | {text} | {notes} |")
    if data["unmatched_text_files"]:
        print("\n## Unmatched Text Files")
        for item in data["unmatched_text_files"]:
            print(f"- `{item}`")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    args = parser.parse_args()

    data = scan(args.root.expanduser().resolve())
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_markdown(data)


if __name__ == "__main__":
    main()
