"""
Document model for FinSight.
Storage-only model for document extraction metadata and facts.
(Document AI will be integrated in later phases).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.db import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)
    document_type = Column(String(50), nullable=False)  # e.g., 'receipt', 'invoice', 'bank_statement', 'bill'
    mime_type = Column(String(100), nullable=False)  # e.g., 'application/pdf', 'image/png'
    raw_text = Column(Text, nullable=True)
    extracted_facts = Column(JSON, nullable=True)  # Structured extracted facts JSON
    is_suspicious = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="documents")

    def __repr__(self) -> str:
        return (
            f"<Document(id={self.id}, user_id={self.user_id}, filename='{self.filename}', "
            f"type='{self.document_type}', is_suspicious={self.is_suspicious})>"
        )
