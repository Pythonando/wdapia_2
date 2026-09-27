ARG ELASTIC_VERSION=8.17.0
FROM docker.elastic.co/kibana/kibana:${ELASTIC_VERSION}

COPY --chown=kibana:root kibana.yml /usr/share/kibana/config/kibana.yml
