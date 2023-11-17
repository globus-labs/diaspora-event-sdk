
import typing as t

import globus_sdk
from globus_compute_sdk.sdk.utils.uuid_like import UUID_LIKE_T
from globus_sdk.exc.api import GlobusAPIError

from ._environments import TOKEN_EXCHANGE


class WebClient(globus_sdk.BaseClient):

    def __init__(
        self,
        *,
        environment: t.Optional[str] = None,
        base_url: t.Optional[str] = None,
        app_name: t.Optional[str] = None,
        **kwargs,
    ):
        if base_url is None:
            base_url = TOKEN_EXCHANGE

        super().__init__(environment=environment, base_url=base_url, **kwargs)

        self._user_app_name = None
        self.user_app_name = app_name

    def create_key(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        return self.post("/create_key", headers={"Subject": subject})

    def acl_list(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        return self.get("/acl_list", headers={"Subject": subject})

    def acl_add(self, subject: UUID_LIKE_T, topic: str) -> globus_sdk.GlobusHTTPResponse:
        return self.post("/acl_add", headers={"Subject": subject, "Topic": topic})

    def acl_remove(self, subject: UUID_LIKE_T, topic: str) -> globus_sdk.GlobusHTTPResponse:
        return self.post("/acl_remove", headers={"Subject": subject, "Topic": topic})
