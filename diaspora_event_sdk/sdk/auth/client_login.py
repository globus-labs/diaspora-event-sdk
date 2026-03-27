from __future__ import annotations

import os


def get_client_creds() -> tuple[str | None, str | None]:
    return os.getenv("DIASPORA_SDK_CLIENT_ID"), os.getenv(
        "DIASPORA_SDK_CLIENT_SECRET"
    )
