# Tech Context: EPUB Quote Extractor

## Technologies Used

*   **Programming Language:** Python
*   **LLM Framework:** Langchain (used for conceptual orchestration, though direct `google.generativeai` SDK is used for core LLM calls)
*   **Large Language Model:** Google Gemini 2.5 Flash (specifically "gemini-2.0-flash" or "gemini-2.5-flash-preview-05-20", enforced in `llm_handler.py`)
*   **Database:** PostgreSQL (primary target, with SQLite fallback implemented in `database.py`)
*   **Database Migrations:** Alembic (planned for managing schema changes)
*   **EPUB Parsing:** `ebooklib` and `BeautifulSoup` (used in `epub_parser.py`)
*   **Data Validation/Serialization:** Pydantic (used in `schemas.py` for `QuoteLLM` and `main.py` for validation)
*   **Environment Variables:** `python-dotenv` (used in `database.py` and `llm_handler.py`)
*   **Text Chunking:** Custom implementation in `epub_parser.py` with configurable overlap. The default overlap size is dynamically set to 10% of the maximum chunk size in `main.py`.

## Development Setup

*   **Python Environment:** Recommended to use `venv` or `conda` for dependency management.
*   **Dependencies:** Managed via `requirements.txt`.
*   **Environment Variables:** Sensitive information like API keys and database connection strings will be managed via `.env` files.
*   **Database Setup:** Requires a running PostgreSQL instance. Docker can be used for local development setup.

## Technical Constraints

*   **LLM Context Window:** The LLM must be fed 20-30% of its context window with relevant pages to ensure proper grounding. This is managed by `chunk_text` in `epub_parser.py` with `max_chunk_size` and `overlap_size`.
*   **Specific LLM Versions:** Only "gemini-2.0-flash" or "gemini-2.5-flash-preview-05-20" are permitted, and this is strictly enforced in `llm_handler.py`.
*   **Multilingual Output:** Specific fields (`speaker`, `context`, `topic`, `additional_info`) must adhere to Farsi/Arabic language requirements. `quote_text` must remain untranslated. This is handled by prompt engineering in `prompts.py`.
*   **JSON Format for `additional_info`:** This field must be a valid JSON string, allowing for flexible storage of extra metadata, including the "quote_translation" and "Surah" information. This is enforced by `schemas.py` and handled in `main.py` and `prompts.py`.
*   **`epub_source_identifier` Content:** Currently, `epub_parser.py` uses chapter/section IDs (e.g., "Section ID: html7927") for `epub_source_identifier` due to the complexity of precise page number extraction from reflowable EPUB content. Further investigation is needed if explicit page numbers are a strict requirement.
*   **Duplicate Quote Prevention:** Implemented via a unique composite index on `epub_source_identifier` and `quote_text` in `schemas.py`, and `ON CONFLICT DO NOTHING` in `database.py` for PostgreSQL.

## Tool Usage Patterns

*   **Database Migrations:** `alembic upgrade head` (or similar command) will be used to apply database migrations. New migrations will be generated as schema changes occur.
*   **Testing:** Unit and integration tests will be written to ensure the correctness of parsing, LLM interaction, and database operations.
*   **Dependency Management:** `pip install -r requirements.txt` for installing dependencies.
