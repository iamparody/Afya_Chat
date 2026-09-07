"""
Embedding provider abstraction for Phase 5.

Each provider implements:
  embed_query(text)    -> list[float]  — for retrieval at query time
  embed_document(text) -> list[float]  — for indexing (task-type aware)
and exposes a COLLECTION class attribute naming its Chroma collection.

rag.py accepts an optional embedder; defaults to GoogleEmbedder.
chroma_loader.py uses embed_document() for corpus indexing.
"""

import os


class GoogleEmbedder:
    COLLECTION = "cds_conditions_google"
    _MODEL = "models/gemini-embedding-001"

    def __init__(self):
        from google import genai
        from google.genai import types
        self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self._types = types

    def embed_query(self, text: str) -> list:
        result = self._client.models.embed_content(
            model=self._MODEL,
            contents=text,
            config=self._types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return list(result.embeddings[0].values)

    def embed_document(self, text: str) -> list:
        result = self._client.models.embed_content(
            model=self._MODEL,
            contents=text,
            config=self._types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        return list(result.embeddings[0].values)


class CohereEmbedder:
    COLLECTION = "cds_conditions"
    _MODEL = "embed-multilingual-v3.0"

    def __init__(self):
        import cohere
        self._co = cohere.Client(os.environ["COHERE_API_KEY"])

    def embed_query(self, text: str) -> list:
        return self._co.embed(
            texts=[text],
            model=self._MODEL,
            input_type="search_query",
        ).embeddings[0]

    def embed_document(self, text: str) -> list:
        return self._co.embed(
            texts=[text],
            model=self._MODEL,
            input_type="search_document",
        ).embeddings[0]

    def embed_documents_batch(self, texts: list, batch_size: int = 96) -> list:
        """Batch embed for indexing — ceil(N/96) API calls instead of N."""
        all_embeddings = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            result = self._co.embed(
                texts=batch,
                model=self._MODEL,
                input_type="search_document",
            )
            all_embeddings.extend(result.embeddings)
        return all_embeddings


class PubMedBertEmbedder:
    COLLECTION = "cds_conditions_pubmedbert"
    _MODEL_NAME = "pritamdeka/S-PubMedBert-MS-MARCO"

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(self._MODEL_NAME)

    def embed_query(self, text: str) -> list:
        return self._model.encode(text).tolist()

    def embed_document(self, text: str) -> list:
        # Sentence transformers are symmetric — same encoding for docs and queries
        return self._model.encode(text).tolist()
