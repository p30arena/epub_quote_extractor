# epub_quote_extractor/main.py
import argparse
import json # For potential pretty printing if needed
from pathlib import Path
from typing import List, Dict, Any

from epub_parser import extract_text_from_epub, chunk_text
from llm_handler import analyze_text_with_gemini, DEFAULT_MODEL_NAME as LLM_DEFAULT_MODEL # import model name
from database import create_db_and_tables, get_db, save_quotes_to_db
from schemas import QuoteLLM # For validation

# Pydantic is needed for QuoteLLM validation
try:
    from pydantic import ValidationError
except ImportError:
    print("CRITICAL Error: Pydantic library is not installed. Please install it: pip install pydantic")
    # Fallback to allow script to run but without validation, not recommended for production
    class ValidationError(Exception): pass
    def main_no_pydantic():
        print("Pydantic is not available. Cannot perform quote validation. Aborting.")
    if __name__ == '__main__':
        main_no_pydantic()
        exit(1)


DEFAULT_MAX_CHUNK_SIZE = 15000 # Characters. Adjusted based on typical LLM input sizes for single calls.
DEFAULT_DB_BATCH_SIZE = 10

def main():
    parser = argparse.ArgumentParser(description="Extract quotes from EPUB ebooks using an LLM and store them in a database.")
    parser.add_argument("epub_filepath", type=str, help="Path to the EPUB file.")
    parser.add_argument(
        "--max-chunk-size",
        type=int,
        default=DEFAULT_MAX_CHUNK_SIZE,
        help=f"Maximum size of text chunks (characters) sent to the LLM (default: {DEFAULT_MAX_CHUNK_SIZE}). This is passed to the chunk_text function."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_DB_BATCH_SIZE,
        help=f"Number of quotes to batch before saving to the database (default: {DEFAULT_DB_BATCH_SIZE})."
    )
    args = parser.parse_args()

    epub_file = Path(args.epub_filepath)
    if not epub_file.is_file():
        print(f"Error: EPUB file not found at {args.epub_filepath}")
        return

    print("Step 1: Initializing database...")
    try:
        create_db_and_tables() # Ensures tables are ready based on schemas.py
        print("Database initialized successfully (tables checked/created).")
    except Exception as e:
        print(f"Fatal: Could not initialize database: {e}")
        print("Please check your database configuration (e.g., in .env) and ensure the database server is operational.")
        return

    print(f"\nStep 2: Processing EPUB file: {epub_file.name}")
    try:
        text_segments = extract_text_from_epub(str(epub_file))
        if not text_segments:
            print("No text segments extracted from the EPUB. Nothing to process.")
            return
        print(f"  Extracted {len(text_segments)} initial segments from EPUB.")

        actual_max_chunk_size = args.max_chunk_size
        print(f"  Using max character chunk size for LLM input: {actual_max_chunk_size}")

        text_chunks = chunk_text(text_segments, actual_max_chunk_size)
        if not text_chunks:
            print("No text chunks to process after segmentation and chunking.")
            return
        print(f"  Segmented into {len(text_chunks)} processable text chunks.")

    except Exception as e:
        print(f"Error processing EPUB file '{epub_file.name}': {e}")
        return

    total_quotes_identified_by_llm = 0
    total_quotes_validated_and_saved = 0
    quotes_to_save_batch: List[Dict[str, Any]] = []

    # Initialize database session
    db_session_gen = get_db()
    db = next(db_session_gen)

    print(f"\nStep 3: Starting quote extraction with LLM ({LLM_DEFAULT_MODEL})...")

    try:
        for i, chunk_info in enumerate(text_chunks):
            chunk_source_preview = chunk_info['source'][:100].replace('\n', ' ')
            print(f"  Processing chunk {i + 1}/{len(text_chunks)} (Source: '{chunk_source_preview}...', Length: {len(chunk_info['text'])} chars)")

            # Call LLM for the current chunk
            llm_output_list = analyze_text_with_gemini(chunk_info['text'])

            if llm_output_list is not None: # analyze_text_with_gemini returns None on total failure, [] if no quotes
                if not llm_output_list: # Empty list means LLM found no quotes
                    print(f"    LLM found no quotes in chunk {i+1}.")
                else:
                    print(f"    LLM identified {len(llm_output_list)} potential quotes in chunk {i+1}.")
                    total_quotes_identified_by_llm += len(llm_output_list)

                    for quote_data_from_llm in llm_output_list:
                        if not isinstance(quote_data_from_llm, dict):
                            print(f"    Warning: LLM returned a non-dictionary item in its list: {quote_data_from_llm}. Skipping this item.")
                            continue
                        try:
                            # Validate data against Pydantic model (QuoteLLM)
                            validated_quote = QuoteLLM(**quote_data_from_llm)

                            # Prepare data for QuoteDB model
                            db_quote_data = validated_quote.model_dump() # Convert Pydantic model to dict
                            db_quote_data['epub_source_identifier'] = chunk_info['source'] # Add the source identifier

                            quotes_to_save_batch.append(db_quote_data)
                            # print(f"      + Valid quote added to batch: '{validated_quote.quote_text[:60]}...'")

                        except ValidationError as e_pydantic:
                            print(f"    Validation Error for LLM output item: {e_pydantic}")
                            print(f"      Problematic data from LLM: {json.dumps(quote_data_from_llm, indent=2)}")
                        except Exception as e_val_other:
                            print(f"    Unexpected error processing/validating quote data: {e_val_other}")
                            print(f"      Data: {json.dumps(quote_data_from_llm, indent=2)}")

                # Save to DB if batch size is reached
                if len(quotes_to_save_batch) >= args.batch_size:
                    try:
                        num_actually_saved = save_quotes_to_db(db, quotes_to_save_batch)
                        print(f"    Saved batch of {num_actually_saved} quotes to database.")
                        total_quotes_validated_and_saved += num_actually_saved
                        quotes_to_save_batch.clear()
                    except Exception as e_db_batch_save:
                        print(f"    Error saving batch to database: {e_db_batch_save}. Quotes in this batch might be lost.")
                        quotes_to_save_batch.clear() # Clear to prevent reprocessing or error loops
            else:
                # This means analyze_text_with_gemini had a critical failure after all retries
                print(f"    Failed to get response from LLM for chunk {i + 1} after retries. Skipping this chunk.")

        # Save any remaining quotes in the final batch
        if quotes_to_save_batch:
            try:
                num_actually_saved_final = save_quotes_to_db(db, quotes_to_save_batch)
                print(f"  Saved final batch of {num_actually_saved_final} quotes to database.")
                total_quotes_validated_and_saved += num_actually_saved_final
                quotes_to_save_batch.clear()
            except Exception as e_db_final_save:
                print(f"    Error saving final batch to database: {e_db_final_save}.")

    except Exception as e_main_loop:
        print(f"Caught an exception in main processing loop. Type: {type(e_main_loop)}")
        print(f"Exception repr: {e_main_loop!r}")
        print(f"An unexpected error occurred during the main processing loop: {e_main_loop}")
    finally:
        print("\nStep 4: Finalizing operations.")
        print("  Closing database session...")
        try:
            # The generator pattern for get_db() ensures 'finally' in get_db closes the session.
            # Calling next() might not be what's intended if the session is already yielded.
            # Instead, rely on the 'finally' block within 'get_db()'.
            # For explicit closure, one might pass the session object around and close it directly.
            # However, the provided `get_db` pattern handles closure.
            db.close() # Explicitly close the session obtained from `next(db_session_gen)`
            print("  Database session closed.")
        except Exception as e_close:
            print(f"  Error closing database session: {e_close}")

    print("\n--- Processing Complete ---")
    print(f"EPUB file processed: {epub_file.name}")
    print(f"Initial text segments extracted: {len(text_segments) if 'text_segments' in locals() and text_segments is not None else 'N/A'}")
    print(f"Text chunks processed by LLM: {len(text_chunks) if 'text_chunks' in locals() and text_chunks is not None else 'N/A'}")
    print(f"Total potential quotes identified by LLM: {total_quotes_identified_by_llm}")
    print(f"Total quotes successfully validated and saved to database: {total_quotes_validated_and_saved}")
    print("--- Done ---")

if __name__ == '__main__':
    main()
