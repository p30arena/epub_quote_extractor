# epub_quote_extractor/prompts.py

# Import the Pydantic schema to help the LLM understand the desired output structure.
# This is for reference in the prompt string and for potential programmatic generation.
from schemas import QuoteLLM
import json

# Constructing the Pydantic schema as a string to include in the prompt
# This helps the LLM understand the exact field names and types.
# Using model_json_schema() and then formatting it for readability in the prompt.

# Generate a more detailed and accurate schema description from the Pydantic model
# This is generally more robust than manually writing it.
try:
    # Create a dictionary that's more readable for the prompt than the full JSON schema
    schema_fields = QuoteLLM.model_fields
    simplified_schema_dict = {}
    for field_name, field_info in schema_fields.items():
        field_entry = {"description": field_info.description or "No description."}
        if field_info.annotation:
            field_entry["type"] = str(field_info.annotation).replace("typing.Optional[", "").replace("]", "") # Simplified type
        if field_info.default is not None:
             field_entry["default"] = str(field_info.default)
        simplified_schema_dict[field_name] = field_entry

    OUTPUT_SCHEMA_DESCRIPTION = json.dumps(simplified_schema_dict, indent=2)
except Exception as e:
    print(f"Warning: Could not dynamically generate schema description from QuoteLLM: {e}")
    print("Falling back to a manually defined schema description.")
    # Fallback manual schema description if Pydantic introspection fails for some reason
    OUTPUT_SCHEMA_DESCRIPTION = '''{
      "quote_text": {
        "description": "The exact text of the saying or quote.",
        "type": "str"
      },
      "speaker": {
        "description": "The person or character who uttered the saying. If unknown, can be null or 'Unknown'.",
        "type": "str",
        "default": "None"
      },
      "context": {
        "description": "The immediate context surrounding the quote, helping to understand its meaning. This should be a brief summary of the situation or surrounding text.",
        "type": "str",
        "default": "None"
      },
      "topic": {
        "description": "The main topic or theme of the quote (e.g., 'Patience', 'Knowledge', 'Charity'). If multiple, pick the most prominent or list them.",
        "type": "str",
        "default": "None"
      },
      "additional_info": {
        "description": "Any other relevant information, such as specific circumstances, historical relevance, or if it's a direct response to a question. If none, can be null.",
        "type": "str",
        "default": "None"
      }
    }'''


# Main system prompt or instruction for the LLM
QUOTE_EXTRACTION_PROMPT_TEMPLATE = f"""You are an expert assistant specialized in analyzing texts and extracting significant quotes, sayings, or "hadith" (which in a general sense means a saying or account).
Your task is to carefully read the provided text chunk from an ebook and identify any such notable statements or sayings.

For each quote you identify, you MUST provide the information in a structured JSON format, as a list of JSON objects.
Each object in the list MUST conform to the following JSON schema, detailing the expected fields:
```json
{OUTPUT_SCHEMA_DESCRIPTION}
```

Key instructions for extraction:
1.  **`quote_text`**: This MUST be the verbatim text of the saying or statement. Do not paraphrase.
2.  **`speaker`**: Identify who made the statement. If explicitly mentioned (e.g., "John said...", "...replied Mary"), use that name. If implied by context, use the name. If it's general narration or the speaker is truly unknown, use "Unknown" or "Narrator" as appropriate. If the text indicates a source (e.g. "a wise man once said"), use that.
3.  **`context`**: Briefly describe the situation in which the quote was made. What was happening, being discussed, or what led to the statement?
4.  **`topic`**: Provide a concise keyword or short phrase for the main theme or subject of the quote (e.g., "Wisdom", "Courage", "On Patience", "The nature of good deeds").
5.  **`additional_info`**: Include any other relevant details. For instance, was it a response to a question? Was it directed at a specific person or group? Is there a specific cultural or historical nuance mentioned? If none, this field can be omitted or null.

Output Requirements:
- Your entire response MUST be a single JSON list.
- If multiple distinct quotes are found, return all of them as objects within this list.
- If no quotes, sayings, or hadith are found in the text chunk, you MUST return an empty list: `[]`.
- Do NOT include any explanatory text, greetings, or apologies before or after the JSON list. Your response should start with `[` and end with `]`.

Consider the following when identifying quotes:
- Direct speech indicated by quotation marks (e.g., "...", '...').
- Reported speech (e.g., He said that..., She explained how...).
- Significant statements or aphorisms presented as wisdom or teachings, even if not in direct quotes.
- A "hadith" in this context is a saying, tradition, or account, often of a moral, religious, or wise nature.

Text chunk to analyze:
-----------------------------------
{{text_chunk}}
-----------------------------------

Example of a valid response with one quote:
```json
[
  {{
    "quote_text": "The best way to predict the future is to create it.",
    "speaker": "Peter Drucker",
    "context": "Discussing proactive approaches to business strategy and innovation.",
    "topic": "Future and Creation",
    "additional_info": "Often attributed to Peter Drucker, emphasizing agency."
  }}
]
```

Example of a valid response with no quotes:
```json
[]
```

Now, please process the text chunk provided above and return the JSON list.
"""

# Function to format the prompt with the text chunk
def get_formatted_quote_extraction_prompt(text_chunk: str) -> str:
    """
    Formats the quote extraction prompt with the given text chunk.

    Args:
        text_chunk: The piece of text from which to extract quotes.

    Returns:
        The fully formatted prompt string ready for the LLM.
    """
    return QUOTE_EXTRACTION_PROMPT_TEMPLATE.format(text_chunk=text_chunk)

if __name__ == '__main__':
    print("--- QUOTE EXTRACTION PROMPT TEMPLATE (showing schema) ---")
    # Test the formatter function
    example_prompt = get_formatted_quote_extraction_prompt(text_chunk="The old man smiled and said, 'Patience is a virtue.' He was sitting by the river.")
    print(example_prompt)

    print("\n--- DYNAMICALLY GENERATED OUTPUT SCHEMA DESCRIPTION (for LLM) ---")
    print(OUTPUT_SCHEMA_DESCRIPTION)

    print("\n--- Test: Accessing QuoteLLM schema directly (for verification) ---")
    try:
        # This demonstrates how the schema description is derived programmatically
        schema_from_pydantic_full = QuoteLLM.model_json_schema()
        print("Full Pydantic JSON Schema (QuoteLLM.model_json_schema()):")
        # print(json.dumps(schema_from_pydantic_full, indent=2)) # Can be very verbose
        print(f"Schema version: {schema_from_pydantic_full.get('$schema', 'N/A')}, Title: {schema_from_pydantic_full.get('title', 'N/A')}")
        print("Successfully imported QuoteLLM and accessed its schema.")
    except ImportError:
        print("Could not import QuoteLLM from .schemas. Ensure schemas.py is in the same directory (or package structure is correct) and there are no circular imports.")
    except Exception as e:
        print(f"An error occurred while accessing QuoteLLM schema: {e}")


