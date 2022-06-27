import os
from textblob import TextBlob
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import *
spark = (SparkSession.builder
   .master("local[3]")
   .appName("streaming")
   .config("spark.es.net.http.auth.user","elastic")
   .config("spark.es.net.http.auth.pass","abcde")
   .config("es.spark.sql.streaming.sink.log.enabled","false")
   .config("spark.es.nodes","http://elasticsearch")
   .config("spark.es.port","9200")
    .config("spark.es.index.auto.create", "true")
   .getOrCreate())

lines = (spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", "kafka:29092")
        .option("subscribe", "twitter_topic_full_en")
        .option("startingOffsets", "earliest")
        .load())


lines_new = lines.select(F.col('value').cast('string'),'timestamp')

schema =  StructType([
    StructField('id',StringType()),
    StructField('lang',StringType()),
    StructField('text',StringType()),
])

lines_new_json = lines_new.select(F.from_json('value',schema).alias('json'),'timestamp')

def preprocessing(lines):
    words = lines.select(F.explode(F.split(lines.value, "t_end")).alias("word"))
    words = words.na.replace('', None)
    words = words.na.drop()
    words = words.withColumn('word', F.regexp_replace('word', r'http\S+', ''))
    words = words.withColumn('word', F.regexp_replace('word', '@\w+', ''))
    words = words.withColumn('word', F.regexp_replace('word', '#', ''))
    words = words.withColumn('word', F.regexp_replace('word', 'RT', ''))
    words = words.withColumn('word', F.regexp_replace('word', ':', ''))
    return words

def polarity_detection(text):
    return TextBlob(text).sentiment.polarity
def subjectivity_detection(text):
    return TextBlob(text).sentiment.subjectivity
def text_classification(words):
    # polarity detection
    polarity_detection_udf = F.udf(polarity_detection, StringType())
    words = words.withColumn("polarity", polarity_detection_udf("word"))
    # subjectivity detection
    subjectivity_detection_udf = F.udf(subjectivity_detection, StringType())
    words = words.withColumn("subjectivity", subjectivity_detection_udf("word"))
    return words
lines_sentiment = lines_new_json.select(F.col('json')['text'].alias('value'))
words = preprocessing(lines_sentiment)
# text classification to define polarity and subjectivity
words = text_classification(words)
words = words.repartition(1)
words = (
    words.withColumn('sentiment_analysis',
                     F.when(
                         F.col('polarity').cast('double') < 0, F.lit('Negative')
                     )
                     .when(F.col('polarity').cast('double') == 0, F.lit('Neutral'))
                     .otherwise(F.lit('Positive'))
                    )
        )

(words.writeStream
  .outputMode("append")
  .format("org.elasticsearch.spark.sql")
  .option("checkpointLocation", "logs_elastic_clean")
  .start("sentiment_labels").awaitTermination())