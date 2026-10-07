from enum import StrEnum

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_checks, enum_column


class DocumentType(StrEnum):
    PROCEDURE = "PROCEDURE"
    POLICY = "POLICY"
    GUIDELINE = "GUIDELINE"
    SLA = "SLA"


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Knowledge-base document. Chunks and embeddings are added in the RAG phase."""

    __tablename__ = "documents"
    __table_args__ = (*enum_checks(document_type=DocumentType),)

    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    document_type: Mapped[DocumentType] = mapped_column(enum_column(DocumentType, "document_type"))
    source: Mapped[str] = mapped_column(String(200))
