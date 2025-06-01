import os
import re
import json
import boto3
import psycopg2
import logging
from kafka import KafkaConsumer
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, length, current_timestamp
from pyspark.sql.types import DecimalType, IntegerType, StringType
from config import S3_CONFIG, POSTGRES_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/tmp/etl_worker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

KAFKA_TOPIC = "uploads"
KAFKA_SERVER = os.getenv("KAFKA_SERVER", "kafka:9092")
POSTGRES_JAR_PATH = "/opt/bitnami/spark/jars/postgresql-42.6.0.jar"
MAX_LENGTH_DESCRIPTION = 20


def download_from_s3(file_name):
    session = boto3.session.Session()
    s3 = session.client(
        service_name="s3",
        endpoint_url=S3_CONFIG["endpoint_url"],
        aws_access_key_id=S3_CONFIG["aws_access_key_id"],
        aws_secret_access_key=S3_CONFIG["aws_secret_access_key"],
    )
    obj = s3.get_object(Bucket=S3_CONFIG["bucket_name"], Key=file_name)
    return obj["Body"].read()


def extract_user_id(file_name):
    match = re.search(r"user_(\d+)", file_name)
    return int(match.group(1)) if match else None


def create_spark_session():
    spark = SparkSession.builder \
        .appName("ETL Worker") \
        .config("spark.jars", POSTGRES_JAR_PATH) \
        .getOrCreate()

    hadoop_conf = spark._jsc.hadoopConfiguration()
    hadoop_conf.set("fs.s3a.access.key", S3_CONFIG["aws_access_key_id"])
    hadoop_conf.set("fs.s3a.secret.key", S3_CONFIG["aws_secret_access_key"])
    hadoop_conf.set("fs.s3a.endpoint", S3_CONFIG["endpoint_url"])
    hadoop_conf.set("fs.s3a.path.style.access", "true")

    return spark


def process_file(file_name: str):
    try:
        logger.info(f"Start processing file: {file_name}")
        spark = create_spark_session()

        file_bytes = download_from_s3(file_name)
        local_path = f"/tmp/{file_name}"
        with open(local_path, "wb") as f:
            f.write(file_bytes)
        logger.info(f"Downloaded file to {local_path}")

        df = spark.read.option("header", "true").csv(local_path)
        logger.info(f"Read CSV into DataFrame with {df.count()} rows")

        user_id = extract_user_id(file_name)

        df_clean = (
            df.withColumn("price", col("price").cast(DecimalType(12, 2)))
              .withColumn("quantity_in_stock", col("quantity_in_stock").cast(IntegerType()))
              .withColumn("user_id", lit(user_id))
              .withColumn("created_at", current_timestamp())
              .withColumn("description", col("description").cast(StringType()))
              .filter(col("name").isNotNull() & col("price").isNotNull() & col("quantity_in_stock").isNotNull())
              .filter(col("price") > 0)
              .filter(length(col("description")) <= MAX_LENGTH_DESCRIPTION)
        )
        logger.info(f"Filtered DataFrame has {df_clean.count()} rows")

        jdbc_url = f"jdbc:postgresql://{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['dbname']}"

        existing_df = spark.read \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", "products") \
            .option("user", POSTGRES_CONFIG["user"]) \
            .option("password", POSTGRES_CONFIG["password"]) \
            .load() \
            .select("name", "user_id", "price", "quantity_in_stock")

        df_new = df_clean.alias("new")
        df_existing = existing_df.alias("existing")

        to_update_with_qty = (
            df_new.join(df_existing, (col("new.name") == col("existing.name")) & (col("new.user_id") == col("existing.user_id")))
                  .filter(col("new.quantity_in_stock") > 0)
                  .select(
                      col("new.name"),
                      col("new.user_id"),
                      col("new.price"),
                      (col("existing.quantity_in_stock") + col("new.quantity_in_stock")).alias("quantity_in_stock"),
                      col("new.description"),
                      col("new.created_at")
                  )
        )

        to_update_only_price = (
            df_new.join(df_existing, (col("new.name") == col("existing.name")) & (col("new.user_id") == col("existing.user_id")))
                  .filter(col("new.quantity_in_stock") == 0)
                  .select(
                      col("new.name"),
                      col("new.user_id"),
                      col("new.price"),
                      col("existing.quantity_in_stock"),
                      col("new.description"),
                      col("new.created_at")
                  )
        )

        to_insert = (
            df_new.join(df_existing, (col("new.name") == col("existing.name")) & (col("new.user_id") == col("existing.user_id")), "left_anti")
                  .filter(col("new.quantity_in_stock") > 0)
                  .select("new.name", "new.user_id", "new.price", "new.quantity_in_stock", "new.description", "new.created_at")
        )

        logger.info(f"Rows to insert: {to_insert.count()}")
        logger.info(f"Rows to update (qty): {to_update_with_qty.count()}")
        logger.info(f"Rows to update (price): {to_update_only_price.count()}")

        cols_to_save = ["name", "user_id", "price", "quantity_in_stock", "description", "created_at"]

        if to_insert.count() > 0:
            to_insert.select(*cols_to_save).write \
                .format("jdbc") \
                .option("url", jdbc_url) \
                .option("dbtable", "products") \
                .option("user", POSTGRES_CONFIG["user"]) \
                .option("password", POSTGRES_CONFIG["password"]) \
                .mode("append") \
                .save()
            logger.info("Inserted new records into products")

        if to_update_with_qty.count() > 0 or to_update_only_price.count() > 0:
            to_update = to_update_with_qty.union(to_update_only_price)
            temp_table = "temp_products_update"
            to_update.write \
                .format("jdbc") \
                .option("url", jdbc_url) \
                .option("dbtable", temp_table) \
                .option("user", POSTGRES_CONFIG["user"]) \
                .option("password", POSTGRES_CONFIG["password"]) \
                .mode("overwrite") \
                .save()
            logger.info("Wrote updated records to temporary table")

            conn = psycopg2.connect(
                host=POSTGRES_CONFIG["host"],
                port=POSTGRES_CONFIG["port"],
                dbname=POSTGRES_CONFIG["dbname"],
                user=POSTGRES_CONFIG["user"],
                password=POSTGRES_CONFIG["password"]
            )
            conn.autocommit = True
            cur = conn.cursor()

            merge_sql = """
            UPDATE products SET
                price = temp.price,
                quantity_in_stock = temp.quantity_in_stock,
                description = temp.description,
                created_at = temp.created_at
            FROM temp_products_update AS temp
            WHERE products.name = temp.name AND products.user_id = temp.user_id
            """
            cur.execute(merge_sql)
            cur.close()
            conn.close()
            logger.info("Merged updates into products table")

        spark.stop()
        logger.info(f"Finished processing file: {file_name}")

    except Exception as e:
        logger.exception(f"Error while processing file {file_name}: {str(e)}")


def main():
    try:
        logger.info("ETL worker started. Waiting for Kafka messages...")

        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_SERVER,
            auto_offset_reset="earliest",
            group_id="etl-group",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        for message in consumer:
            try:
                data = message.value
                file_name = data["file_name"]
                logger.info(f"Received message with file: {file_name}")
                process_file(file_name)
            except Exception as e:
                logger.exception(f"Error processing Kafka message: {str(e)}")

    except Exception as e:
        logger.exception(f"Fatal error in main loop: {str(e)}")


if __name__ == "__main__":
    main()
