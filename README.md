<h1>Diaspora Event Fabric: Resilience-enabling services for science from HPC to edge</h1>

## Installation
### Recommended Installation with Kafka Client Library
The `KafkaProducer` and `KafkaConsumer` classes within the SDK are designed for seamless integration with Diaspora Event Fabric using pre-configured settings. For utilizing these classes, the `kafka-python` library is necessary.

To install the Diaspora Event SDK along with `kafka-python,` execute:
```bash
pip install "diaspora-event-sdk[kafka-python]"
```

### Installation Without Kafka Client Library
If you prefer using different client libraries for Kafka communication, you can install the SDK without the kafka-python dependency. The SDK still serves for topic-level access control (authorization) and login credential management (authentication).

To install the SDK without client libraries, simply run:
```bash
pip install diaspora-event-sdk
```
Note: This does not install the necessary dependency for `KafkaProducer` and `KafkaConsumer` classes.

## Use Diaspora Event Fabric SDK

Please refer to our [QuickStart Guide](docs/quickstart.md) for recommended use with `kafka-python` library as well as steps to use your own Kafka client.

Please refer to our [TrobleShooting Guide](docs/troubleshooting.md) for debugging common problems and effective key management strategies.

[Topic: Use faust to Process Records](docs/faust_weather_app.md)