#!/usr/bin/env python3
"""Index the Cultural Revolution knowledge base into Chroma vector store.

Usage:
    python3 scripts/rag_index.py --root /path/to/knowledge_base
    python3 scripts/rag_index.py --root /path/to/knowledge_base --rebuild   # force rebuild
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# chunking
# ---------------------------------------------------------------------------

CHUNK_SIZE = 800        # characters
CHUNK_OVERLAP = 120
MIN_CHUNK = 60

# directories to index
INDEX_DIRS = (
    Path("raw"),
    Path("books"),
    Path("notes"),
    Path("topics"),
    Path("index"),
)

EXTS = {".txt", ".md", ".json"}


def source_key(path: Path) -> tuple[Path, str]:
    """Return a stable key so raw text is skipped when a cleaned file exists."""
    stem = re.sub(r"-cleaned$", "", path.stem, flags=re.I)
    return path.parent, stem


def prefer_cleaned(paths: list[Path]) -> list[Path]:
    """Prefer foo-cleaned.txt over foo.txt from the same directory."""
    chosen: dict[tuple[Path, str], Path] = {}
    for path in sorted(paths):
        key = source_key(path) if path.suffix.lower() == ".txt" else (path.parent, path.name)
        current = chosen.get(key)
        if current is None:
            chosen[key] = path
            continue
        if path.name.endswith("-cleaned.txt") and not current.name.endswith("-cleaned.txt"):
            chosen[key] = path
    return sorted(chosen.values())


def iter_text_files(root: Path):
    """Yield paths to indexable text files."""
    for rel_dir in INDEX_DIRS:
        base = root / rel_dir
        if not base.exists():
            continue
        paths = []
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in EXTS:
                continue
            paths.append(path)
        yield from prefer_cleaned(paths)


def chunk_text(text: str, source: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[dict[str, Any]]:
    """Split text into overlapping chunks with source metadata."""
    chunks: list[dict[str, Any]] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end == len(text):
            pass
        elif end < len(text):
            # try to break at paragraph boundary
            next_para = text.find("\n\n", end - overlap, end + overlap + 200)
            if next_para != -1 and next_para > start + MIN_CHUNK:
                end = next_para
            else:
                # try sentence boundary
                for sep in ("。", "！", "？", "\n"):
                    idx = text.rfind(sep, end - overlap, end)
                    if idx > start + MIN_CHUNK:
                        end = idx + 1
                        break
        text_chunk = text[start:end].strip()
        if len(text_chunk) >= MIN_CHUNK:
            chunks.append({
                "text": text_chunk,
                "source": source,
                "chunk_start": start,
                "chunk_end": end,
            })
        start = end - overlap if end < len(text) else len(text)
    return chunks


# ---------------------------------------------------------------------------
# embedding + chroma
# ---------------------------------------------------------------------------

EMBED_MODEL = os.environ.get("KB_EMBED_MODEL", "shibing624/text2vec-base-chinese")
CHROMA_DIR = None  # set after root known


def get_chroma_path(root: Path) -> Path:
    return root / ".chroma"


def get_embed_fn():
    """Lazy-load embedding model."""
    from sentence_transformers import SentenceTransformer  # noqa: auto-import
    model = SentenceTransformer(EMBED_MODEL, device="cpu", local_files_only=True)
    dim = model.get_sentence_embedding_dimension()

    def embed(texts: list[str]) -> list[list[float]]:
        vecs = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return vecs.tolist()

    return embed, dim


# ---------------------------------------------------------------------------
# incremental tracking via sqlite
# ---------------------------------------------------------------------------

TRACK_DB = None


def get_track_path(root: Path) -> Path:
    return root / ".chroma" / "track.db"


def init_tracking(root: Path):
    db_path = get_track_path(root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            mtime REAL,
            size INTEGER,
            md5 TEXT,
            indexed_at REAL,
            num_chunks INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    globals()["TRACK_DB"] = conn
    return conn


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_indexed(rel_path: str, root: Path, conn: sqlite3.Connection) -> bool:
    full = root / rel_path
    if not full.exists():
        return False
    st = full.stat()
    row = conn.execute("SELECT mtime, size, md5 FROM files WHERE path = ?",
                       (rel_path,)).fetchone()
    if row is None:
        return False
    old_mtime, old_size, old_md5 = row
    if abs(old_mtime - st.st_mtime) > 0.01 or old_size != st.st_size:
        return False
    if old_md5 != file_md5(full):
        return False
    return True


def mark_indexed(rel_path: str, root: Path, num_chunks: int, conn: sqlite3.Connection):
    full = root / rel_path
    st = full.stat()
    conn.execute("""
        INSERT OR REPLACE INTO files (path, mtime, size, md5, indexed_at, num_chunks)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (rel_path, st.st_mtime, st.st_size, file_md5(full), time.time(), num_chunks))
    conn.commit()


def remove_stale(active_paths: set[str], conn: sqlite3.Connection) -> list[str]:
    """Remove tracking entries for files that no longer exist or are no longer preferred."""
    rows = conn.execute("SELECT path FROM files").fetchall()
    stale_paths = [row[0] for row in rows if row[0] not in active_paths]
    if stale_paths:
        conn.execute("DELETE FROM files WHERE path IN ({})".format(
            ",".join("?" for _ in stale_paths)), stale_paths)
        conn.commit()
    return stale_paths


def delete_source_chunks(collection: Any, sources: list[str]) -> None:
    """Delete existing Chroma chunks for source files before replacing them."""
    for source in sources:
        try:
            collection.delete(where={"source": source})
        except Exception:
            # Chroma raises if there is nothing to delete in some versions.
            pass


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Index knowledge base into Chroma")
    parser.add_argument("--root", type=Path,
                        default=Path(os.environ.get("KB_ROOT",
                                    str(Path.home() / "knowledge-base"))))
    parser.add_argument("--rebuild", action="store_true", help="Delete existing index and rebuild")
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    chroma_path = get_chroma_path(root)

    # connect to chroma (without default embedding fn)
    import chromadb  # noqa: auto-import
    client = chromadb.PersistentClient(path=str(chroma_path))

    coll_name = "kb"
    try:
        if args.rebuild:
            client.delete_collection(coll_name)
            coll = client.create_collection(name=coll_name, metadata={"hnsw:space": "cosine"})
        else:
            coll = client.get_or_create_collection(name=coll_name, metadata={"hnsw:space": "cosine"})
    except Exception:
        coll = client.get_or_create_collection(name=coll_name, metadata={"hnsw:space": "cosine"})

    # tracking
    conn = init_tracking(root)

    files = sorted(iter_text_files(root))
    print(f"Found {len(files)} text files", file=sys.stderr)

    active_paths: set[str] = set()
    total_chunks = 0
    new_files = 0
    skipped = 0
    batch_texts: list[str] = []
    batch_metadatas: list[dict] = []
    batch_ids: list[str] = []

    for path in files:
        rel = str(path.relative_to(root))
        active_paths.add(rel)

        if not args.rebuild and is_indexed(rel, root, conn):
            row = conn.execute("SELECT num_chunks FROM files WHERE path = ?", (rel,)).fetchone()
            total_chunks += row[0] if row else 0
            skipped += 1
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"  SKIP {rel}: {e}", file=sys.stderr)
            continue

        if not text.strip():
            continue

        chunks = chunk_text(text, source=rel)
        total_chunks += len(chunks)
        new_files += 1
        delete_source_chunks(coll, [rel])

        for i, ch in enumerate(chunks):
            batch_texts.append(ch["text"])
            batch_metadatas.append({
                "source": rel,
                "chunk_id": f"{rel}#{i}",
                "chunk_start": ch["chunk_start"],
                "chunk_end": ch["chunk_end"],
            })
            batch_ids.append(f"{rel}#{i}")

        mark_indexed(rel, root, len(chunks), conn)

    # compute embeddings in batches, then add to Chroma
    BATCH_SIZE = 1000
    if batch_texts:
        embed_fn, dim = get_embed_fn()
        print(f"Embedding model: {EMBED_MODEL} (dim={dim})", file=sys.stderr)
        print("Computing embeddings may take a while on first run...", file=sys.stderr)
        print(f"Computing embeddings for {len(batch_texts)} chunks...", file=sys.stderr)
        for batch_start in range(0, len(batch_texts), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(batch_texts))
            b_texts = batch_texts[batch_start:batch_end]
            b_metas = batch_metadatas[batch_start:batch_end]
            b_ids = batch_ids[batch_start:batch_end]
            print(f"  batch {batch_start}-{batch_end} / {len(batch_texts)}", file=sys.stderr)
            embeddings = embed_fn(b_texts)
            coll.add(
                documents=b_texts,
                embeddings=embeddings,
                metadatas=b_metas,
                ids=b_ids,
            )

    # remove stale tracking and chunks for files that are gone or superseded by cleaned text
    stale_paths = remove_stale(active_paths, conn)
    delete_source_chunks(coll, stale_paths)

    print(f"\nIndexed: {new_files} new files, {skipped} up-to-date, "
          f"{total_chunks} total chunks", file=sys.stderr)
    print(f"Chroma path: {chroma_path}", file=sys.stderr)

    count = coll.count()
    print(f"Vector store: {count} embeddings", file=sys.stderr)


if __name__ == "__main__":
    main()
