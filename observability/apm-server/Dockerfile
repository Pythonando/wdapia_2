ARG ELASTIC_VERSION=8.17.0
FROM docker.elastic.co/apm/apm-server:${ELASTIC_VERSION}

COPY --chown=apm-server:apm-server apm-server.yml /usr/share/apm-server/apm-server.yml
