ARG IMAGE_VARIANT=slim-buster
ARG OPENJDK_VERSION=8
ARG PYTHON_VERSION=3.9.8

FROM python:${PYTHON_VERSION}-${IMAGE_VARIANT} AS py3
FROM openjdk:${OPENJDK_VERSION}-${IMAGE_VARIANT}

RUN apt-get update && apt-get install -y --no-install-recommends curl

##SPARK
ENV SPARK_VERSION=3.2.1
ENV SPARK_URL=https://www.apache.org/dist/spark/spark-$SPARK_VERSION/spark-$SPARK_VERSION-bin-hadoop2.7.tgz 

RUN set -x \
    && curl -fSL "$SPARK_URL" -o /tmp/spark.tar.gz \
    && tar -xvf /tmp/spark.tar.gz -C /opt/ \
    && rm /tmp/spark.tar.gz*

ENV SPARK_HOME=/opt/spark-$SPARK_VERSION-bin-hadoop2.7
ENV PYSPARK_PYTHON=python3.9

COPY --from=py3 / /

COPY files .

ARG PYSPARK_VERSION=3.2.1
RUN pip --no-cache-dir install TextBlob pyspark==${PYSPARK_VERSION}

ENTRYPOINT ["sh","start-submit.sh"]
