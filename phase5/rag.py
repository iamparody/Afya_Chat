"""
Phase 5 RAG — orchestrator.

Four responsibilities only:
1. Receive patient presentation
2. Run retrieval (vector candidates → graph profiles → filtered vector passages)
3. Build context and call LLM via provider
4. Validate returned JSON against OUTPUT_SCHEMA — fail closed

Clinical logic lives in prompts.py. Provider logic lives in providers.py.
This file orchestrates only.
"""

import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import chromadb
import jsonschema
from neo4j import GraphDatabase

_LOG = logging.getLogger("cds.rag.decision")


def _log(stage: str, payload: dict) -> None:
    """Emit one structured decision-path log line. No behaviour change."""
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("%s %s", stage, json.dumps(payload, ensure_ascii=False, default=str))

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))   # ensures phase7 package is importable from any calling context
load_dotenv(ROOT / ".env")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from phase7.context_engine import ContextResult, get_environmental_evidence
from phase7.comorbidity_engine import get_comorbidity_alerts

from prompts import SYSTEM_PROMPT, OUTPUT_SCHEMA, build_context
from providers import get_provider
from presentation_map import classify as _map_classify, get_map_candidates as _map_get_candidates

CHROMA_DIR       = ROOT / "chroma" / "db"
CHUNKS_PATH      = ROOT / "corpus_pipeline" / "output" / "chunks.jsonl"
TOP_N_CANDIDATES = 9
TOP_N_PASSAGES   = 5  # per candidate — wider window to ensure red flag + diagnostic sections are included
RRF_K            = 60  # Cormack et al. 2009 standard default — swept in Phase 5b calibration


# ── BM25 tokeniser + singleton ────────────────────────────────────────────────

_STOPWORDS = frozenset({
    # general
    "the", "and", "with", "for", "this", "that", "from", "may", "can",
    "are", "has", "have", "been", "will", "its", "also", "such", "due",
    "more", "both", "into", "than", "often", "most", "other", "which",
    "when", "does",
    # corpus boilerplate (section headers, card metadata)
    "symptoms", "features", "diagnosis", "diagnostic", "patient", "clinical",
    "associated", "common", "typically", "present", "usually", "include",
    "condition",
})

def _tokenize(text: str) -> list:
    tokens = re.findall(r"[a-z0-9][a-z0-9'/\-]*", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 2]


_bm25_cache: dict = {}   # {"hash": str, "index": BM25Okapi, "chunks": list}

def _get_bm25():
    """Return cached BM25 index, rebuilding if chunks.jsonl has changed."""
    from rank_bm25 import BM25Okapi
    raw = CHUNKS_PATH.read_bytes()
    h = hashlib.md5(raw).hexdigest()
    if _bm25_cache.get("hash") == h:
        return _bm25_cache["index"], _bm25_cache["chunks"]
    chunks = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    corpus = [_tokenize(c["text"]) for c in chunks]
    index = BM25Okapi(corpus)
    _bm25_cache.update({"hash": h, "index": index, "chunks": chunks})
    return index, chunks


# ── Retrieval: BM25 + RRF ─────────────────────────────────────────────────────

def _bm25_candidates(presentation: str, n: int = TOP_N_CANDIDATES) -> list:
    """Return top-n condition names by BM25 score."""
    index, chunks = _get_bm25()
    tokens = _tokenize(presentation)
    scores = index.get_scores(tokens)
    ranked = sorted(enumerate(scores), key=lambda x: -x[1])
    seen: dict = {}
    for idx, _score in ranked:
        cond = chunks[idx]["metadata"]["condition"]
        if cond not in seen:
            seen[cond] = True
        if len(seen) >= n:
            break
    return list(seen.keys())


def _rrf_candidates(
    dense_list: list,
    bm25_list: list,
    n: int = TOP_N_CANDIDATES,
    k: int = RRF_K,
) -> list:
    """Reciprocal Rank Fusion of dense and BM25 candidate lists."""
    scores: dict = {}
    for rank, cond in enumerate(dense_list):
        scores[cond] = scores.get(cond, 0.0) + 1.0 / (k + rank)
    for rank, cond in enumerate(bm25_list):
        scores[cond] = scores.get(cond, 0.0) + 1.0 / (k + rank)
    ranked = sorted(scores, key=lambda c: -scores[c])
    return ranked[:n]


# ── Retrieval: vector candidate generation ────────────────────────────────────

def get_vector_candidates(embedder, collection, presentation, n=TOP_N_CANDIDATES, query_embedding=None):
    """Unrestricted semantic search → top N unique conditions.

    Uses a large n_results pool to ensure n unique conditions are found even
    when a small number of conditions dominate the top-k chunk rankings.
    With 9 chunks per condition, worst-case requires (n-1)*9+1 results to
    guarantee n unique conditions; 500 safely covers any realistic corpus size.

    query_embedding: optional precomputed embedding of `presentation` — pass this
    when the caller already embedded the same text elsewhere in the same request
    (see run()), to avoid a redundant Cohere call. Computed here if not supplied.
    """
    emb = query_embedding if query_embedding is not None else embedder.embed_query(presentation)

    results = collection.query(
        query_embeddings=[emb],
        n_results=min(500, collection.count()),
        include=["metadatas"],
    )

    seen = {}
    for meta in results["metadatas"][0]:
        condition = meta["condition"]
        if condition not in seen:
            seen[condition] = True
        if len(seen) >= n:
            break

    return list(seen.keys())


# ── Retrieval: graph profiles ─────────────────────────────────────────────────

SYMPTOMS_QUERY = """
MATCH (c:Condition {name: $condition})-[:HAS_CARDINAL_SYMPTOM|HAS_ASSOCIATED_SYMPTOM]->(s:Symptom)
RETURN s.name AS symptom
"""

ARGUES_AGAINST_QUERY = """
MATCH (c:Condition {name: $condition})-[:ARGUES_AGAINST]->(s:Symptom)
RETURN s.name AS feature
"""

def get_graph_profile(session, condition):
    symptoms       = [r["symptom"]  for r in session.run(SYMPTOMS_QUERY, condition=condition)]
    argues_against = [r["feature"]  for r in session.run(ARGUES_AGAINST_QUERY, condition=condition)]
    return symptoms, argues_against


def count_overlap(presentation_lower, terms):
    return [t for t in terms if t.lower() in presentation_lower]


# ── Retrieval: filtered vector passages ───────────────────────────────────────

RED_FLAG_SECTION = "red_flags"  # must match section key from ingest.py
AGAINST_SECTION  = "against"    # "Features that argue against this diagnosis" — must match section key from ingest.py

FORCED_SECTIONS = (RED_FLAG_SECTION, AGAINST_SECTION)

def get_filtered_passages(embedder, collection, presentation, conditions, query_embedding=None):
    """
    Semantic search restricted to the graph's top candidates.
    Red flags and argues-against sections are always retrieved FIRST per
    condition — positional primacy ensures the LLM sees both regardless of
    presentation similarity. Top-N similarity passages follow.

    query_embedding: optional precomputed embedding of `presentation` — see
    get_vector_candidates(). Computed here if not supplied.
    """
    emb = query_embedding if query_embedding is not None else embedder.embed_query(presentation)

    passages = []
    for condition in conditions:
        # Step 1: fetch forced sections (red flags, argues-against) unconditionally — always first
        for section in FORCED_SECTIONS:
            forced_results = collection.query(
                query_embeddings=[emb],
                n_results=1,
                where={"$and": [{"condition": {"$eq": condition}}, {"section": {"$eq": section}}]},
                include=["documents", "metadatas"],
            )
            if forced_results["documents"][0]:
                passages.append({
                    "condition": forced_results["metadatas"][0][0]["condition"],
                    "section":   forced_results["metadatas"][0][0]["section"],
                    "text":      forced_results["documents"][0][0],
                })

        # Step 2: top-N similarity passages (skip forced sections if already added)
        results = collection.query(
            query_embeddings=[emb],
            n_results=TOP_N_PASSAGES,
            where={"condition": condition},
            include=["documents", "metadatas"],
        )
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            if meta["section"] in FORCED_SECTIONS:
                continue  # already prepended
            passages.append({
                "condition": meta["condition"],
                "section":   meta["section"],
                "text":      doc,
            })

    return passages


# ── Retrieval: router ─────────────────────────────────────────────────────────

class RetrievalRouter:
    """
    Candidate generation seam. Phase 5b: dense vector + BM25 fused via RRF.
    Returns candidates with provenance labels.

    Provenance values:
        "retrieval"      — RRF output (dense only — BM25 agreed but contributed no new candidates)
        "map+retrieval"  — RRF output confirmed by presentation map
        "map-only"       — map candidate not found by RRF (has a corpus card)
    """

    def __init__(self, embedder, collection):
        self.embedder   = embedder
        self.collection = collection

    def get_candidates(self, presentation: str, n: int = TOP_N_CANDIDATES, query_embedding=None) -> list[dict]:
        """
        Return [{condition, source}, ...].

        RRF candidates are listed first (preserving RRF rank as the vector rank signal).
        Map-only candidates are appended at the end.

        source values:
            "retrieval"      — RRF (dense + BM25)
            "map+retrieval"  — RRF output also confirmed by presentation map
            "map-only"       — map candidate not in RRF output

        query_embedding: optional precomputed embedding of `presentation` — see
        get_vector_candidates(). Computed here if not supplied.
        """
        dense_conditions    = get_vector_candidates(
            self.embedder, self.collection, presentation, n, query_embedding=query_embedding
        )
        bm25_conditions     = _bm25_candidates(presentation, n)
        retrieval_conditions = _rrf_candidates(dense_conditions, bm25_conditions, n)
        retrieval_set = set(retrieval_conditions)

        pathway_ids = _map_classify(presentation)
        map_conditions = _map_get_candidates(pathway_ids)
        map_set = set(map_conditions)

        result: list[dict] = []
        for c in retrieval_conditions:
            result.append({
                "condition": c,
                "source": "map+retrieval" if c in map_set else "retrieval",
            })
        for c in map_conditions:
            if c not in retrieval_set:
                result.append({"condition": c, "source": "map-only"})

        return result


# ── Deterministic scoring ─────────────────────────────────────────────────────

# Fusion weights — calibrate from Step 1 log distributions once 10-case run is done.
_VECTOR_WEIGHT = 0.7
_GRAPH_WEIGHT  = 0.3

# Ambiguity threshold — margin below this value means candidates #1 and #2 are
# genuinely competing. Calibrate from Step 1 log distributions.
AMBIGUITY_MARGIN_THRESHOLD = 0.20


def _compute_fused_scores(candidates: list) -> tuple:
    """
    Compute a normalised fused score per candidate and the margin between #1 and #2.

    vector_score : inverted normalised rank — 1.0 for rank 0, decreasing.
    graph_score  : normalised matched_count — 1.0 for the candidate with the most matches.
    fused_score  : weighted sum (vector 70 %, graph 30 %).

    Candidates retain vector rank order — fused score is computed for margin
    and audit purposes only. Sorting by fused score demotes strong graph
    matches (e.g. Malaria) that have moderate vector rank, causing LLM
    positional bias toward vector-dominant candidates. Reorder only after
    weight calibration against the full regression suite.

    Returns (candidates_with_scores, margin).
    """
    n = len(candidates)
    if n == 0:
        return candidates, 1.0

    max_matched = max((c["matched_count"] for c in candidates), default=0) or 1

    for i, c in enumerate(candidates):
        c["vector_score"] = 1.0 - (i / n)
        c["graph_score"]  = c["matched_count"] / max_matched
        c["fused_score"]  = _VECTOR_WEIGHT * c["vector_score"] + _GRAPH_WEIGHT * c["graph_score"]

    margin = (
        candidates[0]["fused_score"] - candidates[1]["fused_score"]
        if n >= 2 else 1.0
    )

    return candidates, margin


# ── Validation ────────────────────────────────────────────────────────────────

_CONF_ORDER = {"low": 0, "moderate": 1, "high": 2}


_HARD_THRESHOLD_TERMS = frozenset({
    "BP below crisis threshold",
    "below crisis threshold",
    "below emergency threshold",
})


def _has_hard_threshold_violation(arguing_against: list) -> bool:
    """Return True if any arguing_against item is a hard threshold violation."""
    for term in arguing_against:
        term_lower = term.lower()
        if any(h.lower() in term_lower for h in _HARD_THRESHOLD_TERMS):
            return True
    return False


def _enforce_arguing_against_ranking(data: dict) -> dict:
    """
    Deterministic post-hoc enforcement of Rule 6.

    Swap the leading candidate when:
    1. The leader has a hard threshold violation in arguing_against[], OR
    2. The leader has arguing_against[] AND a candidate with empty arguing_against[]
       exists at equal or higher confidence.

    For hard threshold violations (Rule 6A), swap to any candidate at equal/higher
    confidence with fewer arguing_against items — replacement need not be empty.
    For ordinary arguing_against matches, the original requirement (empty replacement)
    still applies to avoid over-triggering.

    The LLM populates arguing_against[] only with matched evidence per Rule 3,
    so non-empty arguing_against reliably indicates an argues-against match in
    the patient presentation.
    """
    candidates = data.get("candidates", [])
    if len(candidates) < 2:
        return data

    leading = candidates[0]
    lead_ag = leading.get("arguing_against", [])
    if not lead_ag:
        return data  # Nothing to act on

    lead_conf = _CONF_ORDER.get(leading.get("confidence_level", "low"), 0)
    hard_violation = _has_hard_threshold_violation(lead_ag)

    best_i = None
    best_ag_count = len(lead_ag)

    for i, cand in enumerate(candidates[1:], 1):
        cand_conf = _CONF_ORDER.get(cand.get("confidence_level", "low"), 0)
        if cand_conf < lead_conf:
            continue
        cand_ag = cand.get("arguing_against", [])
        if hard_violation:
            # Hard threshold: swap to candidate with fewer arguing_against items
            if len(cand_ag) < best_ag_count:
                best_ag_count = len(cand_ag)
                best_i = i
        else:
            # Ordinary match: original requirement — replacement must be empty
            if not cand_ag and best_i is None:
                best_i = i

    if best_i is not None:
        cand = candidates[best_i]
        _log("ARGUES_AGAINST_SWAP", {
            "swapped_out":   leading.get("diagnosis"),
            "swapped_in":    cand.get("diagnosis"),
            "hard_violation": hard_violation,
            "reason": (
                "leading has hard threshold violation; replacement has fewer arguing_against items"
                if hard_violation
                else "leading had arguing_against match; replacement has none at >= confidence"
            ),
        })
        candidates[0], candidates[best_i] = candidates[best_i], candidates[0]
        data["leading_candidate"] = candidates[0]["diagnosis"]

    return data


def validate(raw_text: str) -> dict:
    """
    Parse and validate LLM response. Fail closed — no repair attempts.
    Raises ValueError on any failure.
    """
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    try:
        jsonschema.validate(data, OUTPUT_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValueError(f"Schema violation: {e.message}")

    candidate_names = {c["diagnosis"] for c in data["candidates"]}
    if data["leading_candidate"] not in candidate_names:
        raise ValueError(
            f"leading_candidate '{data['leading_candidate']}' not in candidates[]"
        )

    _enforce_arguing_against_ranking(data)

    return data


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run(
    presentation: str,
    embedder=None,
    patient_location: str | None = None,
    patient_exposures: list | None = None,
    encounter_date: datetime | None = None,
    onset_date: datetime | None = None,
    patient_latitude: float | None = None,
    patient_longitude: float | None = None,
) -> dict:
    """
    Full RAG pipeline for a patient presentation.
    Returns validated dict or raises ValueError on failure.

    embedder           : optional embed_provider.CohereEmbedder or GoogleEmbedder.
                         Defaults to CohereEmbedder when not supplied.
    patient_location   : endemic_region vocabulary value (optional); passed to context engine.
    patient_exposures  : list of exposure vocabulary values (optional).
    encounter_date     : datetime of the encounter; defaults to now(). Used as seasonal reference
                         when onset_date is not provided.
    onset_date         : symptom onset datetime (optional); used as seasonal reference if provided.
    patient_latitude   : county centroid latitude from LocationNormalization (optional).
    patient_longitude  : county centroid longitude from LocationNormalization (optional).
                         When both are provided, OpenMeteoProvider fetches raw rainfall features
                         attached to ContextResult for audit.  Signal activation is unaffected.
    """
    if embedder is None:
        from embed_provider import CohereEmbedder
        embedder = CohereEmbedder()

    db       = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col      = db.get_or_create_collection(embedder.COLLECTION)
    driver   = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )
    provider = get_provider()

    try:
        # Embed the presentation once and reuse — get_candidates() and
        # get_filtered_passages() both need it; embedding it separately in each
        # was doubling the Cohere embed-call volume for identical input text.
        query_embedding = embedder.embed_query(presentation)

        # Step 1 — Candidate generation: dense vector search via router
        router = RetrievalRouter(embedder, col)
        router_candidates = router.get_candidates(presentation, query_embedding=query_embedding)

        _log("VECTOR_CANDIDATES", {
            "count": len(router_candidates),
            "ranked": [
                {"rank": i, "condition": rc["condition"], "source": rc["source"]}
                for i, rc in enumerate(router_candidates)
            ],
        })

        # Step 2 — Graph: symptom profiles + argues_against per candidate
        presentation_lower = presentation.lower()
        candidates = []

        with driver.session() as session:
            for rc in router_candidates:
                condition = rc["condition"]
                symptoms, argues_against = get_graph_profile(session, condition)
                matched = count_overlap(presentation_lower, symptoms)
                candidates.append({
                    "condition":        condition,
                    "source":           rc["source"],
                    "matched_count":    len(matched),
                    "matched_symptoms": matched,
                    "argues_against":   argues_against,
                })

        _log("GRAPH_PROFILES", {
            "candidates": [
                {
                    "rank":             i,
                    "condition":        c["condition"],
                    "source":           c["source"],
                    "matched_count":    c["matched_count"],
                    "matched_symptoms": c["matched_symptoms"],
                    "argues_against":   c["argues_against"],
                }
                for i, c in enumerate(candidates)
            ],
        })

        # Do not sort by matched_count — vector order is the primary semantic ranking.
        # Graph data (matched_symptoms, argues_against) is supplemental evidence for the LLM to use.

        # Step 2b — Deterministic fused scores + margin (no re-sort; scores attached in-place)
        candidates, score_margin = _compute_fused_scores(candidates)
        _log("FUSED_SCORES", {
            "score_margin": round(score_margin, 4),
            "ambiguity_threshold": AMBIGUITY_MARGIN_THRESHOLD,
            "is_ambiguous_deterministic": score_margin < AMBIGUITY_MARGIN_THRESHOLD,
            "candidates": [
                {
                    "condition":     c["condition"],
                    "vector_score":  round(c["vector_score"], 4),
                    "graph_score":   round(c["graph_score"], 4),
                    "fused_score":   round(c["fused_score"], 4),
                }
                for c in candidates
            ],
        })


    # Step 3 — Vector: prose passages filtered to candidates only
        top_conditions = [c["condition"] for c in candidates]
        passages = get_filtered_passages(embedder, col, presentation, top_conditions, query_embedding=query_embedding)

        # --- DEBUG LOGGING: COMPACT RETRIEVED EVIDENCE --- (gate: CDS_DEBUG=1)
        if os.environ.get("CDS_DEBUG"):
            print("\n" + "=" * 70)
            print("DEBUG: RETRIEVED EVIDENCE SUMMARY")
            print("=" * 70)
            for i, item in enumerate(passages, 1):
                print(f"\n--- #{i} ({item.get('condition', 'Unknown')} - {item.get('section', 'Unknown')}) ---")
                print(str(item.get('text', ''))[:1000].replace("\n", " ") + "...")

        # # Step 3 — Vector: prose passages filtered to candidates only
        # top_conditions = [c["condition"] for c in candidates]
        # passages = get_filtered_passages(embedder, col, presentation, top_conditions, query_embedding=query_embedding)

        # print("\n" + "=" * 70)
        # print("DEBUG: RETRIEVED EVIDENCE")
        # print("=" * 70)
        # for i, item in enumerate(passages, 1):
        #     print(f"\n--- Retrieved #{i} ---")
        #     print(item)

        # Step 3b — Environmental context (optional; no-op when no location/signals match)
        _enc = encounter_date or datetime.now()
        _env = get_environmental_evidence(
            candidates=top_conditions,
            encounter_date=_enc,
            patient_location=patient_location,
            patient_exposures=patient_exposures or [],
            onset_date=onset_date,
            latitude=patient_latitude,
            longitude=patient_longitude,
        )
        env_evidence = _env.evidence if isinstance(_env, ContextResult) else []

        # Step 3c — Comorbidity context (deterministic; no-op when no triggers match)
        comorbidity_alerts = get_comorbidity_alerts(top_conditions, presentation)

        # # Step 4 — Build context and call LLM
        context = build_context(
            presentation, candidates, passages,
            env_evidence=env_evidence,
            comorbidity_alerts=comorbidity_alerts,
            score_margin=score_margin,
            near_tie=score_margin < AMBIGUITY_MARGIN_THRESHOLD,
        )
        if hasattr(provider, "set_schema"):
            provider.set_schema(OUTPUT_SCHEMA)

        # --- DEBUG LOGGING: FINAL GEMINI PROMPT --- (gate: CDS_DEBUG=1)
        if os.environ.get("CDS_DEBUG"):
            print("\n" + "=" * 70)
            print("DEBUG: FINAL GEMINI PROMPT")
            print("=" * 70)
            print(f"SYSTEM PROMPT:\n{SYSTEM_PROMPT}\n\nUSER CONTEXT:\n{context}")
            print("=" * 70)

        raw     = provider.generate(SYSTEM_PROMPT, context)

        # --- DEBUG LOGGING: FULL GEMINI RESPONSE --- (gate: CDS_DEBUG=1)
        if os.environ.get("CDS_DEBUG"):
            print("\n" + "=" * 70)
            print("DEBUG: FULL GEMINI RESPONSE")
            print("=" * 70)
            print(raw)
            print("=" * 70)

        # Step 4 — Build context and call LLM
        # context = build_context(
        #     presentation, candidates, passages,
        #     env_evidence=env_evidence,
        #     comorbidity_alerts=comorbidity_alerts,
        # )
        # if hasattr(provider, "set_schema"):
        #     provider.set_schema(OUTPUT_SCHEMA)
        # raw     = provider.generate(SYSTEM_PROMPT, context)

        # Step 5 — Validate (fail closed)
        result = validate(raw)

        _log("LLM_DECISION", {
            "leading_candidate": result.get("leading_candidate"),
            "candidates": [
                {
                    "rank":            i,
                    "diagnosis":       c.get("diagnosis"),
                    "confidence_level": c.get("confidence_level"),
                    "arguing_against": c.get("arguing_against", []),
                    "missing_information": c.get("missing_information", []),
                }
                for i, c in enumerate(result.get("candidates", []))
            ],
            "disambiguation_current_logic": result.get("candidates", [{}])[0].get("confidence_level") != "high"
            if result.get("candidates") else None,
        })

        # Attach score margin for disambiguation gate (not part of LLM schema)
        result["_score_margin"] = score_margin

        # Step 6 — Enrich output candidates with retrieval provenance
        # source_map keyed on lowercase condition name; LLM diagnosis field may differ in
        # capitalisation but wording is generally stable.
        source_map = {c["condition"].lower(): c["source"] for c in candidates}
        for cand in result.get("candidates", []):
            diag_lower = cand.get("diagnosis", "").lower()
            cand["retrieval_source"] = source_map.get(diag_lower, "unknown")

        return result

    finally:
        driver.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        presentation = " ".join(sys.argv[1:])
    else:
        presentation = (
            "29M, 4 days fever, chills, headache. Productive cough started yesterday. "
            "Weakness, not eating well. No known illness. Came from Kisumu 10 days ago."
        )

    print(f"Presentation: {presentation}\n")

    try:
        result = run(presentation)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except ValueError as e:
        print(f"FAIL — {e}", file=sys.stderr)
        sys.exit(1)
