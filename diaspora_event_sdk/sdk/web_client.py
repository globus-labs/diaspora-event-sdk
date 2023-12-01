from typing import Optional

import globus_sdk
from diaspora_event_sdk.sdk.utils.uuid_like import UUID_LIKE_T

from ._environments import TOKEN_EXCHANGE


class WebClient(globus_sdk.BaseClient):

    def __init__(
        self,
        *,
        environment: Optional[str] = None,
        base_url: Optional[str] = None,
        app_name: Optional[str] = None,
        **kwargs,
    ):
        if base_url is None:
            base_url = TOKEN_EXCHANGE

        super().__init__(environment=environment, base_url=base_url, **kwargs)

        self._user_app_name = None
        self.user_app_name = app_name

    def create_key(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        return self.post("/v1/create_key", headers={"Subject": str(subject)})

    def list_topics(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        return self.get("/v1/list_topics", headers={"Subject": str(subject)})

    def register_topic(self, subject: UUID_LIKE_T, topic: str) -> globus_sdk.GlobusHTTPResponse:
        return self.post("/v1/register_topic", headers={"Subject": str(subject), "Topic": topic})

    def unregister_topic(self, subject: UUID_LIKE_T, topic: str) -> globus_sdk.GlobusHTTPResponse:
        return self.post("/v1/unregister_topic", headers={"Subject": str(subject), "Topic": topic})
