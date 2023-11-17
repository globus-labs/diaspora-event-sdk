from diaspora_event_sdk import Client as GlobusClient  # Globus client
from diaspora_event_sdk import Consumer  # Kafka producer

c = GlobusClient()
topic = f"topic-of-{c.subject_openid}"

consumer = Consumer(topic)
for msg in consumer:
    print(msg)
