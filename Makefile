# CDS pipeline orchestration
#
# Targets:
#   make ingest       — parse condition cards → chunks.jsonl + graph_entities.jsonl
#   make load-neo4j   — load graph_entities.jsonl → Neo4j AuraDB
#   make embed        — embed chunks.jsonl → Chroma vector store
#   make eval         — run 8-case RAG evaluation harness (exits non-zero if < 7/8)
#   make eval-disam   — run 5-case disambiguation evaluation harness (exits non-zero if < 4/5)
#   make pipeline     — run all stages in sequence with failure propagation
#
# Credentials: loaded from .env (local) or environment variables (CI)
# Run from the cds/ root directory.

PYTHON ?= python

.PHONY: ingest load-neo4j embed eval eval-disam pipeline

ingest:
	$(PYTHON) ingest.py

load-neo4j:
	$(PYTHON) neo4j/neo4j_loader.py

embed:
	$(PYTHON) chroma/chroma_loader.py

eval:
	$(PYTHON) phase5/evaluate.py

eval-disam:
	$(PYTHON) phase8/evaluate_disambiguation.py

pipeline: ingest load-neo4j embed eval eval-disam
