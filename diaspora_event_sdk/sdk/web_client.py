import json
from typing import Optional

import globus_sdk

from diaspora_event_sdk.sdk.utils.uuid_like import UUID_LIKE_T

from ._environments import get_web_service_url


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
            base_url = get_web_service_url(environment)

        super().__init__(environment=environment, base_url=base_url, **kwargs)

        self._user_app_name = None
        self.user_app_name = app_name

    def create_key(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        return self.get("/api/v2/create_key", headers={"Subject": str(subject)})

    def list_topics(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        return self.get("/api/v2/topics", headers={"Subject": str(subject)})

    def register_topic(
        self, subject: UUID_LIKE_T, topic: str, action: str
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.put(
            f"/api/v2/topic/{topic}",
            headers={"Subject": str(subject), "Action": action},
        )

    def get_topic_configs(
        self, subject: UUID_LIKE_T, topic: str
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.get(
            f"/api/v2/topic/{topic}", headers={"Subject": str(subject), "Topic": topic}
        )

    def update_topic_configs(
        self, subject: UUID_LIKE_T, topic: str, configs: dict
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.post(
            f"/api/v2/topic/{topic}",
            headers={
                "Subject": str(subject),
                "Topic": topic,
                "Content-Type": "text/plain",
            },
            data=json.dumps(configs).encode("utf-8"),
        )

    def update_topic_partitions(
        self, subject: UUID_LIKE_T, topic: str, new_partitions: int
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.post(
            f"/api/v2/topic/{topic}/partitions",
            headers={
                "Subject": str(subject),
                "Topic": topic,
                "NewPartitions": str(new_partitions),
            },
        )

    def reset_topic(
        self, subject: UUID_LIKE_T, topic: str
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.post(
            f"/api/v2/topic/{topic}/reset",
            headers={"Subject": str(subject), "Topic": topic},
        )

    def grant_user_access(
        self, subject: UUID_LIKE_T, topic: str, user: UUID_LIKE_T, action: str
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.post(
            f"/api/v2/topic/{topic}/user",
            headers={
                "Subject": str(subject),
                "Action": action,
                "Topic": topic,
                "User": str(user),
            },
        )

    def list_topic_users(
        self, subject: UUID_LIKE_T, topic: str
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.get(
            f"/api/v2/topic/{topic}/users",
            headers={"Subject": str(subject), "Topic": topic},
        )

    def list_triggers(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        return self.get("/api/v2/triggers", headers={"Subject": str(subject)})

    def create_trigger(
        self,
        subject: UUID_LIKE_T,
        topic: str,
        function: str,
        action: str,
        function_configs: dict,
        trigger_configs: dict,
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.put(
            "/api/v2/trigger",
            headers={
                "Subject": str(subject),
                "Topic": topic,
                "Trigger": function,
                "Action": action,
                "Content-Type": "text/plain",
            },
            data=json.dumps(
                {"function": function_configs, "trigger": trigger_configs}
            ).encode("utf-8"),
        )

    def update_trigger(
        self, subject: UUID_LIKE_T, trigger_uuid: UUID_LIKE_T, trigger_configs: dict
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.post(
            f"/api/v2/triggers/{trigger_uuid}",
            headers={
                "Subject": str(subject),
                "Trigger_id": str(trigger_uuid),
                "Content-Type": "text/plain",
            },
            data=json.dumps(trigger_configs).encode("utf-8"),
        )

    def list_log_streams(
        self, subject: UUID_LIKE_T, trigger: str
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.get(
            "/api/v2/logs", headers={"Subject": str(subject), "Trigger": trigger}
        )

    def get_log_events(
        self, subject: UUID_LIKE_T, trigger: str, stream: str
    ) -> globus_sdk.GlobusHTTPResponse:
        return self.get(
            "/api/v2/log",
            headers={"Subject": str(subject), "Trigger": trigger, "Stream": stream},
        )
