# Diaspora Event Fabric: Resilience-enabling services for science from HPC to edge

### Install
```bash
pip install diaspora_event_sdk
```

## Use kafka-python

### Claim Topic Ownership
```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
topic = f"topic-of-{c.subject_openid}" # or any unclaimed topic
print(c.acl_add(topic))
print(c.acl_list())
```

### Create Topic
```python
from diaspora_event_sdk import KafkaAdmin, NewTopic 
admin = KafkaAdmin()
res = admin.create_topics(new_topics=[NewTopic(name=topic, num_partitions=2, replication_factor=2)])
print(res)
```

### Start Producer
```python
from diaspora_event_sdk import Producer
future = producer.send(
    topic, {'message': 'Synchronous message from Diaspora SDK'})
result = future.get(timeout=10)
print(result)
```
### Start Consumer
```python
from diaspora_event_sdk import Consumer  # Kafka producer
consumer = Consumer(topic)
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

### Release Topic Ownership
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
For AWS_IAM authentication, use `access_key` and `secret_key` as authentication credential.