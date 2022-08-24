from time import sleep
from json import dumps
from kafka import KafkaProducer
import requests
from requests.structures import CaseInsensitiveDict
import json
from time import sleep
import os
# print('esperando para rodar')
# sleep(180)
# print('RODANDO')

bearer = os.getenv('BEARER_TOKEN')
base_url = "https://api.twitter.com/2/tweets/sample/stream"

headers = CaseInsensitiveDict()
headers["Accept"] = "application/json"
headers["Authorization"] = f"Bearer {bearer}"


get_url = f"{base_url}?tweet.fields=text,lang&user.fields=name,username,location&place.fields=country"

producer = KafkaProducer(bootstrap_servers=['kafka:29092'],
                         value_serializer=lambda x:
                         dumps(x,ensure_ascii=False).encode('utf-8'),request_timeout_ms=1000000, api_version_auto_timeout_ms=1000000,api_version=(2,8,0))

response = requests.get(get_url,stream=True,headers=headers)
for line in response.iter_lines():
    try:
        if json.loads(line)['data']['lang'] in ["en"]:
            producer.send('twitter_topic_full_en', value=json.loads(line.decode('utf-8'))['data'])
    except:
        continue
