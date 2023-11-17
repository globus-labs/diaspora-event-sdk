from diaspora_event_sdk import Client as GlobusClient  # Globus client
from diaspora_event_sdk import Producer  # Kafka client


c = GlobusClient()
topic = f"topic-of-{c.subject_openid}"
producer = Producer()


future = producer.send(
    topic, {'message': 'Synchronous message 1 from Diaspora SDK'})
result = future.get(timeout=10)
print(result)

future = producer.send(
    topic, {'message': 'Synchronous message 2 from Diaspora SDK'})
result = future.get(timeout=10)
print(result)
