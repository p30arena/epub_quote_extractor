# Active Context: EPUB Quote Extractor

## Current Work Focus

The current focus is on initializing the project's memory bank with comprehensive documentation based on the initial project description. This foundational step ensures that all subsequent development is aligned with the project's goals and constraints.

## Recent Changes

*   **Memory Bank Initialized & Updated:** All core memory bank files have been created and subsequently updated to reflect the current state of the codebase.
*   **Unique Composite Index Implemented:** A unique composite index on `epub_source_identifier` and `quote_text` has been added to the `QuoteDB` model in `schemas.py` to prevent duplicate quote entries.
*   **Database Conflict Handling:** The `save_quotes_to_db` function in `database.py` has been modified to use `ON CONFLICT DO NOTHING` for PostgreSQL inserts, leveraging the new `to_dict()` method on `QuoteDB` for proper data mapping.
*   **Chunking Overlap Added:** The `chunk_text` function in `epub_parser.py` now supports an `overlap_size` parameter.
*   **Main Script Updated for Overlap:** `main.py` has been updated to accept `--overlap-size` as a command-line argument and pass it to the `chunk_text` function. The `DEFAULT_OVERLAP_SIZE` in `main.py` is now dynamically calculated as 0.1 of `DEFAULT_MAX_CHUNK_SIZE`.
*   **Progress Tracking Implemented:**
    *   A `ProgressDB` model has been added to `schemas.py` to store `epub_filepath` and `last_processed_chunk_index`.
    *   `save_progress`, `load_progress`, and `clear_progress` functions have been added to `database.py` to manage progress persistence.
    *   `main.py` now integrates these functions to enable resuming processing from the last saved chunk and clearing progress upon completion.
*   **LLM Prompt Refinement for Conversational Quotes:** The `QUOTE_EXTRACTION_PROMPT_TEMPLATE` in `prompts.py` has been updated to explicitly instruct the LLM to combine consecutive conversational turns into a single `quote_text` entry, with guidance on handling `speaker` and `context` for such cases.
*   **Heuristic-based Page Estimation Implemented:** `epub_parser.py` now includes a `CHARS_PER_ESTIMATED_PAGE` constant (set to 2000) and the `chunk_text` function calculates an `estimated_page` number for each chunk. `main.py` has been updated to incorporate this estimated page number into the `epub_source_identifier` (e.g., "Section ID: {section_id} (Est. Page: {estimated_page_number})").

## Next Steps

1.  **Environment Setup:** Set up the Python virtual environment and install all necessary dependencies as specified in `requirements.txt`.
2.  **Database Migration Setup:** Initialize Alembic for database migrations, ensuring it integrates with the existing SQLAlchemy models (`QuoteDB` and `ProgressDB`). This is crucial for applying the new unique constraint and the `progress` table to the database.
3.  **EPUB Page Number Refinement (Phase 2 & 3):** Continue to investigate and implement more precise page number extraction from EPUBs, or enhance `epub_source_identifier` if possible, beyond just section IDs and current heuristic. This includes exploring structural metadata and LLM-assisted extraction if needed.
4.  **LLM Prompt Optimization:** Further fine-tune the LLM prompts to improve extraction accuracy, especially for diverse EPUB content and complex quote structures.
5.  **Comprehensive Error Handling:** Enhance error handling across all modules, particularly for edge cases in EPUB parsing (e.g., malformed EPUBs), LLM response failures, and database integrity issues.
6.  **Testing:** Develop a comprehensive suite of unit, integration, and end-to-end tests to ensure reliability and correctness of the entire pipeline.
7.  **CLI Enhancements:** Improve the command-line interface for better user experience, including progress indicators, verbose logging options, and potentially more input options.

## Active Decisions and Considerations

*   **LLM Model Version:** Confirmed strict adherence to "gemini-2.0-flash" or "gemini-2.5-flash-preview-05-20" in `llm_handler.py`.
*   **Multilingual Fields:** Implementation in `prompts.py` and `schemas.py` confirms the handling of Farsi/Arabic for `speaker`, `context`, `topic`, `additional_info`, and no translation for `quote_text`.
*   **`additional_info` JSON Structure:** Confirmed the JSON format for `additional_info` including `surah` and optional `quote_translation` in `schemas.py` and `prompts.py`.
*   **`epub_source_identifier`:** Now includes an estimated page number based on character count (e.g., "Section ID: {item.get_id()} (Est. Page: {estimated_page_number})"). This is a significant improvement over just section IDs, though true page numbers remain a challenge.
*   **Conversational Quote Handling:** A specific instruction has been added to the LLM prompt to group consecutive conversational turns into a single quote, with guidelines for `speaker` and `context` fields.
*   **Database Fallback:** The `database.py` module includes a fallback to SQLite if PostgreSQL environment variables are not properly configured, which is a useful development feature.
*   **LLM Response Robustness:** `llm_handler.py` includes logic to handle cases where the LLM might return a single JSON object instead of a list, and sanitizes keys, improving robustness.
*   **Chunking Overlap:** Implemented with a default of 200 characters (dynamically calculated as 10% of max chunk size), configurable via `main.py`. This enhances LLM context.
*   **Duplicate Prevention:** Implemented at the database level using a unique composite index and `ON CONFLICT DO NOTHING`, ensuring data integrity.
*   **Progress Persistence:** Implemented using a dedicated `progress` table in the database, allowing for robust pause/resume functionality.

## Learnings and Project Insights

*   The core structure for LLM interaction (Langchain, Gemini, structured output) and database persistence (SQLAlchemy, PostgreSQL/SQLite) is well-established.
*   Prompt engineering is critical and well-addressed with dynamic schema injection and detailed instructions.
*   The challenge of precise page number extraction from EPUBs remains a key area for potential future enhancement.
*   The project now has robust mechanisms for handling LLM calls, preventing database duplicates, managing text context through chunking overlap, and persisting processing progress.
