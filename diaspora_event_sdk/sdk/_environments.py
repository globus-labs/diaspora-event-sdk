import os
from typing import Union


DIASPORA_RESOURCE_SERVER = "2b9d2f5c-fa32-45b5-875b-b24cd343b917"


def _get_envname():
    return os.getenv("DIASPORA_SDK_ENVIRONMENT", "production")


def get_web_service_url(envname: Union[str, None] = None) -> str:
    env = envname or _get_envname()
    urls = {
        "production": "https://diaspora-web-service.qpp943wkvr7b2.us-east-1.cs.amazonlightsail.com/",
        "local": "http://localhost:8000",
    }

    return urls.get(env, urls["production"])
