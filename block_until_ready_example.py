import json
from datetime import datetime

from diaspora_event_sdk import Client as GlobusClient
from diaspora_event_sdk import KafkaConsumer, KafkaProducer
from diaspora_event_sdk.version import __version__

c = GlobusClient()
print("SDK version:", __version__)
print("User's OpenID:", c.subject_openid)

print(c.list_topics())
my_topic = "demo-topic-2025"
p = KafkaProducer(my_topic)
future = p.send(
    my_topic, {"current-time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
)
print(future.get(timeout=10))

consumer = KafkaConsumer(my_topic, auto_offset_reset="earliest")
messages = consumer.poll(timeout_ms=5000)
for tp, msgs in messages.items():
    for message in msgs:
        print(json.loads(message.value.decode("utf-8")))
