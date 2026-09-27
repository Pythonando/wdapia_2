ARG ELASTIC_VERSION=8.17.0
FROM docker.elastic.co/beats/metricbeat:${ELASTIC_VERSION}

USER root
COPY --chown=root:metricbeat metricbeat.yml /usr/share/metricbeat/metricbeat.yml
RUN chmod go-w /usr/share/metricbeat/metricbeat.yml

CMD ["metricbeat", "-e", "--strict.perms=false", "--system.hostfs=/hostfs"]
