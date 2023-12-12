from diaspora_event_sdk import Client as GlobusClient
from diaspora_event_sdk import block_until_ready
c = GlobusClient()
assert block_until_ready()


