import datetime

from sqlalchemy import BigInteger, Boolean, Identity, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from tessera_server.data.model.base import Base, UtcDateTime


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(
        Integer().with_variant(BigInteger(), "postgresql"),
        Identity(),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    key_prefix: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    key_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(
        UtcDateTime, nullable=True
    )
