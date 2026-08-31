"""
Step 3 — Neo4j graph load verification.

Checks that every condition in graph_entities.jsonl has:
- A Condition node in Neo4j
- HAS_CARDINAL_SYMPTOM edges
- ARGUES_AGAINST edges

Requires live Neo4j connection. Run with: pytest -m integration
Skip with: pytest -m "not integration"
"""

import os
import pytest

from helpers import get_condition_names_from_graph

pytestmark = pytest.mark.integration

CONDITIONS = get_condition_names_from_graph()


@pytest.fixture(scope="module")
def neo4j_session():
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )
    with driver.session() as session:
        yield session
    driver.close()


def test_conditions_loaded_from_graph_jsonl():
    assert len(CONDITIONS) > 0, \
        "No conditions found in graph_entities.jsonl — run ingest.py first"


def test_total_condition_node_count(neo4j_session):
    result = neo4j_session.run("MATCH (c:Condition) RETURN count(c) AS n")
    count = result.single()["n"]
    assert count >= len(CONDITIONS), \
        f"Expected >= {len(CONDITIONS)} Condition nodes, got {count}"


@pytest.mark.parametrize("condition", CONDITIONS)
def test_condition_node_exists(neo4j_session, condition):
    result = neo4j_session.run(
        "MATCH (c:Condition {name: $name}) RETURN count(c) AS n",
        name=condition,
    )
    assert result.single()["n"] == 1, \
        f"Condition node not found in Neo4j: '{condition}'"


@pytest.mark.parametrize("condition", CONDITIONS)
def test_cardinal_symptom_edges_exist(neo4j_session, condition):
    result = neo4j_session.run(
        "MATCH (c:Condition {name: $name})-[:HAS_CARDINAL_SYMPTOM]->() RETURN count(*) AS n",
        name=condition,
    )
    assert result.single()["n"] > 0, \
        f"No HAS_CARDINAL_SYMPTOM edges for '{condition}'"


@pytest.mark.parametrize("condition", CONDITIONS)
def test_argues_against_edges_exist(neo4j_session, condition):
    result = neo4j_session.run(
        "MATCH (c:Condition {name: $name})-[:ARGUES_AGAINST]->() RETURN count(*) AS n",
        name=condition,
    )
    assert result.single()["n"] > 0, \
        f"No ARGUES_AGAINST edges for '{condition}'"


@pytest.mark.parametrize("condition", CONDITIONS)
def test_red_flag_edges_exist(neo4j_session, condition):
    result = neo4j_session.run(
        "MATCH (c:Condition {name: $name})-[:HAS_RED_FLAG]->() RETURN count(*) AS n",
        name=condition,
    )
    assert result.single()["n"] > 0, \
        f"No HAS_RED_FLAG edges for '{condition}'"
