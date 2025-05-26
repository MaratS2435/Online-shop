from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment, DataTypes
from pyflink.table.descriptors import Kafka, Json, Schema

# Init
env = StreamExecutionEnvironment.get_execution_environment()
t_env = StreamTableEnvironment.create(env)

# Kafka source
source_properties = {
    'bootstrap.servers': 'kafka:9092',
    'group.id': 'flink-activity'
}

t_env.execute_sql(
    """
    CREATE TABLE activity (
      product_id BIGINT,
      user_id BIGINT,
      action STRING,
      ts TIMESTAMP_LTZ(3),
      WATERMARK FOR ts AS ts - INTERVAL '3' SECOND
    ) WITH (
      'connector' = 'kafka',
      'topic' = 'activity',
      'properties.bootstrap.servers' = 'kafka:9092',
      'format' = 'json'
    )
    """
)

# Kafka sink (aggregated)  -> topic activity-agg

t_env.execute_sql(
    """
    CREATE TABLE activity_agg_kafka (
      window_start TIMESTAMP_LTZ(3),
      window_end TIMESTAMP_LTZ(3),
      product_id BIGINT,
      views BIGINT,
      buys BIGINT
    ) WITH (
      'connector' = 'kafka',
      'topic' = 'activity-agg',
      'properties.bootstrap.servers' = 'kafka:9092',
      'format' = 'json',
      'sink.partitioner' = 'fixed'
    )
    """
)

# tumbling window 1m

t_env.execute_sql(
    """
    INSERT INTO activity_agg_kafka
    SELECT
      TUMBLE_START(ts, INTERVAL '1' MINUTE) as window_start,
      TUMBLE_END(ts, INTERVAL '1' MINUTE)   as window_end,
      product_id,
      SUM(CASE WHEN action = 'view' THEN 1 ELSE 0 END) as views,
      SUM(CASE WHEN action = 'buy'  THEN 1 ELSE 0 END) as buys
    FROM activity
    GROUP BY TUMBLE(ts, INTERVAL '1' MINUTE), product_id
    """
)

env.execute("Activity Aggregation Job")