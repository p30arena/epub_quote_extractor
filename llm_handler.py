# epub_quote_extractor/llm_handler.py
import os
import json
import time
from dotenv import load_dotenv
import google.generativeai as genai
from typing import List, Dict, Any, Optional

from prompts import get_formatted_quote_extraction_prompt
from schemas import QuoteLLM # For validation if desired, though prompt is main guide

# Load environment variables from .env file
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SDK_CONFIGURED_SUCCESSFULLY = False

if not GEMINI_API_KEY:
    print("CRITICAL: GEMINI_API_KEY not found in environment variables or .env file. LLM calls will fail.")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        SDK_CONFIGURED_SUCCESSFULLY = True
        print("Google Generative AI SDK configured successfully.")
    except Exception as e:
        print(f"Error configuring Google Generative AI SDK: {e}")
        # GEMINI_API_KEY = None # Effectively disables calls if config fails

DEFAULT_MODEL_NAME = "gemini-2.0-flash"
# For safety, especially with automated calls, very restrictive settings.
# Consider making these configurable if more diverse content is expected.
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
]

def analyze_text_with_gemini(
    text_chunk: str,
    model_name: str = DEFAULT_MODEL_NAME,
    retries: int = 3,
    delay: int = 5 # seconds
) -> Optional[List[Dict[str, Any]]]:
    """
    Analyzes a text chunk using Gemini to extract quotes.

    Args:
        text_chunk: The text to analyze.
        model_name: The name of the Gemini model to use.
        retries: Number of times to retry the API call on failure.
        delay: Delay between retries in seconds.

    Returns:
        A list of dictionaries, where each dictionary represents an extracted quote
        and should conform to QuoteLLM schema. Returns None if all retries fail
        or if the API key is not configured. Returns an empty list if no quotes are found.
    """
    ALLOWED_MODELS = ["gemini-2.0-flash", "gemini-2.5-flash-preview-05-20"]
    if model_name not in ALLOWED_MODELS:
        print(f"Error: Invalid model_name '{model_name}'. Only the following models are allowed: {ALLOWED_MODELS}")
        return None

    if not SDK_CONFIGURED_SUCCESSFULLY: # Check if SDK was configured
        print("Error: Gemini API key not configured or SDK initialization failed. Cannot analyze text.")
        return None

    prompt = get_formatted_quote_extraction_prompt(text_chunk)

    generation_config = genai.types.GenerationConfig(
        response_mime_type="application/json", # Gemini API supports this now
        temperature=0.1 # Low temperature for more deterministic, less creative output
    )

    model = genai.GenerativeModel(
        model_name,
        generation_config=generation_config,
        safety_settings=SAFETY_SETTINGS
    )

    current_retry = 0
    last_error = None

    while current_retry < retries:
        response_text_for_error = "N/A (LLM call not made or no text in response)"
        try:
            print(f"LLM call attempt {current_retry + 1}/{retries} for model {model_name} on text chunk (length {len(text_chunk)} chars)...")
            # Setting a timeout for the request
            request_options = genai.types.RequestOptions(timeout=180) # 3 minutes timeout

            response = model.generate_content(prompt, request_options=request_options)

            # Check for empty or blocked response first
            if not response.parts:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    block_reason = response.prompt_feedback.block_reason
                    block_message = f"LLM call blocked due to: {block_reason}."
                    if response.prompt_feedback.safety_ratings:
                         block_message += f" Safety Ratings: {response.prompt_feedback.safety_ratings}"
                    print(f"Warning: {block_message}")
                    # Depending on policy, might retry or just return empty
                    # For now, if blocked, assume no valid quotes can be extracted from this chunk.
                    return []
                else:
                    print("Warning: LLM response contained no parts for an unknown reason. Assuming no quotes.")
                    return []

            try:
                response_text_for_error = response.text.strip() # For error reporting if JSON parsing fails
            except Exception as text_access_e:
                print(f"Error accessing or stripping response.text (Attempt {current_retry + 1}/{retries}): {text_access_e!r}")
                last_error = text_access_e
                current_retry += 1
                if current_retry < retries:
                    time.sleep(delay)
                continue # Go to the next retry attempt

            if not response_text_for_error:
                 print("Warning: Received empty text string from LLM. Assuming no quotes found.")
                 return [] # Treat empty string as no quotes

            # Validate if the response looks like a JSON list before parsing
            # This is a simple check; more robust validation might be needed
            if not (response_text_for_error.startswith('[') and response_text_for_error.endswith(']')):
                # If it doesn't look like a list, but we expect one, this is an issue.
                # Sometimes the model might return a single JSON object if only one quote is found.
                # The prompt strongly asks for a list, but let's be a bit robust.
                if response_text_for_error.startswith('{') and response_text_for_error.endswith('}'):
                    print("Warning: LLM returned a single JSON object instead of a list. Wrapping it in a list.")
                    response_text_for_error = f"[{response_text_for_error}]" # Wrap it
                else:
                    error_message = f"LLM response is not a JSON list or object. Snippet: {response_text_for_error[:300]}"
                    print(f"Warning: {error_message}")
                    # This might be a malformed response, treat as an error and retry
                    last_error = ValueError(error_message)
                    current_retry += 1
                    if current_retry < retries: time.sleep(delay)
                    continue


            # Attempt to parse the JSON
            parsed_json = json.loads(response_text_for_error)

            # Sanitize keys in each dictionary
            sanitized_list = []
            if isinstance(parsed_json, list):
                for item_dict in parsed_json:
                    if isinstance(item_dict, dict):
                        sanitized_dict = {}
                        for key, value in item_dict.items():
                            print(f"DEBUG: Original key: {key!r}")
                            sanitized_key = key.strip()
                            if sanitized_key.startswith('"') and sanitized_key.endswith('"'):
                                sanitized_key = sanitized_key[1:-1]
                            print(f"DEBUG: Sanitized key: {sanitized_key!r}")
                            sanitized_dict[sanitized_key] = value
                        print(f"DEBUG: Sanitized dictionary to be appended: {sanitized_dict}")
                        sanitized_list.append(sanitized_dict)
                    else:
                        # If an item in the list is not a dict, keep it as is.
                        # This might indicate an unexpected response structure.
                        print(f"Warning: Item in parsed JSON list is not a dictionary: {item_dict}")
                        sanitized_list.append(item_dict)
                parsed_json = sanitized_list
            # End of key sanitization

            # Further validation: ensure it's a list and items are dicts (if not empty)
            if not isinstance(parsed_json, list):
                error_message = f"LLM response was valid JSON, but not a list as expected. Type: {type(parsed_json)}"
                print(f"Error: {error_message}") # This is a deviation from expected format.
                last_error = ValueError(error_message) # Treat as error and retry
                current_retry += 1
                if current_retry < retries: time.sleep(delay)
                continue # Retry

            # Optional: Validate with Pydantic if desired for each item
            # validated_quotes = []
            # for item in parsed_json:
            #     try:
            #         validated_quotes.append(QuoteLLM(**item).model_dump())
            #     except Exception as e: # Pydantic validation error
            #         print(f"Warning: LLM output item failed Pydantic validation: {item}. Error: {e}. Skipping this item.")
            # return validated_quotes

            print(f"Successfully received and parsed JSON list from LLM. Found {len(parsed_json)} potential quotes.")
            print(f"DEBUG: Final list being returned: {parsed_json}")
            return parsed_json # Return the raw list of dicts

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response from LLM (Attempt {current_retry + 1}/{retries}): {e}")
            print(f"LLM Raw Response Snippet for JSON error: '{response_text_for_error[:500]}'")
            last_error = e
        except genai.types.BlockedPromptException as e: # More specific error for blocked content
            print(f"LLM call blocked by API (Attempt {current_retry + 1}/{retries}): {e}")
            last_error = e
            # Blocked content usually means no valid quotes, so return empty list and don't retry further for this chunk
            return []
        except Exception as e: # Broad exception for other API errors (network, timeouts, etc.)
            error_type = type(e).__name__
            try:
                print(f"Error during LLM call (Attempt {current_retry + 1}/{retries}) of type {error_type}. Error: {e!r}") # Using !r for repr(e)
            except Exception as log_e:
                print(f"Critical: Failed to log original error. Original error type: {error_type}. Logging error: {log_e!r}")
            last_error = e

        current_retry += 1
        if current_retry < retries:
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)

    print(f"Error: All {retries} retries failed for LLM call. Last error ({type(last_error).__name__}): {last_error}")
    return None


if __name__ == '__main__':
    print("--- LLM Handler Standalone Test ---")
    if not SDK_CONFIGURED_SUCCESSFULLY:
        print("Skipping llm_handler.py test: GEMINI_API_KEY not set or SDK configuration failed.")
    else:
        # Ensure prompts can be loaded for testing
        try:
            from .prompts import get_formatted_quote_extraction_prompt
            print("Successfully imported prompt function.")
        except ImportError:
            print("CRITICAL: Could not import from .prompts. Ensure prompts.py exists and is in the same directory.")
            print("Standalone test cannot proceed without prompt generation.")
            exit(1) # Exit if prompts can't be loaded for a meaningful test.

        test_chunk_no_quote = "The weather was pleasant, with a slight breeze. Birds were singing in the trees. John walked down the path, thinking about his day. He needed to buy some groceries later."
        test_chunk_with_quote = "The old philosopher paused, looked at his students, and then said wisely: 'The only true wisdom is in knowing you know nothing.' He then invited them for tea."
        test_chunk_malformed_potential = "Sometimes people say things like 'this is important' but it's not really a quote." # Model might get confused here.

        print(f"Using test model: {DEFAULT_MODEL_NAME}")

        print(f"\n--- Test 1: Analyzing chunk with no obvious quote ---")
        print(f"Input: '{test_chunk_no_quote}'")
        extracted_quotes_1 = analyze_text_with_gemini(test_chunk_no_quote)
        if extracted_quotes_1 is not None:
            print(f"Result 1 (No Quote Expected): {json.dumps(extracted_quotes_1, indent=2)}")
            if not extracted_quotes_1: # Empty list is success
                print("Test 1 PASSED: Correctly returned empty list for no quotes.")
            else:
                print(f"Test 1 FAILED: Expected empty list, got {len(extracted_quotes_1)} items.")
        else:
            print("Test 1 FAILED (returned None). Check API key, connectivity, or model issues.")

        print(f"\n--- Test 2: Analyzing chunk with a clear quote ---")
        print(f"Input: '{test_chunk_with_quote}'")
        extracted_quotes_2 = analyze_text_with_gemini(test_chunk_with_quote)
        if extracted_quotes_2 is not None:
            print(f"Result 2 (Quote Expected): {json.dumps(extracted_quotes_2, indent=2)}")
            if extracted_quotes_2 and isinstance(extracted_quotes_2, list) and len(extracted_quotes_2) > 0:
                if isinstance(extracted_quotes_2[0], dict) and 'quote_text' in extracted_quotes_2[0]:
                    print("Test 2 PASSED: Correctly extracted quotes in expected list-of-dict format.")
                else:
                    print("Test 2 FAILED: Extracted data format is not as expected for quote content.")
            elif not extracted_quotes_2:
                 print("Test 2 FAILED: No quotes extracted, but expected one.")
            else: # Should be a list
                 print(f"Test 2 FAILED: Expected a list of quotes, got type {type(extracted_quotes_2)}.")
        else:
            print("Test 2 FAILED (returned None). Check API key, connectivity, or model issues.")

        # print(f"\n--- Test 3: Analyzing chunk with potentially confusing text (optional) ---")
        # print(f"Input: '{test_chunk_malformed_potential}'")
        # extracted_quotes_3 = analyze_text_with_gemini(test_chunk_malformed_potential)
        # if extracted_quotes_3 is not None:
        # print(f"Result 3 (Potentially No Quote): {json.dumps(extracted_quotes_3, indent=2)}")
        # else:
        # print("Test 3 failed (returned None).")

        print("\nLLM Handler Test Complete. Review results above.")
        print("Note: Actual LLM calls depend on a valid GEMINI_API_KEY and network access.")


