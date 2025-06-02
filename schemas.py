# schemas.py
from pydantic import BaseModel, Field
from typing import Optional

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text

# Pydantic model for LLM structured output
class QuoteLLM(BaseModel):
    quote_text: str = Field(description="The exact text of the saying or quote.")
    speaker: Optional[str] = Field(None, description="The person or character who uttered the saying. If unknown, can be null.")
    context: Optional[str] = Field(None, description="The immediate context surrounding the quote, helping to understand its meaning.")
    topic: Optional[str] = Field(None, description="The main topic or theme of the quote.")
    additional_info: Optional[str] = Field(None, description="A JSON string containing other relevant information. Expected keys include 'surah' (the name of the Surah in Farsi) and, if the quote_text is in Arabic, 'quote_translation' (the Farsi translation of the quote). Example: '{\\"surah\\": \\"سورة الفاتحة\\", \\"quote_translation\\": \\"به نام خداوند بخشنده مهربان\\"}'")

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

# SQLAlchemy model for storing quotes in the database
class QuoteDB(Base):
    __tablename__ = "quotes"

    id: int = Column(Integer, primary_key=True, index=True)
    # This field will store the 'source' (chapter/section identifier) from epub_parser.py
    epub_source_identifier: str = Column(String(512), index=True, comment="Identifier from the EPUB, like chapter title or section ID where the quote was found.")
    quote_text: str = Column(Text, nullable=False)
    speaker: Optional[str] = Column(String(255), nullable=True) # Made Optional[str] consistent with Column definition
    context: Optional[str] = Column(Text, nullable=True) # Made Optional[str] consistent with Column definition
    topic: Optional[str] = Column(String(255), nullable=True, index=True) # Made Optional[str] consistent with Column definition
    additional_info: Optional[str] = Column(Text, nullable=True) # Made Optional[str] consistent with Column definition

    def __repr__(self):
        return f"<QuoteDB(id={self.id}, speaker='{self.speaker}', topic='{self.topic}', source='{self.epub_source_identifier[:30]}...')>"

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
