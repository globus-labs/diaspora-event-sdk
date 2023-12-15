# Diaspora Event Fabric SDK: QuickStart
## Basics and Setup

Diaspora Event Fabric offers topic-level access control. Typically, only one user can access a topic. Use `register_topic` API to request access:

```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
topic = "topic-" + c.subject_openid[-12:]

print(c.register_topic(topic))
print(c.list_topics())
```
Expect `success` or `no-op` for the first print, and a list including your topic for the second. For group projects, contact Haochen or Ryan to access pre-registered topics.

Aside from topic authorization, authentication requires a username (user's OpenID) and password (AWS secret key in `$HOME/.diaspora/storage.db`). If the secret key is missing (e.g., new login), `KafkaProducer` or `KafkaConsumer` instance would internally call `create_key()` to generate and store one. However, the key takes 30 seconds to 2 minutes to activate due to AWS processing.

To avoid errors during this delay, use `block_until_ready()`:

```python 
from diaspora_event_sdk import block_until_ready
assert block_until_ready()
# now the secret key is ready to use 
```

This function waits until the key activates, usually within 30 seconds to 2 minutes. Subsequent `block_until_ready()` calls should return in 1-10 seconds. Still, include this primarily in test/setup scripts, but not on the critical (happy) path.



## Producing or Consuming

Once the topic is registered and the secret key is ready, we can publish messages to it. The `KafkaProducer` wraps the [Python KafkaProducer](https://kafka-python.readthedocs.io/en/master/apidoc/KafkaProducer.html), and event publication can be either synchronous or asynchronous. Below demonstrates the synchronous approach. 

```python
from diaspora_event_sdk import KafkaProducer
producer = KafkaProducer()
future = producer.send(
    topic, {'message': 'Synchronous message from Diaspora SDK'})
print(future.get(timeout=10))
```

A consumer can be configured to monitor the topic and act on events as they are published. The `KafkaConsumer` wraps the [Python KafkaConsumer](https://kafka-python.readthedocs.io/en/master/apidoc/KafkaConsumer.html). Here we use the `auto_offset_reset` to consume from the first event published to the topic. Removing this field will have the consumer act only on new events.

```python
from diaspora_event_sdk import KafkaConsumer
consumer = KafkaConsumer(topic, auto_offset_reset='earliest')
for msg in consumer:
    print(msg)
```


## Unregister Topic
To prevent reaching AWS's limit on topic partitions, unregister a topic from Diaspora Event Fabric when it's no longer in use. Use the following code to unregister:

```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
topic = "topic-" + c.subject_openid[-12:]

print(c.unregister_topic(topic))
print(c.list_topics())
```

Once a topic is successfully unregistered, you'll lose access to it. However, it becomes available for registration and access by other users.