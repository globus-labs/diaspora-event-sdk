import requests
import requests_cache
from retry_requests import retry
from pprint import pprint

from diaspora_event_sdk.sdk._environments import MSK_SCRAM_ENDPOINT
from kafka import KafkaProducer
import json
import time


def fetch_weather_data(lat=41.85, lng=-87.65):
    # Setup a session with caching
    cache_session = requests_cache.CachedSession(".cache", expire_after=3)

    # Wrap the session with retry functionality
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)

    # Define the URL and parameters for the Open-Meteo API request
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lng,
        "current": ["temperature_2m", "relative_humidity_2m"],
        "minutely_15": ["temperature_2m", "relative_humidity_2m"],
        "timezone": "GMT",
        "forecast_days": 1,
    }

    # Make the API request using the retry-enabled and cached session
    response = retry_session.get(url, params=params)

    # Process the response as needed (e.g., print, convert to DataFrame, etc.)
    return response.json()


def produce_to_kafka(data_lst, key_lst):
    # TODO: refactor this after "advanced key management ticket"
    conf = {
        "bootstrap_servers": MSK_SCRAM_ENDPOINT,
        "security_protocol": "SASL_SSL",
        "sasl_mechanism": "SCRAM-SHA-512",
        "api_version": (3, 5, 1),
        "sasl_plain_username": "<retrieved-username>",
        "sasl_plain_password": "<retrieved-password>",
        "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
    }
    producer = KafkaProducer(**conf)
    for i, data in enumerate(data_lst):
        producer.send("weather_forecast", data, key=key_lst[i])
    producer.flush()


try:
    data_chicago = fetch_weather_data()
except Exception:
    data_chicago = {}
data_chicago["fetch_GMT"] = time.gmtime()
data_chicago["location"] = "Chicago"


try:
    data_boston = fetch_weather_data(42.35, -71.05)
except Exception:
    data_boston = {}
data_boston["fetch_GMT"] = time.gmtime()
data_boston["location"] = "Boston"


print("weather forecast fetched")

try:
    data_list = [data_chicago, data_boston]
    key_list = [b"Chicago", b"Boston"]
    produce_to_kafka(data_list, key_list)
except Exception:
    pass
print("weather forecast sent")
