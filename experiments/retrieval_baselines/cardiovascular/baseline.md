# Cardiovascular Domain — Phase C Retrieval Baseline

**Status: FROZEN — do not edit after recording. Phase E must use identical fixtures.**

Recorded: 2026-09-24
Corpus: 28 conditions, 252 chunks
Schema version: 2.2 (no retrieval_anchors in any card)
Retrieval config: Dense (Cohere embed-english-v3.0) + BM25 + RRF (K=60), TOP_N=9
Chroma collection: cds_conditions

Fixture definitions: `experiments/retrieval_baselines/cardiovascular/presentations.md`

---

## Pair 1: Essential Hypertension ↔ Hypertensive Crisis

### C1a — Incidental elevated BP, no acute symptoms
**Correct: Essential Hypertension | Confusable: Hypertensive Crisis**

| Retriever | Correct rank | Confusable rank |
|-----------|-------------|----------------|
| Dense     | >10         | 6              |
| BM25      | 2           | 1              |
| RRF       | 6           | 2              |

```
RRF score correct:    0.01639
RRF score confusable: 0.03205
RRF margin:           -0.01566  ← confusable_leads
```

**Finding:** HC outranks Essential Hypertension significantly at all retrievers. Dense completely misses Essential Hypertension (>10). BM25 prefers HC 1:2. RRF gap is large: HC at rank 2, Essential Hypertension at rank 6. Root cause confirmed: "headache + BP" keyword hits HC chunks; Essential Hypertension corpus does not represent the incidental/asymptomatic discovery pattern.

---

### C1b — Persistent hypertension, stable, no end-organ features
**Correct: Essential Hypertension | Confusable: Hypertensive Crisis**

| Retriever | Correct rank | Confusable rank |
|-----------|-------------|----------------|
| Dense     | >10         | >10            |
| BM25      | 4           | 1              |
| RRF       | 9           | 4              |

```
RRF score correct:    0.01587
RRF score confusable: 0.01667
RRF margin:           -0.00080  ← confusable_leads (narrow)
```

**Finding:** Essential Hypertension again loses to HC, but margin is very narrow (-0.00080). Dense retrieval fails both cards. HC wins on BM25 1:4 — "hypertension" keyword hits HC chunks heavily. Essential Hypertension is rank 9 in RRF, just inside TOP_N=9 boundary. This is the most recoverable case.

---

### C1c — Severe acute BP with end-organ involvement
**Correct: Hypertensive Crisis | Confusable: Essential Hypertension**

| Retriever | Correct rank | Confusable rank |
|-----------|-------------|----------------|
| Dense     | >10         | >10            |
| BM25      | 1           | 7              |
| RRF       | 4           | >10            |

```
RRF score correct:    0.01667
RRF score confusable: 0.01515
RRF margin:           +0.00152  ← correct_leads
```

**Finding:** HC correctly retrieved above Essential Hypertension for the emergency presentation. However, HC is only rank 4 in RRF despite being BM25 rank 1 — Dense retrieval fails HC (>10). The system gets this direction right, but with narrow margin and no Dense support.

---

## Pair 2: Pulmonary Embolism ↔ Deep Vein Thrombosis

### C2a — Unilateral limb presentation
**Correct: Deep Vein Thrombosis | Confusable: Pulmonary Embolism**

| Retriever | Correct rank | Confusable rank |
|-----------|-------------|----------------|
| Dense     | >10         | >10            |
| BM25      | 1           | 5              |
| RRF       | 4           | 8              |

```
RRF score correct:    0.01667
RRF score confusable: 0.01562
RRF margin:           +0.00105  ← correct_leads
```

**Finding:** DVT correctly retrieved above PE for the limb presentation. BM25 strongly favours DVT (rank 1 vs 5). RRF margin is narrow (+0.00105). Dense retrieval fails both (>10). Direction is correct but margin is fragile.

---

### C2b — Acute pulmonary presentation
**Correct: Pulmonary Embolism | Confusable: Deep Vein Thrombosis**

| Retriever | Correct rank | Confusable rank |
|-----------|-------------|----------------|
| Dense     | >10         | >10            |
| BM25      | 1           | 3              |
| RRF       | 4           | 6              |

```
RRF score correct:    0.01667
RRF score confusable: 0.01613
RRF margin:           +0.00054  ← correct_leads (very narrow)
```

**Finding:** PE correctly retrieved above DVT but with very narrow margin (+0.00054). BM25 correctly distinguishes (PE rank 1, DVT rank 3) but margin is thin. Dense retrieval fails both. DVT remains close at rank 6 — within the candidates passed to the LLM (TOP_N=9).

---

### C2c — Shared thromboembolic risk language
**Correct: Pulmonary Embolism | Confusable: Deep Vein Thrombosis**

| Retriever | Correct rank | Confusable rank |
|-----------|-------------|----------------|
| Dense     | >10         | >10            |
| BM25      | 1           | 2              |
| RRF       | 4           | 5              |

```
RRF score correct:    0.01667
RRF score confusable: 0.01639
RRF margin:           +0.00028  ← correct_leads (extremely narrow)
```

**Finding:** PE narrowly leads DVT when post-partum + shared risk-factor language is used without explicit limb or pulmonary symptoms. Margin of +0.00028 is the smallest observed — essentially tied. BM25 ranks them 1:2. This fixture will be the hardest to improve and most sensitive to anchor changes.

---

## Summary

| Fixture | Correct card | Status | RRF margin |
|---------|-------------|--------|------------|
| C1a | Essential Hypertension | **confusable_leads** | -0.01566 |
| C1b | Essential Hypertension | **confusable_leads** | -0.00080 |
| C1c | Hypertensive Crisis | correct_leads | +0.00152 |
| C2a | Deep Vein Thrombosis | correct_leads | +0.00105 |
| C2b | Pulmonary Embolism | correct_leads | +0.00054 |
| C2c | Pulmonary Embolism | correct_leads | +0.00028 |

**Critical finding:** Dense retrieval fails all 6 fixtures — both cardiovascular cards rank >10 in dense for every presentation. The system is entirely BM25-dependent for cardiovascular retrieval. Dense embedding does not represent either condition cluster usefully in the current corpus. This is the primary target for Phase D retrieval anchors.

**Pair 1 conclusion:** Essential Hypertension is the broken card. It loses to HC on C1a (large margin, -0.01566) and C1b (narrow, -0.00080). HC correctly leads on C1c. Phase D must improve Essential Hypertension's representation for incidental/asymptomatic/stable patterns without pulling HC down.

**Pair 2 conclusion:** Direction is correct on all three fixtures but margins are fragile (+0.00105, +0.00054, +0.00028). C2c is essentially tied. Phase D anchors for both PE and DVT must widen the margin without flipping the direction.

---

## Phase E — Attempt 1 (2026-09-24) — BLOCKED

**Change tested:** Dedicated `retrieval_context` chunk emitted at ingest time when `retrieval_anchors.positive` is non-empty. Anchor phrases entered the Chroma embedding space for the first time. Corpus: 256 chunks (252 clinical + 4 anchor chunks).

| Fixture | Correct | C baseline margin | E attempt 1 margin | Delta | Result |
|---------|---------|-------------------|--------------------|-------|--------|
| C1a | EH | -0.01566 | -0.00098 | +0.01468 | IMPROVED (margin) — still confusable_leads |
| C1b | EH | -0.00080 | +0.00049 | +0.00129 | **IMPROVED (flipped to correct_leads)** |
| C1c | HC | +0.00152 | +0.00049 | -0.00103 | REGRESSED (margin dropped) |
| C2a | DVT | +0.00105 | -0.00025 | -0.00130 | **REGRESSED (flipped to confusable_leads)** |
| C2b | PE | +0.00054 | +0.00049 | -0.00005 | unchanged (noise) |
| C2c | PE | +0.00028 | +0.00104 | +0.00076 | IMPROVED — Dense >10 → 1 |

**Gate 1 verdict: BLOCKED.** C2a rank regressed (4 → 5, direction flipped). C1c margin regressed.

**Key finding — mechanism validated:** C2c Dense rank >10 → 1 confirms anchor chunks enter the embedding space and influence retrieval. The implementation change is correct.

**Key finding — anchor bleed confirmed:** PE anchors contain `"acute respiratory presentation with thromboembolic risk factors — post-partum or post-surgical"` which matched C2a (DVT-correct, post-flight immobility presentation) and pulled PE above DVT. EH anchors contain `"known hypertensive on antihypertensive medication attending for routine review"` which partially matched C1c (HC-correct, known hypertensive who stopped medication) and narrowed HC's margin.

**Root cause:** Anchors were too broad — they represent the condition category rather than the condition's discriminating clinical phenotype. Phrases shared with the confusable card's presentation vocabulary cause bleed.

**Phase D2 action:** Revise anchors for all 4 cards using domain-level phenotype discriminators. Do not patch individual failing fixtures. Anchor language must represent what makes the presentation uniquely retrieve *this* card over its direct confusable.

---

## Phase E target

For each fixture, Phase E must demonstrate either:
- `rank improved AND margin increased`, OR
- `rank == 1 before and after AND margin increased`

No regression in correct-card rank is permitted.

Minimum acceptable outcome: C1a and C1b move from `confusable_leads` to `correct_leads`. C2a/C2b/C2c margins must increase without direction flip.
