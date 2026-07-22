from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_server.data.database.connection import get_db_session

DatabaseSessionDependency = Annotated[AsyncSession, Depends(get_db_session)]
