"""API key management REST endpoints."""

import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from tessara_server.data.database.dependencies import DatabaseSessionDependency
from tessara_server.data.repository import api_key_repository
from tessara_server.web.dependencies.auth import require_superuser_any

router = APIRouter(
    prefix="/api/api-keys",
    tags=["api-keys"],
    dependencies=[Depends(require_superuser_any)],
)


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    is_superuser: bool
    is_active: bool
    last_used_at: datetime.datetime | None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreateResponse(ApiKeyResponse):
    key: str = Field(..., description="Plaintext key — shown only once, store it now")


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1)
    is_superuser: bool = False


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(session: DatabaseSessionDependency) -> list[ApiKeyResponse]:
    keys = await api_key_repository.list_all(session)
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=ApiKeyCreateResponse
)
async def create_api_key(
    data: ApiKeyCreate,
    session: DatabaseSessionDependency,
) -> ApiKeyCreateResponse:
    key, plaintext = await api_key_repository.create(
        session,
        data.name,
        is_superuser=data.is_superuser,
    )
    return ApiKeyCreateResponse(
        id=key.id,
        name=key.name,
        key_prefix=key.key_prefix,
        is_superuser=key.is_superuser,
        is_active=key.is_active,
        last_used_at=key.last_used_at,
        created_at=key.created_at,
        key=plaintext,
    )


@router.patch("/{key_id}/toggle", response_model=ApiKeyResponse)
async def toggle_api_key(
    key_id: int,
    session: DatabaseSessionDependency,
) -> ApiKeyResponse:
    key = await api_key_repository.get_by_id(session, key_id)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Key not found"
        )
    await api_key_repository.toggle_active(session, key_id)
    await session.refresh(key)
    return ApiKeyResponse.model_validate(key)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: int,
    session: DatabaseSessionDependency,
) -> None:
    key = await api_key_repository.get_by_id(session, key_id)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Key not found"
        )
    await api_key_repository.delete(session, key_id)
