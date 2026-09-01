# CDS pipeline orchestration
#
# Targets:
#   make ingest       — parse condition cards → chunks.jsonl + graph_entities.jsonl
#   make load-neo4j   — load graph_entities.jsonl → Neo4j AuraDB
#   make embed        — embed chunks.jsonl → Chroma vector store
#   make eval         — run 8-case evaluation harness (exits non-zero if < 7/8)
#   make pipeline     — run all four stages in sequence with failure propagation
#
# Credentials: loaded from .env (local) or environment variables (CI)
# Run from the cds/ root directory.

PYTHON ?= python

.PHONY: ingest load-neo4j embed eval pipeline

ingest:
	$(PYTHON) ingest.py

load-neo4j:
	$(PYTHON) neo4j/neo4j_loader.py

embed:
	$(PYTHON) chroma/chroma_loader.py

eval:
	$(PYTHON) phase5/evaluate.py

pipeline: ingest load-neo4j embed eval
