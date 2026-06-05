"""
Streamlit UI for Lab 7 — Embedding & Vector Store explorer.
Run: streamlit run app.py
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import streamlit as st

from src.chunking import (
    ChunkingStrategyComparator,
    FixedSizeChunker,
    RecursiveChunker,
    SentenceChunker,
    compute_similarity,
)
from src.embeddings import MockEmbedder, _mock_embed
from src.models import Document
from src.store import EmbeddingStore

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Lab 7 — RAG Explorer", layout="wide")
st.title("Lab 7 — Embedding & Vector Store Explorer")

DATA_DIR = Path("data")
DATA_FILES = sorted(DATA_DIR.glob("*.txt")) + sorted(DATA_DIR.glob("*.md"))

# ── helpers ───────────────────────────────────────────────────────────────────
def euclidean(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


@st.cache_resource
def get_local_embedder():
    from src.embeddings import LocalEmbedder
    return LocalEmbedder()


@st.cache_resource
def get_openai_embedder():
    from src.embeddings import OpenAIEmbedder
    return OpenAIEmbedder()


def get_embedder(choice: str):
    if choice == "Local (all-MiniLM-L6-v2)":
        try:
            return get_local_embedder()
        except Exception as e:
            st.warning(f"Local embedder failed: {e}. Falling back to Mock.")
            return _mock_embed
    elif choice == "OpenAI (text-embedding-3-small)":
        try:
            return get_openai_embedder()
        except Exception as e:
            st.warning(f"OpenAI embedder failed: {e}. Falling back to Mock.")
            return _mock_embed
    return _mock_embed


def get_chunker(strategy: str, chunk_size: int, overlap: int, max_sentences: int):
    if strategy == "FixedSizeChunker":
        return FixedSizeChunker(chunk_size=chunk_size, overlap=overlap)
    elif strategy == "SentenceChunker":
        return SentenceChunker(max_sentences_per_chunk=max_sentences)
    else:
        return RecursiveChunker(chunk_size=chunk_size)


# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")

    embedder_choice = st.selectbox(
        "Embedder",
        ["Mock (random, fast)", "Local (all-MiniLM-L6-v2)", "OpenAI (text-embedding-3-small)"],
        help="Mock = no install needed. Local = pip install sentence-transformers. OpenAI = needs API key."
    )

    st.divider()
    st.subheader("Chunking")
    strategy = st.selectbox("Strategy", ["RecursiveChunker", "FixedSizeChunker", "SentenceChunker"])
    chunk_size = st.slider("Chunk size (chars)", 100, 1000, 400, 50,
                           disabled=(strategy == "SentenceChunker"))
    overlap = st.slider("Overlap (chars)", 0, 200, 50, 10,
                        disabled=(strategy != "FixedSizeChunker"))
    max_sentences = st.slider("Max sentences / chunk", 1, 10, 3,
                              disabled=(strategy != "SentenceChunker"))

    st.divider()
    if st.button("Clear index", type="secondary", use_container_width=True):
        st.session_state.pop("store", None)
        st.session_state.pop("indexed_files", None)
        st.success("Index cleared.")

# ── tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["Documents & Chunks", "Search", "Similarity Explorer", "Agent Q&A"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Documents & Chunks
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Load & Index Documents")

    selected_files = st.multiselect(
        "Select files from data/",
        options=[f.name for f in DATA_FILES],
        default=["cmmi_nhom2.md"] if (DATA_DIR / "cmmi_nhom2.md").exists() else ([DATA_FILES[0].name] if DATA_FILES else []),
    )

    col_load, col_preview = st.columns([1, 2])

    with col_load:
        if st.button("Chunk & Index", type="primary", use_container_width=True):
            if not selected_files:
                st.warning("Select at least one file.")
            else:
                embedder = get_embedder(embedder_choice)
                chunker = get_chunker(strategy, chunk_size, overlap, max_sentences)
                store = EmbeddingStore(embedding_fn=embedder)
                all_chunks: dict[str, list[str]] = {}

                with st.spinner("Chunking and embedding..."):
                    for fname in selected_files:
                        content = (DATA_DIR / fname).read_text(encoding="utf-8")
                        chunks = chunker.chunk(content)
                        all_chunks[fname] = chunks
                        docs = [
                            Document(
                                id=f"{Path(fname).stem}_chunk_{i}",
                                content=chunk,
                                metadata={"source": fname, "chunk_index": i},
                            )
                            for i, chunk in enumerate(chunks)
                        ]
                        store.add_documents(docs)

                st.session_state["store"] = store
                st.session_state["indexed_files"] = selected_files
                st.session_state["all_chunks"] = all_chunks
                st.success(f"Indexed {store.get_collection_size()} chunks from {len(selected_files)} file(s).")

    with col_preview:
        if "store" in st.session_state:
            st.metric("Total chunks in index", st.session_state["store"].get_collection_size())

    # Chunk stats + comparator
    if "all_chunks" in st.session_state:
        st.divider()
        st.subheader("Chunk Statistics")

        for fname, chunks in st.session_state["all_chunks"].items():
            if not chunks:
                continue
            lengths = [len(c) for c in chunks]
            with st.expander(f"{fname} — {len(chunks)} chunks", expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Count", len(chunks))
                c2.metric("Avg length", f"{sum(lengths)//len(lengths)} chars")
                c3.metric("Min", f"{min(lengths)} chars")
                c4.metric("Max", f"{max(lengths)} chars")

                st.markdown("**Sample chunks:**")
                sample_indices = random.sample(range(len(chunks)), min(3, len(chunks)))
                for idx in sample_indices:
                    st.markdown(f"<small>Chunk #{idx}</small>", unsafe_allow_html=True)
                    st.text_area("", chunks[idx], height=120, key=f"chunk_{fname}_{idx}")

        # Strategy comparator
        st.divider()
        st.subheader("Strategy Comparator (side-by-side)")
        comp_file = st.selectbox("Compare on file", list(st.session_state["all_chunks"].keys()), key="comp_file")
        if comp_file:
            content = (DATA_DIR / comp_file).read_text(encoding="utf-8")
            result = ChunkingStrategyComparator().compare(content, chunk_size=chunk_size)
            cols = st.columns(3)
            for col, (name, stats) in zip(cols, result.items()):
                col.metric(name, f"{stats['count']} chunks", f"avg {stats['avg_length']:.0f} chars")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Search
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Vector Search")

    if "store" not in st.session_state:
        st.info("Go to **Documents & Chunks** tab and click **Chunk & Index** first.")
    else:
        store: EmbeddingStore = st.session_state["store"]

        col_q, col_k = st.columns([4, 1])
        with col_q:
            query = st.text_input("Query", placeholder="e.g. What is CMMI V2.0?")
        with col_k:
            top_k = st.number_input("Top K", 1, 10, 3)

        use_filter = st.checkbox("Use metadata filter")
        metadata_filter = None
        if use_filter:
            fc1, fc2 = st.columns(2)
            fkey = fc1.text_input("Filter key", "source")
            fval = fc2.text_input("Filter value", "cmmi_nhom2.md")
            if fkey and fval:
                metadata_filter = {fkey: fval}

        if st.button("Search", type="primary") and query:
            with st.spinner("Searching..."):
                if metadata_filter:
                    results = store.search_with_filter(query, top_k=top_k, metadata_filter=metadata_filter)
                else:
                    results = store.search(query, top_k=top_k)

            if not results:
                st.warning("No results found.")
            else:
                for i, r in enumerate(results, 1):
                    score = r.get("score", 0)
                    source = r.get("metadata", {}).get("source", "unknown")
                    chunk_idx = r.get("metadata", {}).get("chunk_index", "?")
                    with st.expander(f"#{i} — score: {score:.4f} | {source} [chunk {chunk_idx}]", expanded=True):
                        st.write(r["content"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Similarity Explorer
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Similarity Explorer")
    st.caption("Compare two texts using Cosine similarity and Euclidean distance.")

    embedder = get_embedder(embedder_choice)

    col_a, col_b = st.columns(2)
    with col_a:
        text_a = st.text_area("Text A", "CMMI giúp cải thiện quy trình phần mềm", height=120)
    with col_b:
        text_b = st.text_area("Text B", "Mô hình trưởng thành năng lực tích hợp hỗ trợ tổ chức", height=120)

    if st.button("Compute", type="primary"):
        with st.spinner("Embedding..."):
            vec_a = embedder(text_a)
            vec_b = embedder(text_b)
            cos = compute_similarity(vec_a, vec_b)
            euc = euclidean(vec_a, vec_b)

        c1, c2, c3 = st.columns(3)
        c1.metric("Cosine Similarity", f"{cos:.4f}",
                  help="Range [-1, 1]. Closer to 1 = more similar meaning.")
        c2.metric("Euclidean Distance", f"{euc:.4f}",
                  help="Range [0, ∞). Closer to 0 = more similar.")
        c3.metric("Embedding dim", len(vec_a))

        st.divider()

        # Visual score bar
        st.markdown("**Cosine similarity scale**")
        norm = (cos + 1) / 2  # map [-1,1] → [0,1] for progress bar
        st.progress(norm)
        if cos > 0.7:
            st.success("High similarity — texts are semantically close.")
        elif cos > 0.4:
            st.warning("Moderate similarity.")
        else:
            st.error("Low similarity — texts are semantically distant.")

        # Multi-pair batch
        st.divider()
        st.subheader("Batch comparison")
        st.caption("Enter multiple text pairs to compare at once.")

        n_pairs = st.number_input("Number of pairs", 2, 6, 3)
        pairs_data = []
        for i in range(int(n_pairs)):
            ca, cb = st.columns(2)
            pa = ca.text_input(f"Pair {i+1} — Text A", key=f"pa_{i}")
            pb = cb.text_input(f"Pair {i+1} — Text B", key=f"pb_{i}")
            pairs_data.append((pa, pb))

        if st.button("Compare all pairs"):
            rows = []
            for pa, pb in pairs_data:
                if pa and pb:
                    va, vb = embedder(pa), embedder(pb)
                    rows.append({
                        "Text A": pa[:60],
                        "Text B": pb[:60],
                        "Cosine": round(compute_similarity(va, vb), 4),
                        "Euclidean": round(euclidean(va, vb), 4),
                    })
            if rows:
                st.dataframe(rows, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Agent Q&A
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Agent Q&A (RAG)")

    if "store" not in st.session_state:
        st.info("Go to **Documents & Chunks** tab and click **Chunk & Index** first.")
    else:
        from src.agent import KnowledgeBaseAgent

        def demo_llm(prompt: str) -> str:
            context_part = prompt.split("Question:")[0].replace("Context:", "").strip()
            question_part = prompt.split("Question:")[-1].split("Answer:")[0].strip()
            chunks_preview = "\n".join(
                f"- {line[:120]}" for line in context_part.split("\n---\n") if line.strip()
            )
            return (
                f"**[Demo LLM — no real AI]**\n\n"
                f"Based on the retrieved context, here is a summary answer to: _{question_part}_\n\n"
                f"Retrieved context chunks used:\n{chunks_preview}"
            )

        agent = KnowledgeBaseAgent(store=st.session_state["store"], llm_fn=demo_llm)

        question = st.text_input("Ask a question", placeholder="e.g. Maturity Level trong CMMI là gì?")
        agent_top_k = st.slider("Chunks to retrieve", 1, 10, 3, key="agent_k")

        if st.button("Ask", type="primary") and question:
            with st.spinner("Retrieving and generating..."):
                results = st.session_state["store"].search(question, top_k=agent_top_k)
                answer = agent.answer(question, top_k=agent_top_k)

            st.markdown("### Answer")
            st.markdown(answer)

            st.divider()
            st.markdown("### Retrieved chunks used")
            for i, r in enumerate(results, 1):
                score = r.get("score", 0)
                source = r.get("metadata", {}).get("source", "?")
                with st.expander(f"Chunk #{i} — score {score:.4f} | {source}", expanded=i == 1):
                    st.write(r["content"])
