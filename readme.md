# Diaspora Logger

Diaspora Logger is a library for logging events to the Diaspora Streams (Kafka) cluster. The producer and consumer connections to Diaspora Streams are authenticated with Globus Auth. Follow the steps below to set up a `DiasporaLogger` instance for producing events.

## Install
```bash
pip install diaspora_logger
```

## Setup

1. **Generate Globus Auth Tokens:**
    Run `credentials.py` to generate a Globus Auth access token and a refresh token. 

    ```python
    from diaspora_logger import request_token_workflow

    request_token_workflow()
    ```
    Here's an example run:
    ```
    Please visit the following URL to authorize the application: <Globus Auth /authorize endpoint>
    Paste the authorization code here: <authorization-code>
    ================================
    Subject claim:     <subject-claim>
    Principal name:    <subject-username>
    Access token:      <access-token>
    Refresh token:     <refresh-token>
    Py clients:        export DIASPORA_REFRESH=<refresh-token>
    Java clients:      Connection properties are saved to <subject-username>.properties.
    ================================
    ```

    Note that the `<access-token>` is good for 48 hours once generated. The `<refresh-token>` expires after six months of inactivity but is good forever if used. The token owner can revoke the refresh token; see Globus Auth documentation for details.

    To generate `<subject-username>.properties` for establishing a connection from a Java client, call `request_token_workflow` with the optional argument `save_for_java=True`


2. **Register Topics:** Use the [public ACL endpoint](http://52.200.217.146:9090/acl) to claim topics. 

    > A topic only needs to be claimed once, skip this step if you have a topic claimed previously.

    The request form takes three inputs:
    - Subject Claim: paste in the `<subject-claim>` retrieved above.
    - Access Token: paste in the `<access-token>` retrieved above.
    - Topic Name: a string consists of letters, numbers, and underscores. A topic name cannot start with an underscore. 

    Once the form is submitted, this endpoint also generates an equivalent GET request with the form filled for conveniently claiming another topic through the web interface and an equivalent CURL POST request for using CLI tools to interact with the public ACL endpoint.

    If the access token expires, the access token and the subject claim do not match, or the topic has ACL rules associated already (i.e., claimed by other users), the request will fail. 

    If a topic is claimed by an user, different refresh token (if ever requested) would also work for this topic.


3. **Export Credential:**
    Instead of hard-coding the refresh token to your code repository, export it to your environment for using it. You could also put the token in a read-only file in the production environment.
    ```bash
    export DIASPORA_REFRESH=<Globus-Auth-refresh-token>
    ```

4. **Run a Producer:**
    Set the `topic` variable to your producer topic, then call `run_producer_example()` to start the producer.
    ```python
    from diaspora_logger.examples import run_producer_example

    topic = "<claimed-topic>"
    run_producer_example(topic)
    ```

    [Inside this example](/diaspora_logger/examples/example_producer.py), a `DiasporaLogger` instance is created, and all method calls to this instance will be directed to its `_producer` object, a [`KafkaProducer`](https://kafka-python.readthedocs.io/en/master/apidoc/KafkaProducer.html) instance of the kafka-python library. In other words, you can use `DiasporaLogger` exactly the same as a `KafkaProducer`.




4. **Run a Consumer:**
    Set the `topic` and `group_id` variables to your consumer topic and group ID respectively, then call `run_consumer_example(topic, group_id)` to start the consumer.
    ```python
    from diaspora_logger.examples import run_consumer_example

    topic = '<consumer-topic>'
    groupid = "<some-group-id-of-your-choice>"
    run_consumer_example(topic, groupid)
    ```

## Communication Flows

![A](https://drive.google.com/uc?export=view&id=1wnMFkcafBF5xqCz_tJtf2isAvkT25Hkf)

