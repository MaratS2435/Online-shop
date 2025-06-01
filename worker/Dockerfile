FROM bitnami/spark:latest

WORKDIR /app

COPY worker/etl_requirements.txt /app/etl_requirements.txt
RUN pip install --no-cache-dir -r etl_requirements.txt

COPY worker/worker.py /app/worker.py

ENV PYTHONPATH=/app/shop/app
COPY shop/app /app/shop/app

CMD ["python", "worker.py"]
