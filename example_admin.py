from diaspora_event_sdk import Client as GlobusClient  # Globus client
from diaspora_event_sdk import KafkaAdminClient, NewTopic  # Kafka clients

c = GlobusClient()
print(c.retrieve_or_create_key())
topic = f"topic-of-{c.subject_openid}"
print("topic name is", topic)
# print(c.acl_add(topic))
# print(c.acl_list())

admin = KafkaAdminClient(c)
# res = admin.create_topics(new_topics=[NewTopic(
#     name=topic, num_partitions=2, replication_factor=2)])
# print(res)

# res = admin.delete_topics(topics=[topic])
# print(res)
