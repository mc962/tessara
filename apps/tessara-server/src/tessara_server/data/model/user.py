from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Identity, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tessara_server.data.model.base import Base

if TYPE_CHECKING:
    from tessara_server.data.model.api_token import ApiToken


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer().with_variant(BigInteger(), "postgresql"),
        Identity(),
        primary_key=True,
    )
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    api_tokens: Mapped[list["ApiToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
