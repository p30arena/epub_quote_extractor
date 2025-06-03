# System Patterns: EPUB Quote Extractor

## System Architecture

The system will follow a modular architecture, separating concerns into distinct components:

*   **EPUB Parser Module:** Responsible for reading EPUB files and extracting raw text content, along with any available structural information (e.g., section IDs, potential page numbers).
*   **LLM Handler Module:** Manages interaction with the Large Language Model (LLM), including prompt engineering, context window management, and structured output parsing.
*   **Database Module:** Handles all database operations, including schema definition, data storage, and migration management.
*   **Main Application Logic:** Orchestrates the flow, connecting the parser, LLM handler, and database modules.

## Key Technical Decisions

*   **Langchain for LLM Orchestration:** Confirmed as the framework for managing LLM interactions, prompt templating, and structured output parsing.
*   **Google Gemini 2.5 Flash:** Confirmed as the specific LLM, with strict adherence to "gemini-2.0-flash" or "gemini-2.5-flash-preview-05-20" enforced in `llm_handler.py`.
*   **Structured Outputs (Pydantic):** Pydantic models (`QuoteLLM` in `schemas.py`) are explicitly used to define the expected output schema from the LLM, and this schema is dynamically injected into the LLM prompt in `prompts.py`.
*   **PostgreSQL for Data Storage (SQLAlchemy):** SQLAlchemy ORM is used for database interaction, with PostgreSQL as the primary target. A fallback to SQLite is implemented in `database.py` for development convenience. Unique composite index on `epub_source_identifier` and `quote_text` is implemented in `schemas.py` to prevent duplicates. **A new `ProgressDB` model is added to `schemas.py` for tracking processing state.**
*   **Alembic for Database Migrations:** Planned for managing schema changes over time, integrating with SQLAlchemy models defined in `schemas.py`.

## Design Patterns in Use

*   **Modular Design:** The codebase is structured into distinct modules (`main`, `epub_parser`, `llm_handler`, `database`, `prompts`, `schemas`), encapsulating core functionalities.
*   **Dependency Injection:** Database sessions are managed via a generator (`get_db` in `database.py`), allowing sessions to be injected and properly closed.
*   **Data Transfer Objects (DTOs):** Pydantic models (`QuoteLLM`) serve as DTOs for structured data transfer between the LLM and the main application logic, and for validation.
*   **Configuration Management:** Environment variables (`.env`) are used for sensitive configurations like API keys and database credentials.
*   **Retry Mechanism:** Implemented in `llm_handler.py` for robust LLM API calls.
*   **Chunking with Overlap:** Implemented in `epub_parser.py` to provide better context to the LLM and prevent missed quotes at chunk boundaries.
*   **Upsert/Conflict Handling:** `ON CONFLICT DO NOTHING` strategy implemented in `database.py` for PostgreSQL to gracefully handle attempts to insert duplicate quotes.
*   **Progress Tracking:** Implemented using a dedicated `ProgressDB` table and associated functions (`save_progress`, `load_progress`, `clear_progress`) in `database.py` and integrated into `main.py` for pause/resume functionality.
*   **Conversational Quote Prompting:** The LLM prompt (`prompts.py`) has been refined to explicitly guide the model in identifying and combining consecutive conversational turns into a single quote, enhancing the coherence of extracted dialogues.

## Component Relationships

*   **Main Application <--> EPUB Parser:** The main application will invoke the parser to get text chunks from an EPUB.
*   **Main Application <--> LLM Handler:** The main application will pass text chunks to the LLM handler and receive structured quote data.
*   **Main Application <--> Database Module:** The main application will pass structured quote data to the database module for storage.
*   **LLM Handler <--> LLM API:** The LLM handler will communicate directly with the Google Gemini API.
*   **Database Module <--> PostgreSQL:** The database module will interact with the PostgreSQL instance.

```mermaid
graph TD
    A[EPUB File] --> B[EPUB Parser Module]
    B --> C{Text Chunks + Page Info}
    C --> D[LLM Handler Module]
    D --> E[Google Gemini 2.5 Flash API]
    D --> F{Structured Quote Data}
    F --> G[Database Module]
    G --> H[PostgreSQL Database]
    Main[Main Application Logic] --> B
    Main --> D
    Main --> G
