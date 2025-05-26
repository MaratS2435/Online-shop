FROM flink:1.19-scala_2.12

# Устанавливаем зависимости для сборки Python
RUN apt-get update && \
    apt-get install -y wget build-essential zlib1g-dev libncurses5-dev libgdbm-dev \
    libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev curl libbz2-dev && \
    wget https://www.python.org/ftp/python/3.9.18/Python-3.9.18.tgz && \
    tar -xf Python-3.9.18.tgz && \
    cd Python-3.9.18 && \
    ./configure --enable-optimizations && \
    make -j$(nproc) && \
    make altinstall && \
    cd .. && \
    rm -rf Python-3.9.18 Python-3.9.18.tgz

# Устанавливаем pip и pyflink
RUN python3.9 -m ensurepip && \
    python3.9 -m pip install --upgrade pip && \
    python3.9 -m pip install pyflink==1.19.0

# Копируем ваш Python-скрипт
COPY activity_agg.py /job/

# Запускаем скрипт с python3.9
ENTRYPOINT ["python3.9", "/job/activity_agg.py"]
