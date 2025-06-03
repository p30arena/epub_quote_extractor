# Project Brief: EPUB Quote Extractor

## Core Requirements and Goals

The primary goal of this project is to develop a Python application that can extract specific types of quotes (sayings, e.g., "حدیث") from EPUB e-books. The extraction process must involve analysis using a Large Language Model (LLM) to ensure grounding and proper citation.

## Key Features:

1.  **EPUB Parsing:** Ability to read and process EPUB files.
2.  **LLM Integration:** Utilize Langchain and Google Gemini 2.5 Flash for text analysis and quote extraction.
3.  **Structured Outputs:** LLM outputs must be structured to ensure consistency and ease of processing.
4.  **Contextual Grounding:** The LLM should be fed sufficient context (20-30% of its context window filled with pages) to accurately extract quotes.
5.  **Quote Grounding and Citations:** Each extracted quote must be grounded with:
    *   Page number
    *   Speaker (person who said the saying)
    *   Context about the saying
    *   Topic
    *   Additional information
6.  **Multilingual Support (Specific Fields):**
    *   `speaker`: Must be in Farsi or Arabic.
    *   `context`: Must be in Farsi.
    *   `topic`: Must be in Farsi.
    *   `additional_info`: Must be in Farsi.
    *   `quote_text`: Stored as is (no translation). If in Arabic, its translation must be stored in `additional_info` under the key "quote_translation".
7.  **Data Storage:** Extracted quotes must be stored in a PostgreSQL database.
8.  **Database Migrations:** The project must support database migrations.
9.  **LLM Constraints:** Only "gemini-2.0-flash" or "gemini-2.5-flash-preview-05-20" are allowed.
10. **`epub_source_identifier`:** This field must contain the page number (if feasible). Example: "Section ID: html7927".
11. **`additional_info` Format:** Must be in JSON format and include the related Surah (سوره) if the quotation/hadith is about it.
