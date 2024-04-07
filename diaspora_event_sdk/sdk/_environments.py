import os


TOKEN_EXCHANGE = "http://3.220.110.101/"
DIASPORA_RESOURCE_SERVER = "2b9d2f5c-fa32-45b5-875b-b24cd343b917"


def _get_envname():
    return os.getenv("DIASPORA_SDK_ENVIRONMENT", "production")
