FROM apache/airflow:2.10.5-python3.11

USER root
RUN apt-get update \
    && apt-get install --yes --no-install-recommends openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

USER airflow
COPY airflow/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV EARNEST_PROJECT_ROOT=/opt/earnest
ENV PYTHONPATH=/opt/earnest:/opt/earnest/spark
