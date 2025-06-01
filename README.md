# Online-shop

## Состав команды
| Имя               | Группа      |
|-------------------|-------------|
| Сисенов Марат     | М8О-310Б-22 |
| Андреев Иван      | М8О-310Б-22 |
| Слетюрин Кирилл   | М8О-308Б-22 |
| Цирулев Николай   | М8О-308Б-22 |

## Запуск
```bash
docker compose up -d --build

open http://localhost:8000/docs     # swagger shop
open http://localhost:3000          # Grafana (login admin / admin)
open http://localhost:5601          # OpenSearch Dashboards
open http://localhost:9090          # Prometheus
```
Остальные URL пока смотрите в docker-compose.yml
## sql для postgres (для коннектора debezium CDC)
```sql
ALTER ROLE shop WITH REPLICATION;
```

## Регистрация коннекторов
Из папки `kafka-connect/connectors` выполнить
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
### Подключение dashboards Grafana
Перейдите по ссылке http://localhost:3000. \
Зарегестрируйте 2 индекса OpenSearch. \
В разделе `Data sources` выберите `OpenSearch` и введите `http://opensearch:9200`.
 - **index**: raw-events -- **time field**: timestamp
 - **index**: reviews -- **time field**: analysed_at

Зарегестрируйте Prometheus. \
В разделе `Data sources` выберите `Prometheus` и введите `http://prometheus:9090`.

Зарегестрируйте Loki. \
В разделе `Data sources` выберите `Loki` и введите `http://loki:3100`.

### Импорт дашбордов
В папке `grafana dashboards` лежат все дашборды. \
Перейдите в раздел `Dashboards` в Grafana. \
Нажмите `Import Dashboard` и выберите `JSON` файл. \
Повторите со всеми дашбордами. \
Если запрашиваются Data sources, выберите Выберете один из тех, что зарегистрировали раннее


## OpenSearch аналитика
Проверка, летят ли в топик пользовательские события
```bash
docker exec -it kafka   /opt/bitnami/kafka/bin/kafka-console-consumer.sh   --bootstrap-server kafka:9092   --topic raw-events   --from-beginning   --timeout-ms 5000
```
