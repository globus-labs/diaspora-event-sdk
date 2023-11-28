<h1>Diaspora Event Fabric: Resilience-enabling services for science from HPC to edge</h1>

- [Installation Instructions](#installation-instructions)
  - [Recommended Installation with Kafka Client Library: kafka-python](#recommended-installation-with-kafka-client-library-kafka-python)
  - [Installation Without Kafka Client Library](#installation-without-kafka-client-library)
- [Use Diaspora Event SDK](#use-diaspora-event-sdk)
  - [Use SDK to communicate with Kafka (kafka-python Required)](#use-sdk-to-communicate-with-kafka-kafka-python-required)
    - [Register Topic (create topic ACLs)](#register-topic-create-topic-acls)
    - [Start Producer](#start-producer)
    - [Start Consumer](#start-consumer)
    - [Unregister Topic (remove topic ACLs)](#unregister-topic-remove-topic-acls)
  - [Communicating with Kafka Using Your Preferred Client Library](#communicating-with-kafka-using-your-preferred-client-library)
    - [Register and Unregister Topic](#register-and-unregister-topic)
    - [Cluster Connection Details](#cluster-connection-details)
  - [Advanced Usage](#advanced-usage)
    - [Password Refresh](#password-refresh)
- [Common Issues](#common-issues)
  - [ImportError: cannot import name 'KafkaAdmin' from 'diaspora\_event\_sdk'](#importerror-cannot-import-name-kafkaadmin-from-diaspora_event_sdk)
  - [kafka.errors.NoBrokersAvailable and kafka.errors.NodeNotReadyError](#kafka.errors.NoBrokersAvailableandkafka.errors.NodeNotReadyError)

## <a name='InstallationInstructions'></a>Installation Instructions
### <a name='RecommendedInstallationwithKafkaClientLibrary:kafka-python'></a>Recommended Installation with Kafka Client Library: kafka-python
If you plan to utilize the `KafkaAdmin`, `KafkaProducer`, and `KafkaConsumer` classes in the SDK, which are extensions of the respective classes from the `kafka-python` library, we recommend installing the SDK with `kafka-python` support. This is especially convenient for tutorial purposes and integrating Kafka functionalities in your projects with out-of-box configurations.

To install Diaspora Event SDK with `kafka-python`, run:
```bash
pip install "diaspora-event-sdk[kafka-python]"
```

### <a name='InstallationWithoutKafkaClientLibrary'></a>Installation Without Kafka Client Library
For scenarios where `kafka-python` is not required or if you are using other client libraries to communicate with Kafka, you can install the SDK without this dependency.

To install the SDK without Kafka support, simply run:
```bash
pip install diaspora-event-sdk
```
Note that this option does not install the necessary dependency for `KafkaAdmin`, `KafkaProducer`, and `KafkaConsumer` below to work.

## <a name='UseDiasporaEventSDK'></a>Use Diaspora Event SDK
### <a name='UseSDKtocommunicatewithKafkakafka-pythonRequired'></a>Use SDK to communicate with Kafka (kafka-python Required)

#### <a name='RegisterTopiccreatetopicACLs'></a>Register Topic (create topic ACLs)

Before you can create, describe, and delete topics we need to set the appropriate ACLs in ZooKeeper. Here we use the Client to register ACLs for the desired topic name.

```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
topic = "topic-" + c.subject_openid[-12:]
print(c.register_topic(topic))
print(c.list_topics())
```

#### <a name='StartProducer'></a>Start Producer

Once the topic is created we can publish to it. The KafkaProducer wraps the [Python KafkaProducer](https://kafka-python.readthedocs.io/en/master/apidoc/KafkaProducer.html) Event publication can be either synchronous or asynchronous. Below demonstrates the synchronous approach. 

```python
from diaspora_event_sdk import KafkaProducer
producer = KafkaProducer()
future = producer.send(
    topic, {'message': 'Synchronous message from Diaspora SDK'})
print(future.get(timeout=10))
```

#### <a name='StartConsumer'></a>Start Consumer

A consumer can be configured to monitor the topic and act on events as they are published. The KafkaConsumer wraps the [Python KafkaConsumer](https://kafka-python.readthedocs.io/en/master/apidoc/KafkaConsumer.html). Here we use the `auto_offset_reset` to consume from the first event published to the topic. Removing this field will have the consumer act only on new events.

```python
from diaspora_event_sdk import KafkaConsumer
consumer = KafkaConsumer(topic, auto_offset_reset='earliest')
for msg in consumer:
    print(msg)
```

#### <a name='UnregisterTopicremovetopicACLs'></a>Unregister Topic (remove topic ACLs)
```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
topic = "topic-" + c.subject_openid[-12:]
print(c.unregister_topic(topic))
print(c.list_topics())
```

### <a name='CommunicatingwithKafkaUsingYourPreferredClientLibrary'></a>Communicating with Kafka Using Your Preferred Client Library

#### <a name='RegisterandUnregisterTopic'></a>Register and Unregister Topic
The steps are the same as above by using the `register_topic`, `unregister_topic`, and `list_topics` methods from the `Client` class.

#### <a name='ClusterConnectionDetails'></a>Cluster Connection Details
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

### <a name='AdvancedUsage'></a>Advanced Usage

#### <a name='PasswordRefresh'></a>Password Refresh
In case that you need to invalidate all previously issued passwords and generate a new one, call the `create_key` method from the `Client` class
```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
print(c.create_key())
```
Subsequent calls to `retrieve_key` will return the new password from the cache. This cache is reset with a logout or a new `create_key` call.

## <a name='CommonIssues'></a>Common Issues

### <a name='ImportError:cannotimportnameKafkaAdminfromdiaspora_event_sdk'></a>ImportError: cannot import name 'KafkaAdmin' from 'diaspora_event_sdk'

It seems that you ran `pip install diaspora-event-sdk` to install the Diaspora Event SDK without `kafka-python`. Run `pip install kafka-python` to install the necessary dependency for our `KafkaAdmin`, `KafkaProducer`, and `KafkaConsumer` classes.

### <a name='kafka.errors.NoBrokersAvailableandkafka.errors.NodeNotReadyError'></a>kafka.errors.NoBrokersAvailable and kafka.errors.NodeNotReadyError
These messages might pop up if `create_key` is called shortly before instanciating a Kafka client. This is because there's a delay for AWS Secret Manager to associate the newly generated credential with MSK. Note that `create_key` is called the first time you create one of these clients. Please wait a while (around 1 minute) and retry.