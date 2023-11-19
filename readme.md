# Diaspora Event Fabric: Resilience-enabling services for science from HPC to edge

### Install
```bash
pip install diaspora-event-sdk
```

## Use kafka-python

### Register Topic (create topic ACLs)

Before you can create, describe, and delete topics we need to set the appropriate ACLs in ZooKeeper. Here we use the Client to register ACLs for the desired topic name.

```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
topic = "topic-" + c.subject_openid[-12:]
print(c.register_topic(topic))
print(c.list_topics())
```

### Create Topic

Now use the KafkaAdmin to create the topic.

```python
from diaspora_event_sdk import KafkaAdmin, NewTopic 
admin = KafkaAdmin()
print(admin.create_topics(new_topics=[
      NewTopic(name=topic, num_partitions=1, replication_factor=1)]))
```

### Start Producer

Once the topic is created we can publish to it. The KafkaProducer wraps the [Python KafkaProducer](https://kafka-python.readthedocs.io/en/master/apidoc/KafkaProducer.html) Event publication can be either synchronous or asynchronous. Below demonstrates the synchronous approach. 

```python
from diaspora_event_sdk import KafkaProducer
producer = KafkaProducer()
future = producer.send(
    topic, {'message': 'Synchronous message from Diaspora SDK'})
result = future.get(timeout=10)
print(result)
```

### Start Consumer

A consumer can be configured to monitor the topic and act on events as they are published. The KafkaConsumer wraps the [Python KafkaConsumer](https://kafka-python.readthedocs.io/en/master/apidoc/KafkaConsumer.html). Here we use the `auto_offset_reset` to consume from the first event published to the topic. Removing this field will have the consumer act only on new events.

```python
from diaspora_event_sdk import KafkaConsumer
consumer = KafkaConsumer(topic, auto_offset_reset='earliest')
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

### Unregister Topic (remove topic ACLs)
```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
topic = "topic-" + c.subject_openid[-12:]
print(c.unregister_topic(topic))
print(c.list_topics())
```

## Use other Kafka libraries
```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
print(c.retrieve_key())
```
For other Kafka clients, select SASL/SCRAM authentication, and use `username` and `password` as authentication credential. Other connection parameters see [here](). 
