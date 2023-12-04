<h1>Diaspora Event Fabric: Resilience-enabling services for science from HPC to edge</h1>

- [Installation](#installation)
   * [Recommended Installation with Kafka Client Library](#recommended-installation-with-kafka-client-library)
   * [Installation Without Kafka Client Library](#installation-without-kafka-client-library)
- [Use Diaspora Event SDK](#use-diaspora-event-sdk)
   * [Use the SDK to communicate with Kafka (kafka-python Required)](#use-the-sdk-to-communicate-with-kafka-kafka-python-required)
      + [Register Topic (create topic ACLs)](#register-topic-create-topic-acls)
      + [Start Producer](#start-producer)
      + [Start Consumer](#start-consumer)
      + [Unregister Topic (remove topic ACLs)](#unregister-topic-remove-topic-acls)
   * [Use Your Preferred Kafka Client Library](#use-your-preferred-kafka-client-library)
      + [Register and Unregister Topic](#register-and-unregister-topic)
      + [Cluster Connection Details](#cluster-connection-details)
   * [Advanced Usage](#advanced-usage)
      + [Password Refresh](#password-refresh)
- [Common Issues](#common-issues)
   * [ImportError: cannot import name 'KafkaProducer' from 'diaspora_event_sdk'](#importerror-cannot-import-name-kafkaproducer-from-diaspora_event_sdk)
   * [kafka.errors.NoBrokersAvailable and kafka.errors.NodeNotReadyError](#kafkaerrorsnobrokersavailable-and-kafkaerrorsnodenotreadyerror)


## Installation
### Recommended Installation with Kafka Client Library
If you plan to utilize the `KafkaProducer` and `KafkaConsumer` classes in the SDK, which are extensions of the respective classes from the `kafka-python` library, we recommend installing the SDK with `kafka-python` support. This is especially convenient for tutorial purposes and integrating Kafka functionalities in your projects with out-of-box configurations.

To install Diaspora Event SDK with `kafka-python`, run:
```bash
pip install "diaspora-event-sdk[kafka-python]"
```

### Installation Without Kafka Client Library
For scenarios where `kafka-python` is not required or if you are using other client libraries to communicate with Kafka, you can install the SDK without this dependency.

To install the SDK without Kafka support, simply run:
```bash
pip install diaspora-event-sdk
```
Note that this option does not install the necessary dependency for `KafkaProducer` and `KafkaConsumer` below to work.

## Use Diaspora Event SDK
### Use the SDK to communicate with Kafka (kafka-python Required)

#### Register Topic (create topic ACLs)

Before you can create, describe, and delete topics we need to set the appropriate ACLs in ZooKeeper. Here we use the Client to register ACLs for the desired topic name.

```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
topic = "topic-" + c.subject_openid[-12:]
print(c.register_topic(topic))
print(c.list_topics())
```
Register a topic also creates it, if the topic previously does not exist.

#### Start Producer

Once the topic is created we can publish to it. The KafkaProducer wraps the [Python KafkaProducer](https://kafka-python.readthedocs.io/en/master/apidoc/KafkaProducer.html) Event publication can be either synchronous or asynchronous. Below demonstrates the synchronous approach. 

```python
from diaspora_event_sdk import KafkaProducer
producer = KafkaProducer()
future = producer.send(
    topic, {'message': 'Synchronous message from Diaspora SDK'})
print(future.get(timeout=10))
```

#### Start Consumer

A consumer can be configured to monitor the topic and act on events as they are published. The KafkaConsumer wraps the [Python KafkaConsumer](https://kafka-python.readthedocs.io/en/master/apidoc/KafkaConsumer.html). Here we use the `auto_offset_reset` to consume from the first event published to the topic. Removing this field will have the consumer act only on new events.

```python
from diaspora_event_sdk import KafkaConsumer
consumer = KafkaConsumer(topic, auto_offset_reset='earliest')
for msg in consumer:
    print(msg)
```

#### Unregister Topic (remove topic ACLs)
```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
topic = "topic-" + c.subject_openid[-12:]
print(c.unregister_topic(topic))
print(c.list_topics())
```

### Use Your Preferred Kafka Client Library

#### Register and Unregister Topic
The steps are the same as above by using the `register_topic`, `unregister_topic`, and `list_topics` methods from the `Client` class.

#### Cluster Connection Details
| Configuration     | Value                                                               |
| ----------------- | ------------------------------------------------------------------- |
| Bootstrap Servers | [`MSK_SCRAM_ENDPOINT`](/diaspora_event_sdk/sdk/_environments.py#L6) |
| Security Protocol | `SASL_SSL`                                                          |
| Sasl Mechanism    | `SCRAM-SHA-512`                                                     |
| Api Version       | `3.5.1`                                                             |
| Username          | (See instructions below)                                            |
| Password          | (See instructions below)                                            |

Execute the code snippet below to obtain your unique username and password for the Kafka cluster:
```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
print(c.retrieve_key())
```

### Advanced Usage

#### Password Refresh
In case that you need to invalidate all previously issued passwords and generate a new one, call the `create_key` method from the `Client` class
```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
print(c.create_key())
```
Subsequent calls to `retrieve_key` will return the new password from the cache. This cache is reset with a logout or a new `create_key` call.

## Common Issues

### ImportError: cannot import name 'KafkaProducer' from 'diaspora_event_sdk'

It seems that you ran `pip install diaspora-event-sdk` to install the Diaspora Event SDK without `kafka-python`. Run `pip install kafka-python` to install the necessary dependency for our `KafkaProducer` and `KafkaConsumer` classes.

### kafka.errors.NoBrokersAvailable and kafka.errors.NodeNotReadyError
These messages might pop up if `create_key` is called shortly before instanciating a Kafka client. This is because there's a delay for AWS Secret Manager to associate the newly generated credential with MSK. Note that `create_key` is called internally by `kafka_client.py` the first time you create one of these clients. Please wait a while (around 1 minute) and retry.

### kafka.errors.KafkaTimeoutError: KafkaTimeoutError: Failed to update metadata after 60.0 secs.
**Step 1: Verify Topic Creation and Access:**
Before interacting with the producer/consumer, ensure that the topic has been successfully created and access is granted to you. Execute the following command:

```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
# topic = <the topic you want to use>
print(c.register_topic(topic)) 
```
This should return a `status: no-op` message, indicating that the topic is already registered and accessible.

**Step 2: Wait Automatic Key Creation in KafkaProducer and KafkaConsumer**
`KafkaProducer` and `KafkaConsumer` would internally call `create_key` if the keys are not found locally (e.g., when you first authenticated with Globus). Behind the sence, the middle service contacts AWS to initialize the asynchronous process of creating and associating the secret. Please wait a while (around 1 minute) and retry.

### ssl.SSLCertVerificationError
This is commmon on MacOS system, see [this StackOverflow answer](https://stackoverflow.com/a/53310545).