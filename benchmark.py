"""
Phase 2 benchmark — runs 5 group queries against the CMMI document
and prints top-3 retrieved chunks per query.

Usage:
    python benchmark.py [fixed|sentence|recursive]
"""
from __future__ import annotations

import sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.embeddings import LocalEmbedder
from src.models import Document
from src.store import EmbeddingStore

QUERIES = [
    "CMMI V2.0 là gì và tại sao nên sử dụng?",
    "Practice Area trong CMMI V2.0 gồm những gì?",
    "Mức độ trưởng thành (Maturity Level) trong CMMI được phân chia như thế nào?",
    "Configuration Management (CM) trong CMMI thực hiện những gì?",
    "Lợi ích của việc áp dụng CMMI V2.0 cho tổ chức phát triển phần mềm?",
]

STRATEGY = sys.argv[1] if len(sys.argv) > 1 else "recursive"

CHUNKERS = {
    "fixed":     FixedSizeChunker(chunk_size=400, overlap=50),
    "sentence":  SentenceChunker(max_sentences_per_chunk=3),
    "recursive": RecursiveChunker(chunk_size=400),
}

chunker = CHUNKERS[STRATEGY]
print(f"Strategy: {STRATEGY}")

# Load document
content = Path("data/cmmi_nhom2.md").read_text(encoding="utf-8")
chunks = chunker.chunk(content)
print(f"Chunks: {len(chunks)}, avg length: {sum(len(c) for c in chunks) // len(chunks)} chars\n")

# Index chunks
embedder = LocalEmbedder()
store = EmbeddingStore(embedding_fn=embedder)
docs = [
    Document(id=f"cmmi_chunk_{i}", content=chunk, metadata={"source": "cmmi_nhom2", "chunk_index": i})
    for i, chunk in enumerate(chunks)
]
store.add_documents(docs)
print(f"Indexed {store.get_collection_size()} chunks\n")
print("=" * 70)

# Run benchmark
for i, query in enumerate(QUERIES, 1):
    print(f"\nQuery {i}: {query}")
    print("-" * 60)
    results = store.search(query, top_k=3)
    for rank, r in enumerate(results, 1):
        preview = r["content"][:150].replace("\n", " ")
        print(f"  [{rank}] score={r['score']:.3f} | {preview}...")
