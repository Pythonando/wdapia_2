ARG ELASTIC_VERSION=8.17.0
FROM docker.elastic.co/elasticsearch/elasticsearch:${ELASTIC_VERSION}

COPY --chown=elasticsearch:root elasticsearch.yml /usr/share/elasticsearch/config/elasticsearch.yml
