# epub_parser.py
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

# Placeholder comment about page numbers
# Page number extraction in EPUBs is complex due to reflowable content.
# We will use chapter/section names or item IDs for grounding.

def extract_text_from_epub(epub_path: str) -> list[dict[str, str]]:
    """
    Extracts text content from an EPUB file, segmenting it by chapter or section.

    Args:
        epub_path: The file path to the EPUB file.

    Returns:
        A list of dictionaries, where each dictionary contains:
            'source': The chapter title or section ID.
            'text': The extracted text content from that section.
    """
    book = epub.read_epub(epub_path)
    segments = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        content = item.get_content()
        # It's good practice to specify the parser, e.g., 'html.parser' or 'lxml'
        soup = BeautifulSoup(content, 'html.parser')

        # Extract text
        text = soup.get_text(separator=' ', strip=True) # Use separator for better spacing and strip whitespace

        # Try to get a title from h1, h2, h3, or fall back to item ID
        title_tag = soup.find(['h1', 'h2', 'h3'])
        source_name = title_tag.get_text().strip() if title_tag else f"Section ID: {item.get_id()}"

        if text: # ensure there's actual text to add
             segments.append({'source': source_name, 'text': text})
    return segments

def chunk_text(text_segments: list[dict[str, str]], max_chunk_size: int) -> list[dict[str, str]]:
    """
    Chunks text segments into smaller pieces of a maximum specified size.

    Args:
        text_segments: A list of dictionaries from extract_text_from_epub.
        max_chunk_size: The maximum character length for each chunk.

    Returns:
        A new list of dictionaries, each with 'source' and 'text' (the chunked text).
    """
    chunked_segments = []
    if max_chunk_size <= 0:
        raise ValueError("max_chunk_size must be a positive integer.")

    for segment in text_segments:
        text = segment['text']
        source = segment['source']

        # Simple character-based chunking
        for i in range(0, len(text), max_chunk_size):
            chunked_segments.append({'source': source, 'text': text[i:i+max_chunk_size]})

    return chunked_segments

if __name__ == '__main__':
    # This basic test block is for local testing and might require a sample EPUB file.
    # It's not expected to run in all automated environments unless a test file is provided.
    print("EPUB Parser - Basic Test (requires a sample EPUB file named 'test.epub')")
    try:
        # To run this test, place a sample EPUB file named 'test.epub'
        # in the same directory as this script or provide a direct path.
        # segments = extract_text_from_epub('test.epub')
        # print(f"Extracted {len(segments)} segments.")
        # if segments:
        #     print(f"First segment source: {segments[0]['source'][:100]}") # Print first 100 chars of source
        #     print(f"First segment text preview: {segments[0]['text'][:200]}") # Print first 200 chars of text

        # chunks = chunk_text(segments, 500)
        # print(f"Broken into {len(chunks)} chunks.")
        # if chunks:
        #    print(f"First chunk source: {chunks[0]['source'][:100]}")
        #    print(f"First chunk text preview: {chunks[0]['text'][:200]}")
        print("Dummy main execution. For a full test, provide 'test.epub' and uncomment lines above.")
        print("Example of how to use:")
        print("  segments = extract_text_from_epub('path/to/your/book.epub')")
        print("  chunks = chunk_text(segments, 1000)")


    except FileNotFoundError:
        print("Test EPUB file ('test.epub') not found. Skipping basic test execution.")
    except ebooklib.epub.EpubException as e:
        print(f"Error reading EPUB file: {e}. Ensure 'test.epub' is a valid EPUB.")
    except Exception as e:
        print(f"An error occurred during the test: {e}")
    pass
