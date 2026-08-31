"""
Embedding provider abstraction for Phase 5.

Each provider implements embed_query(text) -> list[float] and
exposes a COLLECTION class attribute naming its Chroma collection.

rag.py accepts an optional embedder; defaults to CohereEmbedder.
"""

import os


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


class PubMedBertEmbedder:
    COLLECTION = "cds_conditions_pubmedbert"
    _MODEL_NAME = "pritamdeka/S-PubMedBert-MS-MARCO"

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(self._MODEL_NAME)

    def embed_query(self, text: str) -> list:
        return self._model.encode(text).tolist()
