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