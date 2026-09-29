#!/usr/bin/env bash
# Set up a local Neo4j (Docker) for CDS: ensures .env has NEO4J_* credentials,
# starts the container, and waits until Bolt accepts connections.
#
# Run from the cds/ root:  bash scripts/neo4j_local_setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."

touch .env
set_var() {  # set_var KEY VALUE — replace if present, append otherwise
  if grep -q "^$1=" .env; then
    sed -i "s|^$1=.*|$1=$2|" .env
  else
    printf '%s=%s\n' "$1" "$2" >> .env
  fi
}

current_pw=$(grep '^NEO4J_PASSWORD=' .env | cut -d= -f2- || true)
if [ -z "$current_pw" ]; then
  if docker volume inspect afya_chat_neo4j_data >/dev/null 2>&1; then
    echo "NEO4J_PASSWORD is empty but a neo4j_data volume exists — its stored password would not match." >&2
    echo "Restore the password in .env, or remove the volume: docker compose down -v" >&2
    exit 1
  fi
  current_pw=$(openssl rand -hex 16)
fi

set_var NEO4J_URI "bolt://localhost:7687"
set_var NEO4J_USERNAME "neo4j"
set_var NEO4J_PASSWORD "$current_pw"

docker compose up -d neo4j

echo -n "Waiting for Neo4j"
for _ in $(seq 1 60); do
  if docker exec cds-neo4j cypher-shell -u neo4j -p "$current_pw" "RETURN 1" >/dev/null 2>&1; then
    echo " — ready."
    echo "Bolt:    bolt://localhost:7687"
    echo "Browser: http://localhost:7474  (user: neo4j, password in .env)"
    exit 0
  fi
  echo -n "."
  sleep 2
done
echo " — timed out. Check: docker compose logs neo4j" >&2
exit 1
