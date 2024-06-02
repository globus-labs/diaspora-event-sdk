import os
from typing import Union


# TOKEN_EXCHANGE = "http://3.220.110.101/"
DIASPORA_RESOURCE_SERVER = "2b9d2f5c-fa32-45b5-875b-b24cd343b917"


def _get_envname():
    return os.getenv("DIASPORA_SDK_ENVIRONMENT", "production")


def get_web_service_url(envname: Union[str, None] = None) -> str:
    env = envname or _get_envname()
    urls = {
        "production": "https://diaspora-web-service.ml22sevubfnks.us-east-1.cs.amazonlightsail.com",
        "dev": "https://diaspora-web-service-dev.ml22sevubfnks.us-east-1.cs.amazonlightsail.com",
        "local": "http://localhost:8000",
        "legacy": "http://3.220.110.101/",
    }

    return urls.get(env, urls["production"])
