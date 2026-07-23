"""API token management REST endpoints — superuser-only, can manage any user's tokens."""

import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from tessara_server.data.database.dependencies import DatabaseSessionDependency
from tessara_server.data.repository import api_token_repository
from tessara_server.web.dependencies.auth import require_superuser_any

router = APIRouter(
    prefix="/api/api-tokens",
    tags=["api-tokens"],
    dependencies=[Depends(require_superuser_any)],
)


class ApiTokenResponse(BaseModel):
    id: int
    user_id: int
    name: str
    token_prefix: str
    is_active: bool
    last_used_at: datetime.datetime | None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ApiTokenCreateResponse(ApiTokenResponse):
    token: str = Field(..., description="Plaintext token — shown only once, store it now")


class ApiTokenCreate(BaseModel):
    user_id: int
    name: str = Field(..., min_length=1)


@router.get("", response_model=list[ApiTokenResponse])
async def list_api_tokens(
    user_id: int, session: DatabaseSessionDependency
) -> list[ApiTokenResponse]:
    tokens = await api_token_repository.list_for_user(session, user_id)
    return [ApiTokenResponse.model_validate(t) for t in tokens]


@router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=ApiTokenCreateResponse
)
async def create_api_token(
    data: ApiTokenCreate,
    session: DatabaseSessionDependency,
) -> ApiTokenCreateResponse:
    token, plaintext = await api_token_repository.create(
        session, data.user_id, data.name
    )
    return ApiTokenCreateResponse(
        id=token.id,
        user_id=token.user_id,
        name=token.name,
        token_prefix=token.token_prefix,
        is_active=token.is_active,
        last_used_at=token.last_used_at,
        created_at=token.created_at,
        token=plaintext,
    )


@router.patch("/{token_id}/toggle", response_model=ApiTokenResponse)
async def toggle_api_token(
    token_id: int,
    session: DatabaseSessionDependency,
) -> ApiTokenResponse:
    token = await api_token_repository.get_by_id(session, token_id)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Token not found"
        )
    await api_token_repository.toggle_active(session, token_id)
    await session.refresh(token)
    return ApiTokenResponse.model_validate(token)


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_token(
    token_id: int,
    session: DatabaseSessionDependency,
) -> None:
    token = await api_token_repository.get_by_id(session, token_id)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Token not found"
        )
    await api_token_repository.delete(session, token_id)
