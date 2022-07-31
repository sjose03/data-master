#!/bin/bash
/opt/spark-3.2.2-bin-hadoop2.7/bin/spark-submit \
--master local[*] \
--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.2.1,org.elasticsearch:elasticsearch-spark-30_2.12:7.12.0  \
--archives /pyspark_venv.tar.gz#environment \
--jars /httpclient-3.1.0.jar /spark_stream.py
