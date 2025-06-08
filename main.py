# epub_quote_extractor/main.py
import argparse
import traceback
import json # For potential pretty printing if needed
from pathlib import Path
from typing import List, Dict, Any

from epub_parser import extract_text_from_epub, chunk_text
from llm_handler import analyze_text_with_gemini, DEFAULT_MODEL_NAME as LLM_DEFAULT_MODEL # import model name
from database import create_db_and_tables, get_db, save_quotes_to_db, load_progress, save_progress, clear_progress # Import progress functions
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
DEFAULT_OVERLAP_SIZE = int(DEFAULT_MAX_CHUNK_SIZE * 0.1) # Characters. Default overlap for chunking. Ensure it's an integer.
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
        "--overlap-size",
        type=int,
        default=DEFAULT_OVERLAP_SIZE,
        help=f"Number of characters to overlap between consecutive text chunks (default: {DEFAULT_OVERLAP_SIZE}). This is passed to the chunk_text function."
    )
    parser.add_argument(
        "--context-before-chars",
        type=int,
        default=DEFAULT_OVERLAP_SIZE, # Using overlap size as a reasonable default for context
        help=f"Number of characters from the *previous* chunk to include as context (default: {DEFAULT_OVERLAP_SIZE})."
    )
    parser.add_argument(
        "--context-after-chars",
        type=int,
        default=DEFAULT_OVERLAP_SIZE, # Using overlap size as a reasonable default for context
        help=f"Number of characters from the *next* chunk to include as context (default: {DEFAULT_OVERLAP_SIZE})."
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

    # Initialize database session for progress tracking and main operations
    db_session_gen = get_db()
    db = next(db_session_gen)

    # Load existing progress
    start_chunk_index = 0
    try:
        loaded_progress_index = load_progress(db, str(epub_file.resolve())) # Use absolute path for consistency
        if loaded_progress_index is not None:
            start_chunk_index = loaded_progress_index + 1 # Start from the next chunk
            print(f"Resuming processing from chunk index {start_chunk_index} for '{epub_file.name}'.")
    except Exception as e:
        print(f"Warning: Could not load previous progress for '{epub_file.name}': {e}. Starting from beginning.")
        start_chunk_index = 0 # Fallback to start from beginning if progress loading fails

    print(f"\nStep 2: Processing EPUB file: {epub_file.name}")
    try:
        text_segments = extract_text_from_epub(str(epub_file))
        if not text_segments:
            print("No text segments extracted from the EPUB. Nothing to process.")
            return
        print(f"  Extracted {len(text_segments)} initial segments from EPUB.")

        actual_max_chunk_size = args.max_chunk_size
        actual_overlap_size = args.overlap_size
        print(f"  Using max character chunk size for LLM input: {actual_max_chunk_size}")
        print(f"  Using overlap size for chunking: {actual_overlap_size}")

        text_chunks = chunk_text(text_segments, actual_max_chunk_size, actual_overlap_size)
        if not text_chunks:
            print("No text chunks to process after segmentation and chunking.")
            return
        print(f"  Segmented into {len(text_chunks)} processable text chunks.")

        if start_chunk_index >= len(text_chunks):
            print(f"All chunks for '{epub_file.name}' already processed according to saved progress. Clearing progress and exiting.")
            clear_progress(db, str(epub_file.resolve()))
            return

    except Exception as e:
        print(f"Error processing EPUB file '{epub_file.name}': {e}")
        return

    total_quotes_identified_by_llm = 0
    total_quotes_validated_and_saved = 0
    quotes_to_save_batch: List[Dict[str, Any]] = []

    print(f"\nStep 3: Starting quote extraction with LLM ({LLM_DEFAULT_MODEL})...")
    print(f"  Starting from chunk {start_chunk_index + 1} of {len(text_chunks)}.")

    try:
        for i in range(start_chunk_index, len(text_chunks)):
            chunk_info = text_chunks[i]
            chunk_source_preview = chunk_info['source'][:100].replace('\n', ' ')
            print(f"  Processing chunk {i + 1}/{len(text_chunks)} (Source: '{chunk_source_preview}...', Length: {len(chunk_info['text'])} chars)")

            # Construct the full contextual text for the LLM
            current_chunk_text = chunk_info['text']
            context_before = ""
            context_after = ""

            # Get context from previous chunk if available
            if i > 0:
                prev_chunk_text = text_chunks[i-1]['text']
                context_before = prev_chunk_text[-args.context_before_chars:] + "\n\n... (Previous Section Continued) ...\n\n"

            # Get context from next chunk if available
            if i < len(text_chunks) - 1:
                next_chunk_text = text_chunks[i+1]['text']
                context_after = "\n\n... (Next Section Continued) ...\n\n" + next_chunk_text[:args.context_after_chars]

            full_context_text = f"{context_before}{current_chunk_text}{context_after}"

            print(f"DEBUG_MAIN: Calling analyze_text_with_gemini for chunk: {chunk_info['source'][:50]} (Contextual length: {len(full_context_text)} chars)")
            # Call LLM for the current chunk with surrounding context
            llm_output_list = analyze_text_with_gemini(full_context_text)
            print(f"DEBUG_MAIN: Returned from analyze_text_with_gemini. Type: {type(llm_output_list)}, Content: {str(llm_output_list)[:500]}")

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
                            # Handle additional_info: if it's a dict, convert to JSON string
                            # This ensures compatibility with QuoteLLM which expects a string that is JSON.
                            ai = quote_data_from_llm.get("additional_info")
                            if isinstance(ai, dict):
                                quote_data_from_llm["additional_info"] = json.dumps(ai, ensure_ascii=False)

                            # Validate data against Pydantic model (QuoteLLM)
                            validated_quote = QuoteLLM(**quote_data_from_llm)

                            # Prepare data for QuoteDB model
                            db_quote_data = validated_quote.model_dump() # Convert Pydantic model to dict
                            # Add the source identifier including the estimated page number
                            db_quote_data['epub_source_identifier'] = f"{chunk_info['source']} (Est. Page: {chunk_info['estimated_page']})"

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

            # Save progress after each chunk is processed
            try:
                save_progress(db, str(epub_file.resolve()), i)
            except Exception as e_save_progress:
                print(f"Warning: Could not save progress for chunk {i} of '{epub_file.name}': {e_save_progress}")

        # Save any remaining quotes in the final batch
        if quotes_to_save_batch:
            try:
                num_actually_saved_final = save_quotes_to_db(db, quotes_to_save_batch)
                print(f"  Saved final batch of {num_actually_saved_final} quotes to database.")
                total_quotes_validated_and_saved += num_actually_saved_final
                quotes_to_save_batch.clear()
            except Exception as e_db_final_save:
                print(f"    Error saving final batch to database: {e_db_final_save}.")

        # Clear progress if all chunks were processed successfully
        print(f"All {len(text_chunks)} chunks processed for '{epub_file.name}'. Clearing progress.")
        clear_progress(db, str(epub_file.resolve()))

    except Exception as e_main_loop:
        print(f"Caught an exception in main processing loop. Type: {type(e_main_loop)}")
        print(f"Exception repr: {e_main_loop!r}")
        print("--- Full Traceback ---")
        traceback.print_exc()
        print("--- End Traceback ---")
        print(f"An unexpected error occurred during the main processing loop: {e_main_loop}")
    finally:
        print("\nStep 4: Finalizing operations.")
        print("  Closing database session...")
        try:
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
