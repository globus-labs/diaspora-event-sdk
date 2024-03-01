# Diaspora: Resilience-enabling services for science from HPC to edge

## Event Fabric SDK Installation Guide
### Recommended Method: Use with `kafka-python`
For easy integration with Diaspora Event Fabric, use the `KafkaProducer` and `KafkaConsumer` classes from our SDK. This requires the `kafka-python` library.

To install the Event Fabric SDK and `kafka-python,` with the following command:
```bash
pip install "diaspora-event-sdk[kafka-python]"
```

### Alternative Installation: Without Kafka Client Library
To use alternative Kafka client libraries (e.g., `confluent-kafka-python`, `aiokafka`, and libraries for other programming laguages), you can install the SDK without the `kafka-python` dependency. This option still provides topic-level access control (authorization) and login credential management features.

To install the SDK without `kafka-python`, use:
```bash
pip install diaspora-event-sdk
```
Note: This method does not include dependencies for `KafkaProducer` and `KafkaConsumer` classes mentioned in the QuickStart

## Use Diaspora Event Fabric SDK

**Getting Started**: Visit our [QuickStart Guide](docs/quickstart.md) for details on using the SDK with the kafka-python library and instructions for other Kafka clients.

**Troubleshooting and Credential Management**: Consult our [TrobleShooting Guide](docs/troubleshooting.md) for solving common issues and tips on managing keys effectively.

**Advanced Consumers with Faust**: Explore the [Faust Streaming Guide](docs/faust_weather_app.md) for advanced event streaming with Faust.

**Advanced Consumer Functions**: See our [Colab example](https://colab.research.google.com/drive/1tPKfxU2qPsLvNTreF6nKINU62k7pQWxa?usp=sharing) for demonstration.