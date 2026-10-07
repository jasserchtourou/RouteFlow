from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_session

# Reusable annotated dependencies: endpoints declare `session: DbSession` and FastAPI's
# dependency injection builds and cleans up the object per request.
DbSession = Annotated[AsyncSession, Depends(get_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]
