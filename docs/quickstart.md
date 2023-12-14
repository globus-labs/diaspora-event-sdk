### QuickStart: Use SDK for Diaspora Event Fabric
#### Basic Concepts and One-time Setup

Diaspora Event Fabric enforces topic-level access control; each topic is usually "owned" by one user and rarely more than one. To request access to a topic, use the `register_topic` API.

```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()

# or use a more meaningful name
topic = "topic-" + c.subject_openid[-12:]

print(c.register_topic(topic))
print(c.list_topics())
```
The first print should return a message with `status` as either `success` or `no-op`, and the second print should return your requested topic in the list of `topics`. If a topic for a group project has been registered by other users before, please contact Haochen or Ryan to add you to the list of owners.


Aside from topic authorization, authentication (username and password) is needed to establish the connection. `KafkaProducer` or `KafkaConsumer` instance will use the user's OpenID as the username, and the AWS secret key stored in `$HOME/.diaspora/storage.db` as the password. If no secret key is found (e.g., when you just log in), it will call the `create_key()` API to request a new one and store the key in `storage.db`. However, when `create_key()` returns, the secret key is not immediately ready to use: it usually takes 30 seconds to 2 minutes for AWS to propagate the secret into Kafka. You will encounter timeout errors when you try to use a newly issued key before the propagation completes.

One solution to avoid the confusion is to call `block_until_ready()`, which calls `create_key()` if no secret key is found in `storage.db` and tries to instantiate a producer and a consumer using the new key. The method blocks until the key is ready to use. Other solutions and advanced key management are outlined in the debug section.

```python 
from diaspora_event_sdk import block_until_ready
assert block_until_ready()
```

This function returns False after five minutes if the connection still cannot be made but usually returns True in 30 seconds to 2 minutes, indicating the newly requested key is ready. Subsequent `block_until_ready()` calls should return in 1-10 seconds. Still, we suggest you include the code only in a testing/setup script, but not on the critical (happy) path.







#### Producing or Consuming

Once the topic is registered we can publish to it. The `KafkaProducer` wraps the [Python KafkaProducer](https://kafka-python.readthedocs.io/en/master/apidoc/KafkaProducer.html) Event publication can be either synchronous or asynchronous. Below demonstrates the synchronous approach. 

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


#### Unregister Topic
When you no longer use a topic, unregister it so Diaspora Event Fabric doesn't hit the hard limit of the number of topic partitions that AWS imposes.

```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
topic = "topic-" + c.subject_openid[-12:]
print(c.unregister_topic(topic))
print(c.list_topics())
```