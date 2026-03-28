# Adapted from globus-compute SDK (Apache 2.0)
# https://github.com/globus/globus-compute/blob/main/compute_sdk/globus_compute_sdk/sdk/auth/client_login.py
from __future__ import annotations

import os


def get_client_creds() -> tuple[str | None, str | None]:
    return os.getenv("DIASPORA_SDK_CLIENT_ID"), os.getenv(
        "DIASPORA_SDK_CLIENT_SECRET"
    )
