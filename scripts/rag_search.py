#!/usr/bin/env python3
"""Hybrid RAG search for the Cultural Revolution knowledge base.

Workflow:
    python3 scripts/rag_search.py --root /path/to/kb "查询词"
    python3 scripts/rag_search.py --root /path/to/kb --top-k 15 "查询词"
    python3 scripts/rag_search.py --root /path/to/kb --expand "source_file#chunk_id"
    python3 scripts/rag_search.py --root /path/to/kb --rag-status  # check index status

分层证据预算模式 (默认):
  1. 全库检索 top-k 个多样片段
  2. 对关键来源做相邻段落扩展
  3. 对争议问题交叉验证
  4. 输出含来源、chunk id 的结构化结果
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

CHROMA_DIR_NAME = ".chroma"
EMBED_MODEL = os.environ.get("WENGE_EMBED_MODEL", "shibing624/text2vec-base-chinese")

# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------

ROOT = None  # set after root known

SHORT_NAMES = {
    "天地翻覆": "天地翻覆——中國文化大革命史 (杨继绳)",
    "十年一梦": "十年一梦 (徐景贤)",
    "十年非梦": "十年非梦——黄金海回忆录",
    "张春桥": "张春桥狱中家书",
    "戚本禹": "戚本禹回忆录",
    "晚年周恩来": "晚年周恩来 (高文谦)",
    "第02卷": "【中华人民共和国史】第02卷",
    "第03卷": "【中华人民共和国史】第03卷",
    "第04卷": "【中华人民共和国史】第04卷",
    "第05卷": "【中华人民共和国史】第05卷",
    "第06卷": "【中华人民共和国史】第06卷",
    "第08卷": "【中华人民共和国史】第08卷",
    "第10卷": "【中华人民共和国史】第10卷",
}


def pretty_source(rel_path: str) -> str:
    """Shorten source paths for readability."""
    for short, full in SHORT_NAMES.items():
        if full in rel_path or short in rel_path:
            return f"{short} ({rel_path})"
    return rel_path


# ---------------------------------------------------------------------------
# embedding
# ---------------------------------------------------------------------------

_EMBED_FN = None
_EMBED_DIM = None


def get_embed_fn():
    global _EMBED_FN, _EMBED_DIM
    if _EMBED_FN is not None:
        return _EMBED_FN, _EMBED_DIM
    from sentence_transformers import SentenceTransformer  # noqa: auto-import
    model = SentenceTransformer(EMBED_MODEL, device="cpu", local_files_only=True)
    _EMBED_FN = model.encode
    _EMBED_DIM = model.get_sentence_embedding_dimension()
    return _EMBED_FN, _EMBED_DIM


# ---------------------------------------------------------------------------
# BM25 index (built per-query from top candidate texts)
# ---------------------------------------------------------------------------

def build_bm25(texts: list[str]) -> Any:
    from rank_bm25 import BM25Okapi  # noqa: auto-import
    tokenized = [list(t) for t in texts]  # char-level for Chinese
    return BM25Okapi(tokenized)


def bm25_scores(bm25: Any, query: str, texts: list[str]) -> list[float]:
    tokenized_q = list(query)
    scores = bm25.get_scores(tokenized_q)
    return scores.tolist()


# ---------------------------------------------------------------------------
# Chroma search
# ---------------------------------------------------------------------------

def vector_search(collection, query: str, k: int) -> tuple[list[str], list[dict], list[float]]:
    embed_fn, _ = get_embed_fn()
    q_vec = embed_fn([query], normalize_embeddings=True)
    results = collection.query(query_embeddings=q_vec, n_results=k, include=["documents", "metadatas", "distances"])
    docs = results["documents"][0] if results["documents"] else []
    metas = results["metadatas"][0] if results["metadatas"] else []
    dists = results["distances"][0] if results["distances"] else []
    # convert distance to similarity score (cosine)
    scores = [(1 - d) for d in dists]
    return docs, metas, scores


# ---------------------------------------------------------------------------
# expand context around a chunk
# ---------------------------------------------------------------------------

def expand_chunk(source_path: str, chunk_start: int, chunk_end: int,
                 context_lines: int = 40) -> str:
    """Read surrounding context from the source file."""
    full_path = ROOT / source_path if ROOT else Path(source_path)
    if not full_path.exists():
        return ""
    try:
        text = full_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    # expand
    estart = max(0, chunk_start - context_lines * 40)
    eend = min(len(text), chunk_end + context_lines * 40)
    expanded = text[estart:eend]
    return expanded


# ---------------------------------------------------------------------------
# hybrid search
# ---------------------------------------------------------------------------

def hybrid_search(collection, query: str, k: int,
                  vector_weight: float = 0.6, bm25_weight: float = 0.4) \
        -> list[dict[str, Any]]:
    """Vector + BM25 hybrid search with RRF fusion."""
    docs, metas, vec_scores = vector_search(collection, query, k)

    # build BM25 from the same candidate docs
    bm25 = build_bm25(docs)
    bm25_s = bm25_scores(bm25, query, docs)

    # normalize each score set to [0,1]
    def norm(scores: list[float]) -> list[float]:
        if not scores:
            return scores
        mn, mx = min(scores), max(scores)
        if mx - mn < 1e-9:
            return [0.5] * len(scores)
        return [(s - mn) / (mx - mn) for s in scores]

    vn = norm(vec_scores)
    bn = norm(bm25_s)

    fused: list[dict[str, Any]] = []
    for i, doc in enumerate(docs):
        hybrid = vn[i] * vector_weight + bn[i] * bm25_weight
        fused.append({
            "text": doc,
            "source": metas[i]["source"],
            "chunk_id": metas[i].get("chunk_id", ""),
            "chunk_start": metas[i].get("chunk_start", 0),
            "chunk_end": metas[i].get("chunk_end", 0),
            "score_vector": round(vn[i], 4),
            "score_bm25": round(bn[i], 4),
            "score_hybrid": round(hybrid, 4),
        })

    fused.sort(key=lambda x: x["score_hybrid"], reverse=True)
    return fused


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

def print_results(results: list[dict[str, Any]], top_k: int, expand: bool = False):
    """Print results grouped by source for diversity."""
    seen_sources: dict[str, list[dict]] = {}
    for r in results[:top_k]:
        src = r["source"]
        if src not in seen_sources:
            seen_sources[src] = []
        if len(seen_sources[src]) < 3:  # max 3 chunks per source
            seen_sources[src].append(r)

    # interleave for diversity
    ordered: list[dict] = []
    while any(seen_sources.values()):
        for src in list(seen_sources.keys()):
            if seen_sources[src]:
                ordered.append(seen_sources[src].pop(0))
            if not seen_sources[src]:
                del seen_sources[src]

    for i, r in enumerate(ordered, 1):
        print(f"\n--- Result {i} [hybrid={r['score_hybrid']:.3f}] ---")
        print(f"来源: {pretty_source(r['source'])}")
        print(f"Chunk: {r['chunk_id']}")
        print("─" * 60)
        print(r["text"][:1200])

        if expand and r["chunk_id"]:
            expanded = expand_chunk(r["source"], r["chunk_start"], r["chunk_end"])
            if expanded:
                print(f"\n  ── 展开上下文 (相邻 ~80行) ──")
                print(expanded[:600])

    print(f"\n{'='*60}")
    print(f"共计 {len(ordered)} 个结果, 来自 {len(set(r['source'] for r in ordered))} 个来源")


def print_status(collection, root: Path):
    """Print index status."""
    count = collection.count()
    db_path = root / CHROMA_DIR_NAME / "track.db"
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute("SELECT count(*), sum(num_chunks) FROM files").fetchone()
        n_files, n_chunks = rows[0] or 0, rows[1] or 0
        conn.close()
    else:
        n_files = n_chunks = 0

    print(f"Vector store: {count} embeddings", file=sys.stderr)
    print(f"Indexed files: {n_files}", file=sys.stderr)
    print(f"Total chunks: {n_chunks}", file=sys.stderr)
    print(f"Model: {EMBED_MODEL}", file=sys.stderr)


# ---------------------------------------------------------------------------
# JSON output for model consumption
# ---------------------------------------------------------------------------

def print_json_results(results: list[dict[str, Any]], top_k: int):
    """Output structured JSON for model consumption."""
    out = []
    for r in results[:top_k]:
        out.append({
            "text": r["text"][:2000],
            "source": pretty_source(r["source"]),
            "source_path": r["source"],
            "chunk_id": r["chunk_id"],
            "relevance": r["score_hybrid"],
        })
    # deduplicate by text content similarity
    seen_texts: set[int] = set()
    deduped = []
    for item in out:
        h = hash(item["text"][:100])
        if h not in seen_texts:
            seen_texts.add(h)
            deduped.append(item)
    print(json.dumps(deduped, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Hybrid RAG search for 文革 knowledge base")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--root", type=Path,
                        default=Path(os.environ.get("WENGE_KB_ROOT",
                                    str(Path.home() / "wenge-knowledge-base"))))
    parser.add_argument("--top-k", type=int, default=12, help="Number of results (default: 12)")
    parser.add_argument("--expand", metavar="CHUNK_ID", help="Expand context around a chunk")
    parser.add_argument("--rag-status", action="store_true", help="Show index status")
    parser.add_argument("--json", action="store_true", help="Output JSON for model consumption")
    parser.add_argument("--verbose", action="store_true", help="Show score details")
    args = parser.parse_args()

    global ROOT
    ROOT = args.root.expanduser().resolve()

    chroma_path = ROOT / CHROMA_DIR_NAME
    if not chroma_path.exists():
        print("ERROR: Index not found. Run 'python3 scripts/rag_index.py' first.", file=sys.stderr)
        sys.exit(1)

    import chromadb  # noqa: auto-import
    client = chromadb.PersistentClient(path=str(chroma_path))
    try:
        coll = client.get_collection("wenge")
    except Exception:
        print("ERROR: Collection 'wenge' not found. Run 'python3 scripts/rag_index.py' first.", file=sys.stderr)
        sys.exit(1)

    # status mode
    if args.rag_status:
        print_status(coll, ROOT)
        return

    # expand mode
    if args.expand:
        parts = args.expand.split("#")
        if len(parts) < 2:
            print("ERROR: Chunk ID format: source_file#chunk_index", file=sys.stderr)
            sys.exit(1)
        source_file = "#".join(parts[:-1])
        try:
            chunk_idx = int(parts[-1])
        except ValueError:
            print(f"ERROR: Invalid chunk index: {parts[-1]}", file=sys.stderr)
            sys.exit(1)
        # look up in chroma
        results = coll.get(ids=[args.expand], include=["documents", "metadatas"])
        if results["ids"]:
            meta = results["metadatas"][0]
            expanded = expand_chunk(meta["source"], meta["chunk_start"], meta["chunk_end"],
                                    context_lines=80)
            print(f"# 展开上下文: {pretty_source(meta['source'])}")
            print(f"# Chunk: {args.expand}")
            print("=" * 60)
            print(expanded)
        else:
            # try to read source directly
            expanded = expand_chunk(source_file, 0, 0, context_lines=2000)
            print(expanded)
        return

    # search mode
    if not args.query:
        parser.print_help()
        sys.exit(1)

    results = hybrid_search(coll, args.query, k=args.top_k * 2)

    if args.json:
        print_json_results(results, args.top_k)
    else:
        print_results(results, args.top_k)


if __name__ == "__main__":
    main()
