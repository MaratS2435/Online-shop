# Online-shop

## TL;DR
```bash
git clone <this‑repo>
cd online‑shop
# 1) Запускаем всё
docker compose up -d --build
# 2) Проверяем
open http://localhost:8000/docs     # swagger product‑service
open http://localhost:9200          # OpenSearch
open http://localhost:3000          # Grafana (login admin / admin)
```
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
  -d @debezium-postgres.json
  
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @clickhouse-sink.json
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
