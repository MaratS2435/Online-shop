# Online-shop

## Запуск
```bash
git clone <this‑repo>
cd online‑shop
# 1) Запускаем всё
docker compose up -d --build
# 2) Проверяем
open http://localhost:8000/docs     # swagger shop
open http://localhost:9200          # OpenSearch
open http://localhost:3000          # Grafana (login admin / admin)
open http://localhost:5601          # OpenSearch Dashboards
```
Остальные URL пока смотрите в docker-compose.yml
## sql для postgres (коннектор debezium)
```sql
ALTER ROLE shop WITH REPLICATION;
CREATE PUBLICATION shop_products_pub FOR TABLE public.products;
```

## sql для clickhouse (коннектор clickhouse)
```sql
CREATE TABLE user_events (
    user_id     UInt64,
    action      String,
    product_id  UInt64,
    time        DateTime
)
ENGINE = MergeTree()
ORDER BY (time);
```

## Регистрация коннекторов
Из папки `kafka-connect/connectors` выполним
```bash
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @opensearch-sink.json
  
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @opensearch-events-sink.json 
  
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @debezium-postgres.json
```
Проверка
```bash
curl -X GET http://localhost:8083/connectors
```
```sql
-- Проверить репликационные слоты
SELECT slot_name, plugin, slot_type, active FROM pg_replication_slots;

-- Проверить публикации
SELECT * FROM pg_publication;
```

## OpenSearch аналитика
Проверка, летят ли в топик пользовательские события
```bash
docker exec -it kafka   /opt/bitnami/kafka/bin/kafka-console-consumer.sh   --bootstrap-server kafka:9092   --topic raw-events   --from-beginning   --timeout-ms 5000
```
