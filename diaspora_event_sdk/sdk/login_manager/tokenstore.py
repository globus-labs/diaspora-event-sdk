from __future__ import annotations

import json
import os
import pathlib

from globus_sdk.tokenstorage import SQLiteAdapter

from .._environments import _get_envname
from .client_login import get_client_login, is_client_login
from .globus_auth import internal_auth_client


def _home() -> pathlib.Path:
    # this is a hook point for tests to patch over
    # it just returns `pathlib.Path.home()`
    # replace this with a mock to return some test directory
    return pathlib.Path.home()


def invalidate_old_config() -> None:
    token_file = _home() / ".funcx" / "credentials" / "funcx_sdk_tokens.json"

    if token_file.exists():
        try:
            auth_client = internal_auth_client()
            with open(token_file) as fp:
                data = json.load(fp)
            for token_data in data.values():
                if "access_token" in token_data:
                    auth_client.oauth2_revoke_token(token_data["access_token"])
                if "refresh_token" in token_data:
                    auth_client.oauth2_revoke_token(
                        token_data["refresh_token"])
        finally:
            os.remove(token_file)


def ensure_compute_dir() -> pathlib.Path:
    legacy_dirname = _home() / ".funcx"
    dirname = _home() / ".globus_compute"

    user_dir = os.getenv("GLOBUS_COMPUTE_USER_DIR")
    if user_dir:
        dirname = pathlib.Path(user_dir)

    if dirname.is_dir():
        pass
    elif dirname.is_file():
        raise FileExistsError(
            f"Error creating directory {dirname}, "
            "please remove or rename the conflicting file"
        )
    elif legacy_dirname.is_dir() and not user_dir:
        legacy_dirname.replace(dirname)
        legacy_dirname.symlink_to(dirname, target_is_directory=True)
    else:
        dirname.mkdir(mode=0o700, parents=True, exist_ok=True)

    return dirname


def _get_storage_filename():
    datadir = ensure_compute_dir()
    return os.path.join(datadir, "storage.db")


def _resolve_namespace(environment: str | None) -> str:
    """
    Return the namespace used to save tokens. This will check
    if a client login is being used and return either:
      user/<envname>
    or
      clientprofile/<envname>/<clientid>

    e.g.

      user/production
    """
    env = environment if environment is not None else _get_envname()

    if is_client_login():
        client_id = get_client_login().client_id
        return f"clientprofile/{env}/{client_id}"

    return f"user/{env}"


def get_token_storage_adapter(*, environment: str | None = None) -> SQLiteAdapter:
    # when initializing the token storage adapter, check if the storage file exists
    # if it does not, then use this as a flag to clean the old config
    fname = _get_storage_filename()
    if not os.path.exists(fname):
        invalidate_old_config()
    # namespace is equal to the current environment
    return SQLiteAdapter(
        fname,
        namespace=_resolve_namespace(environment),
        connect_params={"check_same_thread": False},
    )
