## Script to initialize the triplestores started with docker
# Run it from the root of the repo: ./tests/resources/init_triplestores.sh

# Enable federated query for Virtuoso and load a triple for testing
docker compose exec virtuoso isql -U dba -P dba exec='GRANT "SPARQL_SELECT_FED" TO "SPARQL";'
docker compose exec virtuoso isql -U dba -P dba exec='SPARQL INSERT IN <https://identifiers.org/CHEBI> { <https://identifiers.org/CHEBI:24867> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://w3id.org/biolink/vocab/ChemicalEntity> };'

# Load a triple to local blazegraph for testing
docker compose exec blazegraph curl -X POST http://localhost:8080/blazegraph/namespace/kb/sparql -d 'update=insert data {<https://identifiers.org/CHEBI:24867> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://w3id.org/biolink/vocab/ChemicalEntity> . }'
