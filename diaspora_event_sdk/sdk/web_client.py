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

    def register_topic(
        self, subject: UUID_LIKE_T, topic: str
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.post(
            "/v1/register_topic", headers={"Subject": str(subject), "Topic": topic}
        )

    def unregister_topic(
        self, subject: UUID_LIKE_T, topic: str
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.post(
            "/v1/unregister_topic", headers={"Subject": str(subject), "Topic": topic}
        )

    def register_topic_for_user(
        self, subject: UUID_LIKE_T, topic: str, user: UUID_LIKE_T
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.post(
            "/v1/register_topic_for_user",
            headers={"Subject": str(
                subject), "Topic": topic, "User": str(user)}
        )

    def unregister_topic_for_user(
        self, subject: UUID_LIKE_T, topic: str, user: UUID_LIKE_T
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.post(
            "/v1/unregister_topic_for_user",
            headers={"Subject": str(
                subject), "Topic": topic, "User": str(user)}
        )

    def list_functions(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        return self.get("/v1/list_functions", headers={"Subject": str(subject)})

    def register_function(
        self, subject: UUID_LIKE_T, topic: str, function: str,
        function_configs: dict
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.post(
            "/v1/register_function",
            headers={"Subject": str(subject), "Topic": topic,
                     "Function": function},
            data=function_configs
        )

    def unregister_function(
        self, subject: UUID_LIKE_T, topic: str, function: str
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.post(
            "/v1/unregister_function", headers={"Subject": str(subject), "Topic": topic, "Function": function}
        )

    def update_function_trigger(
        self, subject: UUID_LIKE_T, trigger_uuid: UUID_LIKE_T, trigger_configs: dict
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.post(
            "/v1/update_function_trigger",
            headers={"Subject": str(subject), "Trigger": str(trigger_uuid)},
            data=trigger_configs
        )
