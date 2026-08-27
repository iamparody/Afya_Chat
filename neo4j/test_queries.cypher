// CDS — Test Retrieval Queries
// Run these in AuraDB Query tab or via neo4j/run_queries.py

// 1. Count loaded nodes by label
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS total ORDER BY total DESC;

// 2. Given symptoms [fever, headache, rigors] — ranked candidate conditions
MATCH (c:Condition)-[:HAS_CARDINAL_SYMPTOM|HAS_ASSOCIATED_SYMPTOM]->(s:Symptom)
WHERE s.name IN ["fever", "headache", "rigors"]
RETURN c.name AS condition, c.icd11 AS icd11, count(s) AS matched_symptoms
ORDER BY matched_symptoms DESC;

// 3. Differentials for malaria
MATCH (:Condition {name: "Malaria (unspecified)"})-[:HAS_DIFFERENTIAL]->(d:Condition)
RETURN d.name AS differential;

// 4. Red flags for a condition
MATCH (:Condition {name: "Community-acquired pneumonia"})-[:HAS_RED_FLAG]->(f:RedFlag)
RETURN f.name AS red_flag;

// 5. Conditions sharing a risk factor (HIV infection)
MATCH (c:Condition)-[:HAS_RISK_FACTOR]->(r:RiskFactor {name: "HIV infection"})
RETURN c.name AS condition;

// 6. Full profile for one condition
MATCH (c:Condition {name: "Pulmonary tuberculosis"})
OPTIONAL MATCH (c)-[:HAS_CARDINAL_SYMPTOM]->(cs:Symptom)
OPTIONAL MATCH (c)-[:HAS_RED_FLAG]->(rf:RedFlag)
OPTIONAL MATCH (c)-[:HAS_DIFFERENTIAL]->(d:Condition)
RETURN c.name, collect(DISTINCT cs.name) AS cardinal_symptoms,
       collect(DISTINCT rf.name) AS red_flags,
       collect(DISTINCT d.name) AS differentials;
