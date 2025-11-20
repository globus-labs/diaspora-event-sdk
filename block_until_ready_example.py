import json
import time
import uuid
from datetime import datetime

from diaspora_event_sdk import Client as GlobusClient
from diaspora_event_sdk import create_producer, create_consumer
from diaspora_event_sdk.version import __version__

c = GlobusClient()
print("SDK version:", __version__)
print("User's OpenID:", c.subject_openid)

my_topics = c.list_topics()
print(my_topics)
new_topic = f"haochen-demo-topic-{str(uuid.uuid4())[:8]}"
print(f"Using this topic: {new_topic}")
# new_topic = "haochen-demo-topic-690dff06"

if new_topic not in my_topics["topics"]:
    print("Topic not found, registering it…")
    print(c.register_topic(new_topic))

    # Wait until topic appears
    while True:
        time.sleep(3)
        print(time.time())
        my_topics = c.list_topics()
        print(my_topics)

        if new_topic in my_topics["topics"]:
            print("Topic ready")
            break

        print("Waiting for topic creation…")

print("Create producer")
p = create_producer(new_topic)
print("Producing events")
future = p.send(
    new_topic, {"current-time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
)
print(future.get(timeout=10))

print("Create consumer")
c = create_consumer(new_topic, auto_offset_reset="earliest")
print("Consuming events")
messages = c.poll(timeout_ms=5000)
for tp, msgs in messages.items():
    for message in msgs:
        print(json.loads(message.value.decode("utf-8")))
