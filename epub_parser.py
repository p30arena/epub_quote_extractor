# epub_parser.py
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

# Constant for estimated characters per page for heuristic page numbering
# This is an approximation based on standard book sizes and word counts.
# 2000 characters is roughly 300-400 words, which is a common page density.
CHARS_PER_ESTIMATED_PAGE = 2000

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

def chunk_text(text_segments: list[dict[str, str]], max_chunk_size: int, overlap_size: int = 200) -> list[dict[str, str]]:
    """
    Chunks text segments into smaller pieces of a maximum specified size, with overlap.
    Each chunk will also have an 'estimated_page' number based on a global character count.

    Args:
        text_segments: A list of dictionaries from extract_text_from_epub.
        max_chunk_size: The maximum character length for each chunk.
        overlap_size: The number of characters to overlap between consecutive chunks.

    Returns:
        A new list of dictionaries, each with 'source', 'text' (the chunked text),
        and 'estimated_page' (the estimated page number for the start of the chunk).
    """
    chunked_segments = []
    current_total_chars = 0  # Track total characters processed across all segments for global page estimation

    if max_chunk_size <= 0:
        raise ValueError("max_chunk_size must be a positive integer.")
    if overlap_size < 0:
        raise ValueError("overlap_size cannot be negative.")
    if overlap_size >= max_chunk_size:
        print(f"Warning: overlap_size ({overlap_size}) is greater than or equal to max_chunk_size ({max_chunk_size}). Setting overlap_size to 0 to avoid infinite loops or empty chunks.")
        overlap_size = 0  # Prevent infinite loop or empty chunks if overlap is too large

    for segment in text_segments:
        text = segment['text']
        source = segment['source']
        text_len = len(text)
        
        i = 0
        while i < text_len:
            end_index = min(i + max_chunk_size, text_len)
            chunk_content = text[i:end_index]

            # Calculate estimated page number for this chunk
            # The page number is based on the start of the chunk relative to the total characters processed so far
            estimated_page_number = (current_total_chars // CHARS_PER_ESTIMATED_PAGE) + 1

            chunked_segments.append({
                'source': source,
                'text': chunk_content,
                'estimated_page': estimated_page_number  # Add estimated page number
            })
            
            # Update total characters processed by the actual length of the chunk added
            current_total_chars += len(chunk_content)

            # Move the starting index for the next chunk
            if end_index == text_len:
                break
            
            i += (max_chunk_size - overlap_size)
            # Ensure i doesn't go past the end of the text if overlap is large or remaining text is small
            if i < 0:
                i = 0
            
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
