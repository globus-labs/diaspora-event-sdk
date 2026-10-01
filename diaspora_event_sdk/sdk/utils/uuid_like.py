from __future__ import annotations

import uuid

UUID_LIKE_T = uuid.UUID | str


def as_uuid(uuid_like: UUID_LIKE_T) -> uuid.UUID:
    return uuid_like if isinstance(uuid_like, uuid.UUID) else uuid.UUID(uuid_like)


def as_optional_uuid(optional_uuid_like: UUID_LIKE_T | None) -> uuid.UUID | None:
    return as_uuid(optional_uuid_like) if optional_uuid_like else None
