import os


# TOKEN_EXCHANGE = "http://3.220.110.101/"
DIASPORA_RESOURCE_SERVER = "2b9d2f5c-fa32-45b5-875b-b24cd343b917"


def _get_envname():
    return os.getenv("DIASPORA_SDK_ENVIRONMENT", "production")

def get_web_service_url(envname: str | None = None) -> str:
    env = envname or _get_envname()
    urls = {
        "production": "http://3.220.110.101/",
        "dev": "https://diaspora-web-service.ml22sevubfnks.us-east-1.cs.amazonlightsail.com",
        "local": "http://localhost:5000",
    }

    return urls.get(env, urls["production"])
