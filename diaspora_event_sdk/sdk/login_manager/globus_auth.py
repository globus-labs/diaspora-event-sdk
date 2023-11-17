import os

import globus_sdk


def internal_auth_client():
    """
    This is the client that represents the Diaspora Event Fabric application itself
    """

    client_id = os.environ.get(
        "DIASPORA_SDK_CLIENT_ID", "c5d4fab4-7f0d-422e-b0c8-5c74329b52fe"
    )
    return globus_sdk.NativeAppAuthClient(
        client_id, app_name="Diaspora Event Fabric (internal client)"
    )