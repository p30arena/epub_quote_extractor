# Active Context: EPUB Quote Extractor

## Current Work Focus

The current focus is on initializing the project's memory bank with comprehensive documentation based on the initial project description. This foundational step ensures that all subsequent development is aligned with the project's goals and constraints.

## Recent Changes

*   **Memory Bank Initialized:** All core memory bank files (`projectbrief.md`, `productContext.md`, `systemPatterns.md`, `techContext.md`, `activeContext.md`, `progress.md`) have been created and populated based on the initial project description.
*   **Codebase Review Completed:** All existing Python files (`main.py`, `prompts.py`, `database.py`, `epub_parser.py`, `llm_handler.py`, `schemas.py`) have been reviewed to understand the current implementation status.

## Next Steps

1.  **Environment Setup:** Set up the Python virtual environment and install all necessary dependencies as specified in `requirements.txt`.
2.  **Database Migration Setup:** Initialize Alembic for database migrations, ensuring it integrates with the existing SQLAlchemy models defined in `schemas.py`.
3.  **Refine EPUB Parsing:** While basic parsing is in place, investigate further how to extract more precise page numbers or enhance `epub_source_identifier` if possible, beyond just section IDs.
4.  **LLM Prompt Refinement:** Continuously refine the LLM prompts in `prompts.py` to improve quote extraction accuracy and adherence to structured output and multilingual requirements.
5.  **Error Handling Enhancements:** Review and enhance error handling across all modules, especially for edge cases in EPUB parsing, LLM responses, and database operations.
6.  **Testing:** Develop comprehensive unit, integration, and end-to-end tests for all components.
7.  **CLI/Interface:** Develop a user-friendly command-line interface for running the extraction process.

## Active Decisions and Considerations

*   **LLM Model Version:** Confirmed strict adherence to "gemini-2.0-flash" or "gemini-2.5-flash-preview-05-20" in `llm_handler.py`.
*   **Multilingual Fields:** Implementation in `prompts.py` and `schemas.py` confirms the handling of Farsi/Arabic for `speaker`, `context`, `topic`, `additional_info`, and no translation for `quote_text`.
*   **`additional_info` JSON Structure:** Confirmed the JSON format for `additional_info` including `surah` and optional `quote_translation` in `schemas.py` and `prompts.py`.
*   **`epub_source_identifier`:** Currently uses chapter/section IDs (`Section ID: {item.get_id()}`) as implemented in `epub_parser.py`. Direct page number extraction is noted as complex and not yet fully implemented. This is a deviation from the "if feasible" part of the original brief, and will be a point of future refinement.
*   **Database Fallback:** The `database.py` module includes a fallback to SQLite if PostgreSQL environment variables are not properly configured, which is a useful development feature.
*   **LLM Response Robustness:** `llm_handler.py` includes logic to handle cases where the LLM might return a single JSON object instead of a list, and sanitizes keys, improving robustness.

## Learnings and Project Insights

*   The core structure for LLM interaction (Langchain, Gemini, structured output) and database persistence (SQLAlchemy, PostgreSQL/SQLite) is already laid out in the existing files.
*   Prompt engineering is critical and well-addressed in `prompts.py` with dynamic schema injection and detailed instructions.
*   The challenge of precise page number extraction from EPUBs is acknowledged and partially addressed by using section IDs. This will require further investigation if true page numbers are a hard requirement.
*   The project has a good foundation for error handling and robustness in LLM calls and database operations.
