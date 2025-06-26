# epub_quote_extractor/database.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Generator, Any, Optional

# Relative import for schemas
from schemas import Base, QuoteDB, ProgressDB, QuoteApprovalDB, QuoteStatusEnum
from sqlalchemy.dialects import postgresql # For on_conflict_do_nothing and on_conflict_do_update

# Load environment variables from .env file
load_dotenv(override=True) # Ensure .env variables override existing ones

DB_USER = os.getenv("DB_USER", "your_db_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_db_password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME") # Remove default to ensure it's read from .env or is None

print(f"DEBUG: DB_USER={DB_USER}, DB_PASSWORD={'*' * len(DB_PASSWORD) if DB_PASSWORD else 'None'}, DB_HOST={DB_HOST}, DB_PORT={DB_PORT}, DB_NAME={DB_NAME}")

# Construct DATABASE_URL. Fallback to SQLite if PostgreSQL details are default or DB_NAME is not set.
# This provides a more robust default if a PostgreSQL server isn't readily available.
if DB_USER == "your_db_user" or DB_PASSWORD == "your_db_password" or not DB_NAME or not os.getenv("DB_USER"): # Check if DB_USER is not set or DB_NAME is None/empty
    print(f"WARNING: Default PostgreSQL credentials/name detected or DB_USER not set for '{DB_NAME}'. ")
    print("This script will attempt to fall back to a local SQLite database 'quotes_fallback.db'.")
    print("To use PostgreSQL, ensure DB_USER, DB_PASSWORD, and DB_NAME are set in your environment or .env file.")
    DATABASE_URL = "sqlite:///./quotes_fallback.db"
    DB_ENGINE_TYPE = "sqlite"
else:
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    DB_ENGINE_TYPE = "postgresql"
    print(f"Attempting to connect to PostgreSQL database: {DB_NAME} on {DB_HOST}:{DB_PORT}")


engine = create_engine(DATABASE_URL, echo=False) # Set echo=True for debugging SQL
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_db_and_tables():
    # Creates database tables based on SQLAlchemy models.
    try:
        Base.metadata.create_all(bind=engine)
        db_location = DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL and DB_ENGINE_TYPE == "postgresql" else DATABASE_URL
        print(f"Database tables checked/created successfully for {DB_ENGINE_TYPE} at {db_location}.")
    except Exception as e:
        db_location = DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL and DB_ENGINE_TYPE == "postgresql" else DATABASE_URL
        print(f"Error creating database tables for {DB_ENGINE_TYPE} ({db_location}): {e}")
        print("Continuing without table creation due to error. Ensure database server is running and accessible.")


def get_db() -> Generator[Session, Any, None]:
    # Dependency to get a DB session, ensuring it is closed.
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_quotes_to_db(db: Session, quotes_data: List[dict]) -> int:
    # Saves a list of quote data to the database.
    # Each item in quotes_data should be a dictionary matching QuoteDB fields.
    # Returns the number of quotes saved.

    valid_quotes_data = [q for q in quotes_data if isinstance(q, dict) and q]
    if not valid_quotes_data:
        print("No valid quote data provided to save.")
        return 0

    db_quotes = []
    for data in valid_quotes_data:
        try:
            db_quotes.append(QuoteDB(**data))
        except Exception as e:
            print(f"Error creating QuoteDB instance with data {data}: {e}")
            # Optionally skip this quote or handle error differently
            continue # Skip malformed data

    if not db_quotes:
        print("No QuoteDB instances could be created from the provided data.")
        return 0

    try:
        if DB_ENGINE_TYPE == "postgresql":
            inserted_count = 0
            for quote_obj in db_quotes:
                quote_dict = quote_obj.to_dict()
                quote_dict.pop('id', None)

                stmt = postgresql.insert(QuoteDB).values(**quote_dict).returning(QuoteDB.id)
                do_nothing_stmt = stmt.on_conflict_do_nothing(
                    index_elements=['epub_source_identifier', 'quote_text']
                )
                result = db.execute(do_nothing_stmt)
                inserted_id = result.scalar_one_or_none()

                if inserted_id is not None:
                    inserted_count += 1
                    # Create a corresponding QuoteApprovalDB record
                    approval_record = QuoteApprovalDB(
                        quote_id=inserted_id,
                        status=QuoteStatusEnum.PENDING
                    )
                    db.add(approval_record)

            db.commit()
            return inserted_count
        else:
            # For SQLite or other databases, fall back to add_all and commit.
            # Unique constraint will raise an IntegrityError if duplicates exist.
            db.add_all(db_quotes)
            db.commit()
            for quote in db_quotes:
                db.refresh(quote) # Refresh to get auto-generated IDs if needed
            return len(db_quotes)
    except Exception as e:
        db.rollback()
        print(f"Error saving quotes to database ({DB_ENGINE_TYPE}): {e}")
        # Re-raise the exception to be caught by the main loop for logging
        raise

def save_progress(db: Session, epub_filepath: str, last_processed_chunk_index: int):
    """
    Saves or updates the processing progress for a given EPUB file.
    Uses ON CONFLICT DO UPDATE for PostgreSQL.
    """
    if DB_ENGINE_TYPE == "postgresql":
        stmt = postgresql.insert(ProgressDB).values(
            epub_filepath=epub_filepath,
            last_processed_chunk_index=last_processed_chunk_index
        )
        on_conflict_stmt = stmt.on_conflict_do_update(
            index_elements=['epub_filepath'], # Unique index on epub_filepath
            set_=dict(last_processed_chunk_index=last_processed_chunk_index)
        )
        try:
            db.execute(on_conflict_stmt)
            db.commit()
            print(f"Progress saved for '{epub_filepath}': chunk {last_processed_chunk_index}")
        except Exception as e:
            db.rollback()
            print(f"Error saving progress for '{epub_filepath}': {e}")
            raise
    else:
        # For SQLite, a simpler approach: try to update, if not found, insert
        existing_progress = db.query(ProgressDB).filter(ProgressDB.epub_filepath == epub_filepath).first()
        if existing_progress:
            existing_progress.last_processed_chunk_index = last_processed_chunk_index
            print(f"Progress updated for '{epub_filepath}': chunk {last_processed_chunk_index}")
        else:
            new_progress = ProgressDB(epub_filepath=epub_filepath, last_processed_chunk_index=last_processed_chunk_index)
            db.add(new_progress)
            print(f"Progress inserted for '{epub_filepath}': chunk {last_processed_chunk_index}")
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error saving progress for '{epub_filepath}': {e}")
            raise

def load_progress(db: Session, epub_filepath: str) -> Optional[int]:
    """
    Loads the last processed chunk index for a given EPUB file.
    Returns the index or None if no progress is found.
    """
    progress_entry = db.query(ProgressDB).filter(ProgressDB.epub_filepath == epub_filepath).first()
    if progress_entry:
        print(f"Loaded progress for '{epub_filepath}': last processed chunk {progress_entry.last_processed_chunk_index}")
        return progress_entry.last_processed_chunk_index
    print(f"No saved progress found for '{epub_filepath}'.")
    return None

def clear_progress(db: Session, epub_filepath: str):
    """
    Clears the processing progress for a given EPUB file.
    """
    try:
        deleted_count = db.query(ProgressDB).filter(ProgressDB.epub_filepath == epub_filepath).delete()
        db.commit()
        if deleted_count > 0:
            print(f"Progress cleared for '{epub_filepath}'.")
        else:
            print(f"No progress found to clear for '{epub_filepath}'.")
    except Exception as e:
        db.rollback()
        print(f"Error clearing progress for '{epub_filepath}': {e}")
        raise

if __name__ == '__main__':
    print(f"--- Database Module ({DB_ENGINE_TYPE}) Main Execution ---")

    try:
        create_db_and_tables()
        print("Database initialization check complete.")

        print("\n--- Example: Saving quotes ---")

        db_session_generator = get_db()
        db_for_test: Session = next(db_session_generator)

        example_quotes_payload = [
            {
                "epub_source_identifier": "Chapter 1: Test Data",
                "quote_text": "This is a test quote for database.py.",
                "speaker": "Test Runner",
                "topic": "Database Test",
                "context": "Testing the save_quotes_to_db function."
            },
            {
                "epub_source_identifier": "Chapter 2: More Test Data",
                "quote_text": "Another test quote to ensure batching works.",
                "speaker": "Test Scribe",
                "topic": "Database Test",
                "additional_info": "Part of the __main__ block test."
            }
        ]

        try:
            print(f"Attempting to save {len(example_quotes_payload)} example quotes to {DB_ENGINE_TYPE}...")
            num_saved = save_quotes_to_db(db_for_test, example_quotes_payload)
            print(f"Successfully saved {num_saved} quotes to the database.")

            if num_saved > 0:
                retrieved_quotes = db_for_test.query(QuoteDB).limit(num_saved).all()
                print(f"Retrieved {len(retrieved_quotes)} quotes from the DB for verification:")
                for q_idx, q_obj in enumerate(retrieved_quotes):
                    print(f"  {q_idx+1}. ID: {q_obj.id}, Quote: '{q_obj.quote_text[:50]}...', Speaker: {q_obj.speaker}")
                    db_for_test.delete(q_obj)
                db_for_test.commit()
                print("Cleaned up test data by deleting saved quotes.")

        except Exception as e:
            db_location = DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL and DB_ENGINE_TYPE == "postgresql" else DATABASE_URL
            print(f"Error during database example usage in __main__ with {DB_ENGINE_TYPE} at {db_location}: {e}")
            if DB_ENGINE_TYPE == "postgresql":
                print(f"This might be due to issues connecting to PostgreSQL or table/DB creation problems.")
            else:
                 print(f"This might be due to file system permissions or issues with the SQLite file.")
        finally:
            # db_for_test.close() # Already closed by get_db generator's finally block
            pass # Keep this for clarity, as get_db handles closure

        print("\n--- Example: Progress Tracking ---")
        test_epub_path = "/path/to/test_book.epub"
        test_chunk_index = 5

        # Test saving progress
        save_progress(db_for_test, test_epub_path, test_chunk_index)
        save_progress(db_for_test, test_epub_path, test_chunk_index + 1) # Update progress

        # Test loading progress
        loaded_index = load_progress(db_for_test, test_epub_path)
        print(f"Loaded index: {loaded_index}, Expected: {test_chunk_index + 1}")

        # Test clearing progress
        clear_progress(db_for_test, test_epub_path)
        re_loaded_index = load_progress(db_for_test, test_epub_path)
        print(f"Re-loaded index after clear: {re_loaded_index}, Expected: None")

    except Exception as e_main:
        db_location = DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL and DB_ENGINE_TYPE == "postgresql" else DATABASE_URL
        print(f"Could not connect to the database ({DB_ENGINE_TYPE} at {db_location}) or create tables during __main__ test: {e_main}")
        if DB_ENGINE_TYPE == "postgresql":
            print("Please ensure your PostgreSQL server is running and configured correctly in .env or environment variables.")
        else:
            print("For SQLite, ensure the directory is writable and 'quotes_fallback.db' can be created/accessed.")
