import faust
import ssl
import logging
from faust.auth import SASLCredentials
from faust.types.auth import SASLMechanism

logging.basicConfig(level=logging.DEBUG)


class Minutely15(faust.Record, serializer="json"):
    time: list[str]
    temperature_2m: list[float]
    relative_humidity_2m: list[int]


class Record(faust.Record, serializer="json"):
    minutely_15: Minutely15
    location: str
    fetch_GMT: list[int]


# TODO: get username and password
# from diaspora_event_sdk import Client as GlobusClient
# c = GlobusClient()
# print(c.retrieve_key())

app = faust.App(
    "weather_forecast",  # topic name
    broker="kafka://b-1-public.diaspora.k6i387.c21.kafka.us-east-1.amazonaws.com:9196",  # leader broker address, prefixed with kafka://
    ssl_context=ssl.create_default_context(),
    broker_credentials=SASLCredentials(
        username="<retrieved-username>",
        password="<retrieved-password>",
        ssl_context=ssl.create_default_context(),
        mechanism=SASLMechanism.SCRAM_SHA_512,
    ),
)

# TODO: topics to create:
# weather_forecast
# weather_forecast-__assignor-__leader
# weather_forecast-temperature_2m-changelog         (table)
# weather_forecast-relative_humidity_2m-changelog   (table)

weather_forecast_topic = app.topic("weather_forecast", value_type=Record)
temperature_2m_table = app.Table("temperature_2m", default=float)
relative_humidity_2m_table = app.Table("relative_humidity_2m", default=int)
# TODO: topic policies to override


@app.agent(weather_forecast_topic)
async def process(updates: faust.Stream[Record]) -> None:
    async for record in updates:
        # print(f"Received record: {record}")
        if record.location != "Chicago":
            continue

        tmp = record.minutely_15.temperature_2m
        hum = record.minutely_15.relative_humidity_2m
        for i, time in enumerate(record.minutely_15.time):
            print(record.fetch_GMT, time)
            temperature_2m_table[time] = tmp[i]
            relative_humidity_2m_table[time] = hum[i]


# TODO: at terminal, run:
# faust -A test_recv worker -l info
