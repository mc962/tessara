import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "pk": "pk_%(table_name)s",
}


class UtcDateTime(TypeDecorator):
    """TIMESTAMP (no tz) column that always returns UTC-aware datetimes on read.

    Keeps the DB column as plain TIMESTAMP while ensuring Python always sees
    timezone.utc — so strftime('%Z') works and comparisons against aware
    datetimes don't raise TypeError.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self, value: datetime.datetime | None, dialect: object
    ) -> datetime.datetime | None:
        if value is None:
            return value
        # Store as naive UTC — column is TIMESTAMP WITHOUT TIME ZONE
        return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)

    def process_result_value(
        self, value: datetime.datetime | None, dialect: object
    ) -> datetime.datetime | None:
        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=datetime.timezone.utc)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    created_at: Mapped[datetime.datetime] = mapped_column(
        UtcDateTime,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        UtcDateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
