ARG ELASTIC_VERSION=8.17.0
FROM docker.elastic.co/beats/heartbeat:${ELASTIC_VERSION}

USER root
COPY --chown=root:heartbeat heartbeat.yml /usr/share/heartbeat/heartbeat.yml
RUN chmod go-w /usr/share/heartbeat/heartbeat.yml

CMD ["heartbeat", "-e", "--strict.perms=false"]
