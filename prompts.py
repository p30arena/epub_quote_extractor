# epub_quote_extractor/prompts.py

# Import the Pydantic schema to help the LLM understand the desired output structure.
# This is for reference in the prompt string and for potential programmatic generation.
from schemas import QuoteLLM
import json

# Constructing the Pydantic schema as a string to include in the prompt
# This helps the LLM understand the exact field names and types.
# Using model_json_schema() and then formatting it for readability in the prompt.

# Generate a more detailed and accurate schema description from the Pydantic model
try:
    schema_fields = QuoteLLM.model_fields
    simplified_schema_dict = {}
    for field_name, field_info in schema_fields.items():
        field_entry = {"description": field_info.description or "No description."}
        if field_info.annotation:
            field_entry["type"] = str(field_info.annotation).replace("typing.Optional[", "").replace("]", "")
        if field_info.default is not None:
             field_entry["default"] = str(field_info.default)
        simplified_schema_dict[field_name] = field_entry
    # Ensure OUTPUT_SCHEMA_DESCRIPTION uses indent=2 as per original analysis
    OUTPUT_SCHEMA_DESCRIPTION = json.dumps(simplified_schema_dict, indent=2)
except Exception as e:
    print(f"Warning: Could not dynamically generate schema description from QuoteLLM: {e}")
    print("Falling back to a manually defined schema description.")
    # Fallback manual schema description, ensure 2-space indent
    OUTPUT_SCHEMA_DESCRIPTION = '''{
      "quote_text": {
        "description": "The exact text of the saying or quote. This text MUST NOT be translated from its original language.",
        "type": "str"
      },
      "speaker": {
        "description": "The person or character who uttered the saying. If unknown, can be null or 'Unknown'. This field MUST be in Farsi.",
        "type": "str",
        "default": "None"
      },
      "context": {
        "description": "The immediate context surrounding the quote, helping to understand its meaning. This should be a brief summary of the situation or surrounding text. This field MUST be in Farsi.",
        "type": "str",
        "default": "None"
      },
      "topic": {
        "description": "The main topic or theme of the quote (e.g., 'Patience', 'Knowledge', 'Charity'). If multiple, pick the most prominent or list them. This field MUST be in Farsi.",
        "type": "str",
        "default": "None"
      },
      "additional_info": {
        "description": "A JSON string containing other relevant information. This string MUST include a 'surah' key with the Surah name in Farsi. If the 'quote_text' is in Arabic, this JSON string MUST also include a 'quote_translation' key with the Farsi translation of the quote. Example for an Arabic quote: \"{\"surah\": \"سورة الفاتحة\", \"quote_translation\": \"به نام خداوند بخشنده مهربان\"}\". Example for a Farsi quote: \"{\"surah\": \"سوره بقره\"}\". This entire field MUST be in Farsi, except for the JSON structure itself.",
        "type": "str",
        "default": "None"
      }
    }'''

# Main system prompt or instruction for the LLM
# Define ESCAPED_OUTPUT_SCHEMA_DESCRIPTION immediately after OUTPUT_SCHEMA_DESCRIPTION is finalized
ESCAPED_OUTPUT_SCHEMA_DESCRIPTION = OUTPUT_SCHEMA_DESCRIPTION.replace("{", "{{").replace("}", "}}")

EXAMPLE_JSON_CONTENT = """[
  {
    "quote_text": "بسم الله الرحمن الرحيم",
    "speaker": "النبي محمد (ص)",
    "context": "سياق المثال",
    "topic": "الموضوع",
    "additional_info": "{\"surah\": \"سورة الفاتحة\", \"quote_translation\": \"به نام خداوند بخشنده مهربان\"}"
  },
  {
    "quote_text": "این یک نقل قول فارسی است",
    "speaker": "سخنران فرضی",
    "context": "زمینه نمونه",
    "topic": "موضوع نمونه",
    "additional_info": "{\"surah\": \"سوره بقره\"}"
  }
]"""
ESCAPED_EXAMPLE_JSON_CONTENT = EXAMPLE_JSON_CONTENT.replace("{", "{{").replace("}", "}}")

# Define QUOTE_EXTRACTION_PROMPT_TEMPLATE using the escaped version
QUOTE_EXTRACTION_PROMPT_TEMPLATE = f"""You are an expert assistant specialized in analyzing texts and extracting **complete, coherent hadith, revayat, sayings, or accounts**. Your primary goal is to identify and extract these full narratives, not fragmented sentences or partial statements.

Your task is to carefully read the provided text chunk from an ebook and identify any such notable hadith, revayat, or significant accounts.

For each entry you identify, you MUST provide the information in a structured JSON format, as a list of JSON objects.
Each object in the list MUST conform to the following JSON schema, detailing the expected fields:
```json
{ESCAPED_OUTPUT_SCHEMA_DESCRIPTION}
```

**Important Contextual Information**: The `text_chunk` provided below may include additional text from the preceding and succeeding sections of the book. This surrounding context is provided to help you identify complete hadith, revayat, or accounts that might span across original chunk boundaries. Use this context to ensure you extract the *entire* coherent narrative, even if it starts or ends outside the immediate focus area of the current chunk. Your primary goal is to identify and extract complete units, leveraging the provided context for continuity.

Key instructions for extraction:
1.  **`quote_text`**: This MUST be the verbatim text of the hadith, revayat, saying, or account. Do NOT translate the `quote_text`. It should represent a complete, self-contained narrative or teaching.
2.  **`speaker`**: Identify who made the statement or is the primary narrator of the account. This field MUST be in Farsi. If explicitly mentioned (e.g., "John said...", "...replied Mary"), use that name. If implied by context, use the name. If it's general narration or the speaker is truly unknown, use "Unknown" or "Narrator" as appropriate (in Farsi, e.g., "ناشناس" یا "راوی"). If the text indicates a source (e.g. "a wise man once said"), use that (in Farsi).
3.  **`context`**: Briefly describe the situation in which the hadith/revayat/account was made or is presented. What was happening, being discussed, or what led to the statement? This field MUST be in Farsi.
4.  **`topic`**: Provide a concise keyword or short phrase for the main theme or subject of the hadith, revayat, or account (e.g., "صبر", "دانش", "صدقه"). This field MUST be in Farsi.
5.  **`additional_info`**: This field MUST be a JSON string. It must include a 'surah' key with the Surah name in Farsi (e.g., "سوره فاتحه"). If the `quote_text` is in Arabic, the JSON string MUST also include a 'quote_translation' key with the Farsi translation of the `quote_text`. For example, if `quote_text` is "بسم الله الرحمن الرحيم", `additional_info` would be "{{{{\"surah\": \"سورة الفاتحة\", \"quote_translation\": \"به نام خداوند بخشنده مهربان\"}}}}". If `quote_text` is already in Farsi, `additional_info` would be "{{{{\"surah\": \"سوره بقره\"}}}}". All text values within the JSON string (like Surah name and translation) MUST be in Farsi.

Output Requirements:
- Your entire response MUST be a single JSON list.
- If multiple distinct hadith, revayat, or accounts are found, return all of them as objects within this list.
- If no hadith, revayat, or accounts are found in the text chunk, you MUST return an empty list: `[]`.
- Do NOT include any explanatory text, greetings, or apologies before or after the JSON list. Your response should start with `[` and end with `]`.

Consider the following when identifying hadith, revayat, or accounts:
- Direct speech indicated by quotation marks (e.g., "...", '...').
- Reported speech (e.g., He said that..., She explained how...).
- Significant statements or aphorisms presented as wisdom or teachings.
- A "hadith" or "revayat" in this context is a complete saying, tradition, or account, often of a moral, religious, or wise nature. It is typically multi-sentence or multi-paragraph.

**What NOT to extract as separate entries**:
- Short, isolated sentences that are clearly part of a larger, ongoing hadith/revayat.
- Common introductory phrases, verses, or concluding remarks (e.g., "و انزلنا الیک الذکر لتبیین للناس", "انا انزلنا") if they are merely components of a larger narrative and not self-contained teachings.
- Fragments of a hadith/revayat that require preceding or succeeding text to be fully understood.

- **Conversational Accounts**: If multiple consecutive statements form a coherent conversation or dialogue, combine them into a single `quote_text` entry. For such combined accounts, the `speaker` should be the primary speaker, or a general term like 'گفتگوکنندگان' (Conversationalists) or 'چندین نفر' (Multiple people) in Farsi. The `context` should summarize the flow of the dialogue.

- **Hadith/Revayat Extraction**: When identifying a "hadith" or "revayat" (حدیث یا روایت), your primary goal is to extract the *entire* coherent narrative, teaching, or account as a single `quote_text`. Do not split a complete hadith or revayat into smaller, fragmented sentences or sub-accounts, even if it contains multiple distinct statements within it. The `quote_text` for a hadith should be the full, continuous text of that hadith.

**Important Note on `quote_text` Length**: The `quote_text` field is designed to hold the complete identified unit, whether it's a single sentence, a conversation, or an entire hadith/revayat. Therefore, `quote_text` can be multi-sentence or multi-paragraph if that is what constitutes the complete, coherent unit you are extracting.

Text chunk to analyze:
-----------------------------------
{{text_chunk}}
-----------------------------------

Example of a valid response with entries:
```json
{ESCAPED_EXAMPLE_JSON_CONTENT}
```

Example of a valid response with no entries:
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
