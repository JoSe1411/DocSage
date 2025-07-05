import faiss
import numpy as np
from typing import List, Dict, Optional
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

class VectorStore:
    def __init__(self, use_chromadb: bool = False):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001"
        )
        self.use_chromadb = use_chromadb
        self.index = None
        self.texts = []
        self.embedded_vectors = None
        
    def create_index(self, texts: List[str]) -> any:
        """Create FAISS or ChromaDB index"""
        self.texts = texts
        vectors = self.embeddings.embed_documents(texts)
        self.embedded_vectors = np.array(vectors).astype('float32')
        self.index = faiss.IndexFlatL2(self.embedded_vectors.shape[1])
        self.index.add(self.embedded_vectors)
        return self.index
        
    def similarity_search(self, query: str, k: int = 5) -> List[Dict]:
        """Find similar chunks for the query"""
        if self.index is None or self.embedded_vectors is None:
            raise ValueError("Index not created. Call create_index first.")
        query_vec = np.array(self.embeddings.embed_query(query)).astype('float32').reshape(1, -1)
        D, I = self.index.search(query_vec, k)
        results = []
        for idx in I[0]:
            if idx < len(self.texts):
                results.append({"content": self.texts[idx], "index": idx})
        return results

    def build_langchain_faiss(self, texts):
        docs = [Document(page_content=t) for t in texts]
        return FAISS.from_documents(docs, self.embeddings)
