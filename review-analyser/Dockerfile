FROM python:3.11-slim

RUN apt-get update && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt    # torch качается один раз

WORKDIR /app
COPY review_analyser.py .

ENV HF_HOME=/hf-cache
EXPOSE 8000
CMD ["python", "review_analyser.py"]
