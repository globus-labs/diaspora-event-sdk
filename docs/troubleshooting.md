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
New keys may take a while to become active due to AWS processing time. To prevent errors during this period, use `block_until_ready()` as detailed in the quickstart guide.

## Key Migration
To avoid invalidating existing keys (if they're in use elsewhere), follow these steps below.

### Exporting Key from Original Machine

```python
from diaspora_event_sdk import Client as GlobusClient
c = GlobusClient()
print(c.get_secret_key()) # Note down this key
```

### Importing Key on New Machine:

```python
from diaspora_event_sdk import Client as GlobusClient
from diaspora_event_sdk import block_until_ready

c = GlobusClient()
c.put_secret_key("<secret-key-from-first-machine>")
print(c.retrieve_key()) 

assert block_until_ready()  # Should unblock in 1-10 seconds
```

## Key Management After Re-login and Across Multiple Machines

### Key Management After Logout and Login

If you log out and then log in again, any subsequent call to `block_until_ready()` or an attempt to create a producer or consumer will internally trigger the `create_key()` function because no secret key is found in `storage.db`. This API call will invalidate all previously issued keys and retrieve a new one. 

To avoid accidentally invalidating the secret key, it's recommended to use `put_secret_key()` (see above section) before calling `block_until_ready()` or creating a producer or consumer after re-login. This method allows you to manually set the secret key, ensuring that the existing key is not unintentionally invalidated.

### Managing Keys Across Multiple Machines

If machine A is logged in with Globus Auth credentials and has the AWS secret key stored in `storage.db`, logging into machine B with the same Globus Auth credential and calling `block_until_ready()` will invalidate the key on machine A. To ensure both machines have valid secret keys, follow the section above. 

If both machines have a valid secret key in storage.db, calling create_key() on one machine will not update the key on the other. This desynchronization can cause block_until_ready() to timeout on the machine with the outdated key.

We would like to change this behavior in a future update.
