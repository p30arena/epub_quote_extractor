# Product Context: EPUB Quote Extractor

## Why this project exists

This project aims to automate the extraction of specific types of quotes (e.g., "حدیث") from EPUB e-books. Manually extracting and cataloging these sayings, especially with detailed grounding information, is a time-consuming and error-prone process. This tool will streamline the creation of structured databases of religious or scholarly sayings.

## Problems it solves

*   **Manual Extraction Inefficiency:** Eliminates the need for manual reading and transcription of quotes from large EPUB files.
*   **Lack of Grounding:** Ensures that extracted quotes are always accompanied by essential contextual information like page number, speaker, and surrounding context, which is often missing in manual efforts.
*   **Inconsistent Data:** Provides structured outputs, leading to a consistent and queryable database of quotes, unlike disparate manual notes.
*   **Multilingual Challenges:** Addresses the specific need for handling Farsi/Arabic text in certain fields while preserving original quote text.

## How it should work

The system should:
1.  Take an EPUB file as input.
2.  Parse the EPUB to extract text content, ideally maintaining page or section identifiers.
3.  Feed chunks of this text to an LLM (Gemini 2.5 Flash) via Langchain, ensuring 20-30% of the LLM's context window is utilized for optimal grounding.
4.  The LLM, guided by structured output prompts, identifies and extracts quotes along with their associated grounding information (speaker, context, topic, additional info, page number).
5.  Handle multilingual requirements for specific fields as defined in the project brief.
6.  Store the extracted, structured data into a PostgreSQL database.
7.  Allow for database schema evolution through migrations.

## User experience goals

*   **Accuracy:** Users should trust that the extracted quotes are accurate and well-grounded.
*   **Completeness:** The tool should extract all relevant quotes based on the defined criteria.
*   **Ease of Use:** While the core logic is complex, the interface for processing EPUBs and viewing results should be straightforward.
*   **Data Integrity:** The stored data should be clean, consistent, and easily queryable for research or reference.
*   **Reliability:** The system should be robust and handle various EPUB formats gracefully.
