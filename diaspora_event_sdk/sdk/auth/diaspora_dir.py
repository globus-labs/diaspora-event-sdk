# Adapted from globus-compute SDK (Apache 2.0)
# https://github.com/globus/globus-compute/blob/68b1174cc06d4e91f49663128951a0c0080abef9/compute_sdk/globus_compute_sdk/sdk/compute_dir.py
from __future__ import annotations

import os
import pathlib


def ensure_diaspora_dir() -> pathlib.Path:
    dirname = pathlib.Path.home() / ".diaspora"

    user_dir = os.getenv("DIASPORA_USER_DIR")
    if user_dir:
        dirname = pathlib.Path(user_dir)

    if dirname.is_dir():
        pass
    elif dirname.is_file():
        raise FileExistsError(
            f"Error creating directory {dirname}, "
            "please remove or rename the conflicting file"
        )
    else:
        dirname.mkdir(mode=0o700, parents=True, exist_ok=True)

    return dirname
