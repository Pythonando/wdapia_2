ARG ELASTIC_VERSION=8.17.0
FROM docker.elastic.co/beats/filebeat:${ELASTIC_VERSION}

USER root
COPY --chown=root:filebeat filebeat.yml /usr/share/filebeat/filebeat.yml
RUN chmod go-w /usr/share/filebeat/filebeat.yml

# Filebeat precisa ler /var/lib/docker/containers e o socket do Docker
CMD ["filebeat", "-e", "--strict.perms=false"]
