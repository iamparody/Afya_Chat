# CDS pipeline orchestration
#
# Targets:
#   make ingest          — parse condition cards → chunks.jsonl + graph_entities.jsonl
#   make neo4j-up        — start local Neo4j (Docker) and wait until ready
#   make load-neo4j      — load graph_entities.jsonl → Neo4j AuraDB
#   make embed           — embed chunks.jsonl → Chroma vector store
#   make eval            — run 8-case RAG evaluation harness (exits non-zero if < 7/8)
#   make eval-disam      — run 5-case disambiguation evaluation harness (exits non-zero if < 4/5)
#   make eval-reasoning  — run 10-dim reasoning evaluation, deterministic gate (exits non-zero if < 90%)
#   make pipeline        — run all stages in sequence with failure propagation
#
# Credentials: loaded from .env (local) or environment variables (CI)
# Run from the cds/ root directory.

PYTHON ?= python

.PHONY: neo4j-up ingest load-neo4j embed eval eval-disam eval-reasoning pipeline

# Start local Neo4j in Docker (writes NEO4J_* to .env on first run)
neo4j-up:
	bash scripts/neo4j_local_setup.sh

ingest:
	$(PYTHON) corpus_pipeline/ingest_yaml.py corpus/

load-neo4j:
	$(PYTHON) neo4j/neo4j_loader.py

embed:
	$(PYTHON) chroma/chroma_loader.py

eval:
	$(PYTHON) phase5/evaluate.py

eval-disam:
	$(PYTHON) phase8/evaluate_disambiguation.py

eval-reasoning:
	$(PYTHON) phase8/evaluate_reasoning.py --no-judge --gate 90

pipeline: ingest load-neo4j embed eval eval-disam eval-reasoning
