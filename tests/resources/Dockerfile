FROM python:3.10

# Dockerfile used to spawn a mapping service SPARQL endpoint for testing

WORKDIR /app

ADD . .

RUN pip install -e ".[fastapi,rdflib,bioregistry]"

CMD [ "bioregistry", "web", "--port", "8888", "--host", "0.0.0.0" ]
