"""
Hybrid BM25 + Vector RAG retriever with reranker.
Adapted from the agent project's EnhancedMDRAG for methylongAgent.

Falls back gracefully if embedding/reranker models are not configured.
"""
import logging
import os
from typing import List, Optional

import torch

logging.getLogger("transformers").setLevel(logging.ERROR)


def _get_embedding_device() -> str:
    from configs.runtime_config import embedding_args
    device = str(embedding_args.get("device", "cpu")).lower()
    if device in ("cpu",) or device.startswith("cuda"):
        return device
    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return "cpu"


class EnhancedMDRAG:
    """
    Hybrid retriever: BM25 + Chroma vector search + CrossEncoder reranker.
    Initialized once per document; caches the Chroma DB to disk.
    """

    def __init__(self, doc_path: str, cache_dir: Optional[str] = None):
        from langchain_community.retrievers import BM25Retriever
        from langchain_community.vectorstores import Chroma
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
        from langchain_core.documents import Document
        from sentence_transformers import CrossEncoder
        from configs.model_config import llm_model_path

        self.doc_path = doc_path
        device = _get_embedding_device()

        self._embeddings = HuggingFaceEmbeddings(
            model_name=llm_model_path["embedding"],
            model_kwargs={"device": device},
        )
        self._reranker = CrossEncoder(
            model_name_or_path=llm_model_path["reranker"],
            device=device,
        )

        # Build documents
        db_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "vector_db_cache",
            os.path.basename(doc_path).replace(".md", ""),
        )

        header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "H1"), ("##", "H2"), ("###", "H3")]
        )
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=50, separators=["\n\n", "\n", " ", ""]
        )

        from langchain_community.document_loaders import UnstructuredMarkdownLoader
        raw = UnstructuredMarkdownLoader(doc_path).load()
        header_splits = header_splitter.split_text(raw[0].page_content)

        final_docs: List[Document] = []
        for i, parent in enumerate(header_splits):
            for child_text in child_splitter.split_text(parent.page_content):
                cleaned = child_text.strip()
                if not cleaned or len(cleaned) < 10:
                    continue
                if all(c in ' \n\t\r|—–-_*#[](){}' for c in cleaned):
                    continue
                final_docs.append(Document(
                    page_content=cleaned,
                    metadata={**parent.metadata, "doc_id": i},
                ))

        if not final_docs:
            raise ValueError(f"Document is empty, cannot build retriever: {doc_path}")

        os.makedirs(db_dir, exist_ok=True)
        if os.path.exists(db_dir) and os.listdir(db_dir):
            vector_db = Chroma(persist_directory=db_dir, embedding_function=self._embeddings)
        else:
            vector_db = Chroma.from_documents(
                documents=final_docs, embedding=self._embeddings, persist_directory=db_dir
            )

        self._vector = vector_db.as_retriever(search_kwargs={"k": 12})
        self._bm25   = BM25Retriever.from_documents(final_docs)
        self._bm25.k = 12

    def _hybrid_retrieve(self, query: str):
        docs1 = self._vector.invoke(query)
        docs2 = self._bm25.invoke(query)
        seen, merged = set(), []
        for d in docs1 + docs2:
            if d.page_content not in seen:
                merged.append(d)
                seen.add(d.page_content)
        return merged

    def _rerank(self, query: str, docs) -> list:
        if not docs:
            return docs
        pairs  = [(query, d.page_content) for d in docs]
        scores = self._reranker.predict(pairs)
        return [d for _, d in sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)[:6]]

    def search(self, query: str) -> str:
        docs    = self._hybrid_retrieve(query)
        reranked = self._rerank(query, docs)
        parts   = []
        for doc in reranked:
            headers = [doc.metadata[f"H{i}"] for i in range(1, 4) if f"H{i}" in doc.metadata]
            header_path = " > ".join(headers) if headers else "Doc"
            parts.append(f"【来源: {header_path}】\n{doc.page_content}")
        return "\n\n---\n\n".join(parts[:10])
