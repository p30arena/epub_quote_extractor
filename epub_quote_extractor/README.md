# EPUB Quote Extractor

This project aims to extract notable quotes from EPUB files using a Large Language Model (LLM).

## Features

- Parses EPUB files to extract text content.
- Uses an LLM to identify notable quotes from the extracted text.
- Stores extracted quotes in a database.
- Provides a way to retrieve and view extracted quotes.

## Project Structure

- `main.py`: Main script to orchestrate the extraction process.
- `epub_parser.py`: Functions for parsing EPUB files.
- `llm_handler.py`: Functions for interacting with the LLM.
- `prompts.py`: Contains prompts for the LLM.
- `schemas.py`: Pydantic schemas for data validation.
- `database.py`: Functions for database interactions.
- `requirements.txt`: Project dependencies.
- `.env.example`: Example environment variables file.
- `tests/`: Directory for unit and integration tests.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd epub_quote_extractor
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Copy `.env.example` to a new file named `.env` and fill in the required API keys and configurations (e.g., `OPENAI_API_KEY`).
    ```bash
    cp .env.example .env
    ```

## Usage

(To be defined - e.g., command-line interface instructions)

## Running Tests

(To be defined - e.g., how to run pytest)

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
