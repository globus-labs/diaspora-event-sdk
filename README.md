# Diaspora Event Fabric SDK

## Installation Guide
### Recommended Method: With `kafka-python`
To integrate with Diaspora Event Fabric using `KafkaProducer` and `KafkaConsumer`, install the SDK with `kafka-python`:
```bash
pip install "diaspora-event-sdk[kafka-python]"
```

### Alternative Installation: Without Kafka Client Library
For other Kafka client libraries (e.g., `confluent-kafka-python`, `aiokafka`), install the SDK without `kafka-python`:
```bash
pip install diaspora-event-sdk
```
Note: This does not include `KafkaProducer` and `KafkaConsumer` dependencies.

## Using Diaspora Event Fabric SDK
Check our [Notebook](DiasporaDemo.ipynb) for a quickstart and demonstration.

<!-- **Getting Started**: Visit our [QuickStart Guide](docs/quickstart.md) for details on using the SDK with the kafka-python library and instructions for other Kafka clients.

**Troubleshooting and Credential Management**: Consult our [TrobleShooting Guide](docs/troubleshooting.md) for solving common issues and tips on managing keys effectively. -->

<!-- **Advanced Consumers with Faust**: Explore the [Faust Streaming Guide](docs/faust_weather_app.md) for advanced event streaming with Faust. -->

<!-- **Advanced Consumer Functions**: See our [Colab example](https://colab.research.google.com/drive/1tPKfxU2qPsLvNTreF6nKINU62k7pQWxa?usp=sharing) for demonstration. -->
