# Diaspora Event Fabric SDK: Troubleshooting

## Authorization and Authentication Issues
To confirm you have access to a topic and ensure proper authentication with Kafka, use the script below. Remember to replace `...` with your specific topic name:

```python
from diaspora_event_sdk import Client as GlobusClient
from diaspora_event_sdk import block_until_ready

topic = ...  # Replace with your topic

c = GlobusClient()
registration_status = c.register_topic(topic)
print(registration_status)
assert registration_status["status"] in ["no-op", "success"]

registered_topics = c.list_topics()
print(registered_topics)
assert topic in registered_topics["topics"]

assert block_until_ready()
```

If the first two assertions fail, it's likely the topic is already registered by others in your project. In this case, reach out to Haochen or Ryan for access.

If the last assertion fails, refresh your secret key with ` create_key()`, which will invalidate any prior keys associated with the user (if this is not desired, see Key Migration section):

```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
print(c.create_key())
```

To retrieve the new password stored in `$HOME/.diaspora/storage.db`, use `retrieve_key()`. Remember that `storage.db` resets after logout or a new create_key() call:

```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
print(c.retrieve_key()) # Retrieves the key in storage.db

c.logout()              # Clears storage.db
print(c.retrieve_key()) # No a key in cache, calls create_key() and stores the new key
```
New keys may take a while to become active due to AWS processing time. To prevent errors during this period, use block_until_ready() as detailed in the quickstart guide.

## Key Migration
To avoid invalidating existing keys (if they're in use elsewhere), follow these steps below.

#### Exporting Key from Original Machine

```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
print(c.get_secret_key()) # Note down this key
```

#### Importing Key on New Machine:

```python
from diaspora_event_sdk import Client as GlobusClient
from diaspora_event_sdk import block_until_ready

c = GlobusClient()
c.put_secret_key("<secret-key-from-first-machine>")
print(c.retrieve_key()) 

assert block_until_ready()  # Should unblock in 1-10 seconds
```

