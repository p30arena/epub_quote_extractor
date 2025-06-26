# schemas.py
from pydantic import BaseModel, Field
from typing import Optional
import enum

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship

# Pydantic model for LLM structured output
class QuoteLLM(BaseModel):
    quote_text: str = Field(description="The exact text of the saying or quote.")
    speaker: Optional[str] = Field(None, description="The person or character who uttered the saying. If unknown, can be null.")
    context: Optional[str] = Field(None, description="The immediate context surrounding the quote, helping to understand its meaning.")
    topic: Optional[str] = Field(None, description="The main topic or theme of the quote.")
    additional_info: Optional[str] = Field(None, description="A JSON string containing other relevant information. Expected keys include 'surah' (the name of the Surah in Farsi) and, if the quote_text is in Arabic, 'quote_translation' (the Farsi translation of the quote). Example: '{\"surah\": \"سورة الفاتحة\", \"quote_translation\": \"به نام خداوند بخشنده مهربان\"}'")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "quote_text": "The only way to do great work is to love what you do.",
                    "speaker": "Steve Jobs",
                    "context": "Stanford commencement address, 2005.",
                    "topic": "Passion and Work",
                    "additional_info": "Often cited motivational quote."
                }
            ]
        }
    }

# SQLAlchemy base model
Base = declarative_base()

# SQLAlchemy model for tracking processing progress
class ProgressDB(Base):
    __tablename__ = "progress"

    id: int = Column(Integer, primary_key=True, index=True)
    epub_filepath: str = Column(String(1024), unique=True, nullable=False, index=True,
                                comment="Absolute path to the EPUB file being processed.")
    last_processed_chunk_index: int = Column(Integer, nullable=False, default=0,
                                             comment="The index of the last chunk successfully processed for this EPUB.")

    def __repr__(self):
        return f"<ProgressDB(id={self.id}, epub_filepath='{self.epub_filepath[:50]}...', last_processed_chunk_index={self.last_processed_chunk_index})>"

# SQLAlchemy model for storing quotes in the database
from sqlalchemy import UniqueConstraint

class QuoteDB(Base):
    __tablename__ = "quotes"
    __table_args__ = (UniqueConstraint('epub_source_identifier', 'quote_text', name='_epub_quote_uc'),)

    id: int = Column(Integer, primary_key=True, index=True)
    # This field will store the 'source' (chapter/section identifier) from epub_parser.py
    epub_source_identifier: str = Column(String(512), index=True, comment="Identifier from the EPUB, like chapter title or section ID where the quote was found.")
    quote_text: str = Column(Text, nullable=False)
    speaker: Optional[str] = Column(String(255), nullable=True) # Made Optional[str] consistent with Column definition
    context: Optional[str] = Column(Text, nullable=True) # Made Optional[str] consistent with Column definition
    topic: Optional[str] = Column(String(255), nullable=True, index=True) # Made Optional[str] consistent with Column definition
    additional_info: Optional[str] = Column(Text, nullable=True) # Made Optional[str] consistent with Column definition

    approval = relationship("QuoteApprovalDB", back_populates="quote", uselist=False, cascade="all, delete-orphan")
    groups = relationship("QuoteToGroupDB", back_populates="quote", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<QuoteDB(id={self.id}, speaker='{self.speaker}', topic='{self.topic}', source='{self.epub_source_identifier[:30]}...')>"

    def to_dict(self):
        """Converts the SQLAlchemy model instance to a dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class QuoteStatusEnum(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"

class QuoteApprovalDB(Base):
    __tablename__ = "QuoteApproval"

    id: int = Column(Integer, primary_key=True, index=True)
    quote_id: int = Column(Integer, ForeignKey('quotes.id'), nullable=False, unique=True)
    status: str = Column(Enum(QuoteStatusEnum), default=QuoteStatusEnum.PENDING, nullable=False)
    approved_by: Optional[str] = Column(String(255), nullable=True)
    timestamp: str = Column(String, server_default='CURRENT_TIMESTAMP', nullable=False)

    quote = relationship("QuoteDB", back_populates="approval")

class QuoteGroupDB(Base):
    __tablename__ = "QuoteGroup"

    id: int = Column(Integer, primary_key=True, index=True)
    name: Optional[str] = Column(String(255), nullable=True)
    description: Optional[str] = Column(Text, nullable=True)

    quotes = relationship("QuoteToGroupDB", back_populates="group", cascade="all, delete-orphan")

class QuoteToGroupDB(Base):
    __tablename__ = "QuoteToGroup"
    __table_args__ = (PrimaryKeyConstraint('quote_id', 'group_id'),)

    quote_id: int = Column(Integer, ForeignKey('quotes.id'), nullable=False)
    group_id: int = Column(Integer, ForeignKey('QuoteGroup.id'), nullable=False)

    quote = relationship("QuoteDB", back_populates="groups")
    group = relationship("QuoteGroupDB", back_populates="quotes")

if __name__ == '__main__':
    # Basic test for Pydantic model
    print("--- Pydantic Model Test ---")
    test_quote_data_llm = {
        "quote_text": "To be or not to be, that is the question.",
        "speaker": "Hamlet",
        "context": "A soliloquy by Prince Hamlet in William Shakespeare's play Hamlet.",
        "topic": "Existentialism, Life and Death",
        "additional_info": "Act 3, Scene 1. One of the most famous lines in English literature."
    }
    try:
        quote_llm_instance = QuoteLLM(**test_quote_data_llm)
        print("Pydantic model instance created successfully:")
        print(quote_llm_instance.model_dump_json(indent=2))
    except Exception as e:
        print(f"Pydantic model test failed: {e}")

    # Basic output for SQLAlchemy model structure
    print("\n--- SQLAlchemy Model Structure (QuoteDB) ---")
    print(f"Table name: {QuoteDB.__tablename__}")
    print("Columns:")
    for column in QuoteDB.__table__.columns:
        print(f"  - Name: {column.name}")
        print(f"    Type: {column.type}")
        print(f"    Primary Key: {column.primary_key}")
        print(f"    Nullable: {column.nullable}")
        print(f"    Index: {column.index}")
        if hasattr(column, 'comment') and column.comment:
            print(f"    Comment: {column.comment}")

    # Example of creating an instance (not persisted to DB here)
    try:
        db_quote_instance = QuoteDB(
            epub_source_identifier="Chapter 1: The Beginning",
            quote_text="It was a dark and stormy night.",
            speaker="Narrator",
            context="The opening line of the novel.",
            topic="Suspense",
            additional_info="A classic cliché."
        )
        print("\nSQLAlchemy model instance created (not persisted):")
        print(db_quote_instance)
    except Exception as e:
        print(f"SQLAlchemy instance creation test failed: {e}")

    print("\n--- SQLAlchemy Model Structure (ProgressDB) ---")
    print(f"Table name: {ProgressDB.__tablename__}")
    print("Columns:")
    for column in ProgressDB.__table__.columns:
        print(f"  - Name: {column.name}")
        print(f"    Type: {column.type}")
        print(f"    Primary Key: {column.primary_key}")
        print(f"    Nullable: {column.nullable}")
        print(f"    Index: {column.index}")
        if hasattr(column, 'comment') and column.comment:
            print(f"    Comment: {column.comment}")

    # Example of creating a ProgressDB instance (not persisted to DB here)
    try:
        db_progress_instance = ProgressDB(
            epub_filepath="/path/to/my/book.epub",
            last_processed_chunk_index=123
        )
        print("\nProgressDB instance created (not persisted):")
        print(db_progress_instance)
    except Exception as e:
        print(f"ProgressDB instance creation test failed: {e}")
