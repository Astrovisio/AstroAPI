from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import field_validator
from sqlmodel import Field, SQLModel

from api.exceptions import InvalidFileExtensionError, MixedFileTypesError


class TimestampMixin(SQLModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
