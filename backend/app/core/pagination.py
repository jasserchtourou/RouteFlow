from pydantic import BaseModel, Field

MAX_PAGE_SIZE = 100


class PageParams(BaseModel):
    """Offset pagination. Simple and fine for operator UIs with a few thousand rows; switch a
    collection to keyset (cursor) pagination if it grows to where deep OFFSETs get slow."""

    limit: int = Field(default=20, ge=1, le=MAX_PAGE_SIZE, description="Page size")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")


class Page[T](BaseModel):
    items: list[T]
    total: int = Field(description="Total number of items matching the filters")
    limit: int
    offset: int
