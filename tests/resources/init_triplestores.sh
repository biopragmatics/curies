## Script to initialize the triplestores started with docker
# Run it from the root of the repo: ./tests/resources/init_triplestores.sh

TRIPLES="
<https://identifiers.org/CHEBI:24867> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://w3id.org/biolink/vocab/ChemicalEntity> .
<https://identifiers.org/CHEBI:24868> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://w3id.org/biolink/vocab/ChemicalEntity> .
"

echo "  🪄 Load triples to Virtuoso and enable federated queries"
docker compose exec virtuoso isql -U dba -P dba exec='GRANT "SPARQL_SELECT_FED" TO "SPARQL";'
docker compose exec virtuoso isql -U dba -P dba exec="SPARQL INSERT IN <https://identifiers.org/CHEBI> { $TRIPLES };"

echo "  ⚡️ Load triples to Blazegraph"
docker compose exec blazegraph curl -X POST http://localhost:8080/blazegraph/namespace/kb/sparql -d "update=insert data { $TRIPLES }"

echo "  ☕️ Load triples to Fuseki"
docker compose exec fuseki curl -X POST -u admin:dba -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' 'http://localhost:3030/$/datasets' -d "dbName=mapping&dbType=tdb2"
docker compose exec fuseki curl -X POST http://localhost:3030/mapping -d "update=insert data { $TRIPLES }"
