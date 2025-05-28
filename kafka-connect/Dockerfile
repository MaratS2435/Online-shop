# kafka-connect/Dockerfile
FROM confluentinc/cp-kafka-connect:7.8.0

# --------------------------------------------------------------------
# 1. ClickHouse JDBC
RUN confluent-hub install --no-prompt clickhouse/clickhouse-kafka-connect:latest

# --------------------------------------------------------------------
# 2. Debezium ⟶ больше никакой Java-11 ошибки
RUN confluent-hub install --no-prompt debezium/debezium-connector-postgresql:3.0.8

# --------------------------------------------------------------------
# 3. OpenSearch sink
USER root
RUN microdnf install -y unzip curl && microdnf clean all \
 && mkdir -p /usr/share/confluent-hub-components/opensearch-connector \
 && curl -fL -o /tmp/opensearch.zip \
      https://github.com/Aiven-Open/opensearch-connector-for-apache-kafka/releases/download/v3.1.1/opensearch-connector-for-apache-kafka-3.1.1.zip \
 && unzip /tmp/opensearch.zip -d /tmp/opensearch \
 && mv /tmp/opensearch/opensearch-connector-for-apache-kafka-3.1.1/*.jar \
      /usr/share/confluent-hub-components/opensearch-connector/ \
 && rm -rf /tmp/opensearch /tmp/opensearch.zip
USER appuser

RUN confluent-hub install --no-prompt confluentinc/connect-transforms:latest
RUN confluent-hub install --no-prompt jcustenborder/kafka-connect-transform-common:latest


# где лежат плагины
ENV CONNECT_PLUGIN_PATH="/usr/share/confluent-hub-components:/usr/share/confluent-hub-components/opensearch-connector"
CMD ["/etc/confluent/docker/run"]
