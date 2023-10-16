# Diaspora Logger

Diaspora Logger is a library for logging and processing events to Diaspora Stream using Globus Auth for authentication. Follow the steps below to set up and run the example producer and consumer scripts.

## Setup

1. **Generate Globus Auth Refresh Token:**
    Run `credentials.py` to generate a Globus Auth refresh token.
    ```bash
    from diaspora_logger import request_token_workflow

    request_token_workflow()
    ```
    Here's an example run:
    ```
    Please visit the following URL to authorize the application: <Globus Auth /authorize endpoint>
    Paste the authorization code here: <authorization-code>
    ***
    For Python clients (e.g., example_producer.py and example_consumer.py):
    export DIASPORA_REFRESH=<Globus-Auth-refresh-token>
    ***
    Credential subject claim: <subject-claim>
    Credential subject username: <subject-username>
    credential access token: <access-token> (expires in two days)
    credential refresh token: <refresh-token> (expires in six months of inactivity)
    ```

    If it's your first time producing to a topic, use [our ACL endppoint](http://52.200.217.146:9090/acl) to claim one or more topics.


2. **Export Credential:**
    Export the generated refresh token to your environment.
    ```bash
    export DIASPORA_REFRESH=<Globus-Auth-refresh-token>
    ```

3. **Running Producer:**
    Set the `topic` variable to your producer topic, then call `run_producer_example()` to start the producer.
    ```python
    topic = "<producer-topic>"
    run_producer_example(topic)
    ```

4. **Running Consumer:**
    Set the `topic` and `group_id` variables to your consumer topic and group ID respectively, then call `run_consumer_example(topic, group_id)` to start the consumer.
    ```python
    topic = '<consumer-topic>'
    group_id = '<consumer-group-id>'
    run_consumer_example(topic, group_id)
    ```

## Public ACL endpoint
TODO

## Communication Flows

![A](https://drive.google.com/uc?export=view&id=1wnMFkcafBF5xqCz_tJtf2isAvkT25Hkf)

