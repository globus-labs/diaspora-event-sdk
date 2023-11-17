# Diaspora Event Fabric: Resilience-enabling services for science from HPC to edge

### Install
```bash
pip install diaspora-event-sdk
```

## Use kafka-python

### Register ACLs

Before you can create, describe, and delete topics we need to set the appropriate ACLs in ZooKeeper. Here we use the Client to register ACLs for the desired topic name.

```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
topic = f"topic-of-{c.subject_openid}"
print(c.acl_add(topic))
print(c.acl_list())
```

### Create Topic

Now use the KafkaAdmin to create the topic.

```python
from diaspora_event_sdk import KafkaAdmin, NewTopic 
admin = KafkaAdmin()
res = admin.create_topics(new_topics=[NewTopic(name=topic, num_partitions=1, replication_factor=1)])
print(res)
```

### Start Producer

Once the topic is created we can publish to it. The Consumer wraps the [Python KafkaProducer](https://kafka-python.readthedocs.io/en/master/apidoc/KafkaProducer.html) Event publication can be either synchronous or asynchronous. Below demonstrates the synchronous approach. 

```python
from diaspora_event_sdk import Producer
producer = Producer()
future = producer.send(
    topic, {'message': 'Synchronous message from Diaspora SDK'})
result = future.get(timeout=10)
print(result)
```

### Start Consumer

A consumer can be configured to monitor the topic and act on events as they are published. The Consumer wraps the [Python KafkaConsumer](https://kafka-python.readthedocs.io/en/master/apidoc/KafkaConsumer.html). Here we use the `auto_offset_reset` to consume from the first event published to the topic. Removing this field will have the consumer act only on new events.

```python
from diaspora_event_sdk import Consumer  # Kafka producer
consumer = Consumer(topic, auto_offset_reset='earliest')
for msg in consumer:
    print(msg)
```

### Delete Topic
```python
from diaspora_event_sdk import KafkaAdmin
admin = KafkaAdmin()
res = admin.delete_topics(topics=[topic])
print(res)

```

### Remove Topic ACLs
```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
topic = f"topic-of-{c.subject_openid}" # or any topic you claimed
print(c.acl_remove(topic))
print(c.acl_list())
```

## Use other Kafka libraries
```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
c.retrieve_or_create_key()
```
For SASL/SCRAM authentication, use `username` and `secret_key` as authentication credential;
For AWS_MSK_IAM authentication, use `access_key` and `secret_key` as authentication credential.