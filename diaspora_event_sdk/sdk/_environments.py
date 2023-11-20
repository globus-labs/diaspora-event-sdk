import os


TOKEN_EXCHANGE = "http://3.220.110.101"
DIASPORA_RESOURCE_SERVER = '2b9d2f5c-fa32-45b5-875b-b24cd343b917'
MSK_SCRAM_ENDPOINT = "b-1-public.diaspora.k6i387.c21.kafka.us-east-1.amazonaws.com:9196,b-2-public.diaspora.k6i387.c21.kafka.us-east-1.amazonaws.com:9196"


def _get_envname():
    return os.getenv("DIASPORA_SDK_ENVIRONMENT", "production")
