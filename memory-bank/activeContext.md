# Active Context: EPUB Quote Extractor

## Current Work Focus

The current focus is on initializing the project's memory bank with comprehensive documentation based on the initial project description. This foundational step ensures that all subsequent development is aligned with the project's goals and constraints.

## Recent Changes

*   **Memory Bank Initialized & Updated:** All core memory bank files have been created and subsequently updated to reflect the current state of the codebase.
*   **Unique Composite Index Implemented:** A unique composite index on `epub_source_identifier` and `quote_text` has been added to the `QuoteDB` model in `schemas.py` to prevent duplicate quote entries.
*   **Database Conflict Handling:** The `save_quotes_to_db` function in `database.py` has been modified to use `ON CONFLICT DO NOTHING` for PostgreSQL inserts, leveraging the new `to_dict()` method on `QuoteDB` for proper data mapping.
*   **Chunking Overlap Added:** The `chunk_text` function in `epub_parser.py` now supports an `overlap_size` parameter (defaulting to 200 characters) to ensure better context for the LLM across chunk boundaries.
*   **Main Script Updated for Overlap:** `main.py` has been updated to accept `--overlap-size` as a command-line argument and pass it to the `chunk_text` function.

## Next Steps

1.  **Environment Setup:** Set up the Python virtual environment and install all necessary dependencies as specified in `requirements.txt`.
2.  **Database Migration Setup:** Initialize Alembic for database migrations, ensuring it integrates with the existing SQLAlchemy models defined in `schemas.py` (this is crucial for applying the new unique constraint).
3.  **EPUB Page Number Refinement:** Continue to investigate and implement more precise page number extraction from EPUBs, or enhance the `epub_source_identifier` if possible, as the current implementation relies on section IDs.
4.  **LLM Prompt Optimization:** Further fine-tune the LLM prompts to improve extraction accuracy, especially for diverse EPUB content and complex quote structures.
5.  **Comprehensive Error Handling:** Enhance error handling across all modules, particularly for edge cases in EPUB parsing (e.g., malformed EPUBs), LLM response failures, and database integrity issues.
6.  **Testing:** Develop a comprehensive suite of unit, integration, and end-to-end tests to ensure reliability and correctness of the entire pipeline.
7.  **CLI Enhancements:** Improve the command-line interface for better user experience, including progress indicators, verbose logging options, and potentially more input options.

## Active Decisions and Considerations

*   **LLM Model Version:** Confirmed strict adherence to "gemini-2.0-flash" or "gemini-2.5-flash-preview-05-20" in `llm_handler.py`.
*   **Multilingual Fields:** Implementation in `prompts.py` and `schemas.py` confirms the handling of Farsi/Arabic for `speaker`, `context`, `topic`, `additional_info`, and no translation for `quote_text`.
*   **`additional_info` JSON Structure:** Confirmed the JSON format for `additional_info` including `surah` and optional `quote_translation` in `schemas.py` and `prompts.py`.
*   **`epub_source_identifier`:** Currently uses chapter/section IDs (`Section ID: {item.get_id()}`) as implemented in `epub_parser.py`. Direct page number extraction is noted as complex and not yet fully implemented. This is a deviation from the "if feasible" part of the original brief, and will be a point of future refinement.
*   **Database Fallback:** The `database.py` module includes a fallback to SQLite if PostgreSQL environment variables are not properly configured, which is a useful development feature.
*   **LLM Response Robustness:** `llm_handler.py` includes logic to handle cases where the LLM might return a single JSON object instead of a list, and sanitizes keys, improving robustness.
*   **Chunking Overlap:** Implemented with a default of 200 characters, configurable via `main.py`. This enhances LLM context.
*   **Duplicate Prevention:** Implemented at the database level using a unique composite index and `ON CONFLICT DO NOTHING`, ensuring data integrity.

## Learnings and Project Insights

*   The core structure for LLM interaction (Langchain, Gemini, structured output) and database persistence (SQLAlchemy, PostgreSQL/SQLite) is well-established.
*   Prompt engineering is critical and well-addressed with dynamic schema injection and detailed instructions.
*   The challenge of precise page number extraction from EPUBs remains a key area for potential future enhancement.
*   The project now has robust mechanisms for handling LLM calls, preventing database duplicates, and managing text context through chunking overlap.
