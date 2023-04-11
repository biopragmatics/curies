## Script to initialize the triplestores started with docker
# Run it from the root of the repo: ./tests/resources/init_triplestores.sh

# Enable federated query for Virtuoso and load a triple for testing
docker compose exec virtuoso isql -U dba -P dba exec='GRANT "SPARQL_SELECT_FED" TO "SPARQL";'
docker compose exec virtuoso isql -U dba -P dba exec='SPARQL INSERT IN <https://purl.uniprot.org> { <https://purl.uniprot.org/uniprot/P07862> <https://w3id.org/biolink/vocab/category> <https://w3id.org/biolink/vocab/GeneProduct> };'

# Load a triple to local blazegraph for testing
docker compose exec blazegraph curl -X POST http://localhost:8080/blazegraph/namespace/kb/sparql -d 'update=insert data {<http://identifiers.org/ensembl/ENSG00000006453> <https://w3id.org/biolink/vocab/category> <https://w3id.org/biolink/vocab/Gene> . }'
