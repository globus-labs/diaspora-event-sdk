# Diaspora Event Fabric SDK: QuickStart
## Basics and Setup

Diaspora Event Fabric offers topic-level access control. Typically, only one user can access a topic. Use `register_topic` API to request access (Replace `...` below with your topic name):

```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
topic = ... # e.g., "topic-" + c.subject_openid[-12:]

print(c.register_topic(topic))
print(c.list_topics())
```
Expect `success` or `no-op` for the first print, and a list including your topic for the second. For group projects, contact Haochen or Ryan to access topics that have been registered by other users before.

Aside from topic authorization, authentication requires a username (user's OpenID) and password (AWS secret key in `$HOME/.diaspora/storage.db`). If the secret key is missing (e.g., new login), `KafkaProducer` or `KafkaConsumer` instance would internally call `create_key()` to generate and store one. However, the key takes 30 seconds to 2 minutes to activate due to AWS processing.

To avoid errors during this delay, use `block_until_ready()`:

```python
from diaspora_event_sdk import block_until_ready
assert block_until_ready()
# now the secret key is ready to use
```

This function waits until the key activates, usually within a few seconds. Subsequent `block_until_ready()` calls should return even faster. Still, include this in test/setup scripts, but not on the critical (happy) path.


## Producing or Consuming

Once the topic is registered and the access key and secret key are ready (through `c = GlobusClient()`), we can publish messages to it. The `KafkaProducer` wraps the [Python KafkaProducer](https://kafka-python.readthedocs.io/en/master/apidoc/KafkaProducer.html), and event publication can be either synchronous or asynchronous. Below demonstrates the synchronous approach.

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

print(c.unregister_topic(topic))
print(c.list_topics())
```

Once a topic is successfully unregistered, you'll lose access to it. And it becomes available for registration and access by other users.


## Integrating Your Own Kafka Client with Diaspora Event Fabric
If you're opting to use a custom Kafka client library, here are the necessary cluster connection details:

| Configuration     | Value                                 |
| ----------------- | ------------------------------------- |
| Bootstrap Servers | `c.retrieve_key()['endpoint']`        |
| Security Protocol | `SASL_SSL`                            |
| Sasl Mechanism    | `OAUTHBEARER`                         |
| Username          | `c.retrieve_key()['access_key']`      |
| Password          | `c.retrieve_key()['secret_key']`      |

The bootstrap server address, OAuth access key, and OAuth secret key can be retrieved through `retrieve_key()` and invalidated through `create_key()`. To use Diaspora Event Fabric with `confluent-kafka-python`, please refer to [this guide](https://github.com/aws/aws-msk-iam-sasl-signer-python?tab=readme-ov-file). For other programming languages, please refer to [this post](https://aws.amazon.com/blogs/big-data/amazon-msk-iam-authentication-now-supports-all-programming-languages/).
```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
print(c.retrieve_key())
```
