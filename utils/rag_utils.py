"""
RAG for markdown documents.

Strategy (tried in order):
  1. EnhancedMDRAG  — BM25 + Chroma vector + CrossEncoder reranker (local models)
  2. BM25           — pure Python fallback (no local models needed)

EnhancedMDRAG is used only when embedding and reranker model paths are
configured in config.yaml / llm.model_paths and the paths actually exist.
"""
import os
import re
import math
from collections import Counter
from typing import Optional

from utils.ui_logger import ui_print


_K1 = 1.5
_B  = 0.75


def _tokenize(text: str) -> list[str]:
    return re.findall(r'\w+', text.lower())


def _split_by_headers(text: str, source: str) -> list[tuple[str, str]]:
    """Split markdown into chunks at ## headings. Returns (title, content) pairs."""
    chunks: list[tuple[str, str]] = []
    current_title = source
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    chunks.append((current_title, body))
            current_title = line.lstrip("# ").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            chunks.append((current_title, body))

    # If no ## headers found, fall back to splitting every ~60 lines
    if not chunks:
        lines = text.splitlines()
        for i in range(0, max(1, len(lines)), 60):
            body = "\n".join(lines[i:i + 60]).strip()
            if body:
                chunks.append((f"{source} (part {i // 60 + 1})", body))

    return chunks


def _discover_docs() -> dict[str, str]:
    """Walk static/ and return {name: path} for every *_doc.md file."""
    static_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static"
    )
    found: dict[str, str] = {}
    if not os.path.isdir(static_dir):
        return found
    for root, _, files in os.walk(static_dir):
        for fname in files:
            if fname.endswith("_doc.md"):
                name = fname[: -len("_doc.md")]
                found[name] = os.path.join(root, fname)
    return found


class _BM25Store:
    def __init__(self):
        self._chunks: list[tuple[str, str]] = []   # (title, content)
        self._tokenized: list[list[str]] = []
        self._df: Counter = Counter()
        self._avgdl: float = 0.0
        self._loaded = False

    def _load(self):
        docs = _discover_docs()
        if not docs:
            ui_print("[RAG] No *_doc.md files found under static/")
            self._loaded = True
            return

        for name, path in docs.items():
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
                for title, content in _split_by_headers(text, name):
                    self._chunks.append((title, content))
            except Exception as e:
                ui_print(f"[RAG] Failed to load {path}: {e}")

        self._tokenized = [_tokenize(c) for _, c in self._chunks]
        total_len = sum(len(t) for t in self._tokenized)
        self._avgdl = total_len / max(1, len(self._tokenized))

        for tokens in self._tokenized:
            for term in set(tokens):
                self._df[term] += 1

        ui_print(f"[RAG] Loaded {len(self._chunks)} chunks from {list(docs.keys())}")
        self._loaded = True

    def search(self, query: str, top_k: int = 3) -> Optional[str]:
        if not self._loaded:
            self._load()
        if not self._chunks:
            return None

        q_tokens = _tokenize(query)
        if not q_tokens:
            return None

        N = len(self._chunks)
        scores: list[float] = []

        for i, tokens in enumerate(self._tokenized):
            tf = Counter(tokens)
            dl = len(tokens)
            score = 0.0
            for term in q_tokens:
                if term not in tf:
                    continue
                df = self._df.get(term, 0)
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
                freq = tf[term]
                denom = freq + _K1 * (1 - _B + _B * dl / max(1, self._avgdl))
                score += idf * freq * (_K1 + 1) / denom
            scores.append(score)

        # pick top_k with score > 0
        ranked = sorted(
            ((s, i) for i, s in enumerate(scores) if s > 0),
            reverse=True,
        )[:top_k]

        if not ranked:
            return None

        MAX_CHARS = 4000
        parts = []
        total = 0
        for _, i in ranked:
            title, content = self._chunks[i]
            # Always include at least one chunk; truncate content if oversized
            if not parts and len(content) > MAX_CHARS:
                content = content[:MAX_CHARS] + "\n...(truncated)"
            elif total + len(content) > MAX_CHARS:
                break
            parts.append(f"### {title}\n{content}")
            total += len(content)

        return "\n\n---\n\n".join(parts) if parts else None


_store = _BM25Store()

# ── EnhancedMDRAG (embedding + reranker) ──────────────────────────────────────

_enhanced_rag = None
_enhanced_rag_checked = False


def _try_build_enhanced_rag():
    """Build EnhancedMDRAG once if models are configured; returns instance or None."""
    global _enhanced_rag, _enhanced_rag_checked
    if _enhanced_rag_checked:
        return _enhanced_rag
    _enhanced_rag_checked = True

    try:
        from configs.model_config import llm_model_path
        emb_path    = llm_model_path.get("embedding", "")
        rerank_path = llm_model_path.get("reranker", "")

        if (not emb_path or emb_path.startswith("/path/to/") or not os.path.exists(emb_path) or
                not rerank_path or rerank_path.startswith("/path/to/") or not os.path.exists(rerank_path)):
            ui_print("[RAG] Embedding/reranker models not configured — using BM25")
            return None

        from configs.path_config import WORKFLOWS_DOC, WORKFLOWS_CACHE_DIR
        if not os.path.exists(WORKFLOWS_DOC):
            ui_print(f"[RAG] Doc not found: {WORKFLOWS_DOC} — using BM25")
            return None

        ui_print(f"[RAG] Initializing EnhancedMDRAG (embedding={os.path.basename(emb_path)})...")
        from storage.rag_retriever import EnhancedMDRAG
        _enhanced_rag = EnhancedMDRAG(doc_path=WORKFLOWS_DOC, cache_dir=WORKFLOWS_CACHE_DIR)
        ui_print("[RAG] EnhancedMDRAG ready")
        return _enhanced_rag

    except Exception as e:
        ui_print(f"[RAG] EnhancedMDRAG init failed ({e}) — using BM25")
        return None


def rag_search(query: str, top_k: int = 3) -> Optional[str]:
    """Search loaded docs and return relevant context, or None if nothing found."""
    enhanced = _try_build_enhanced_rag()
    if enhanced is not None:
        try:
            result = enhanced.search(query)
            return result if result and result.strip() else None
        except Exception as e:
            ui_print(f"[RAG] EnhancedMDRAG search failed ({e}) — falling back to BM25")

    return _store.search(query, top_k)
