import json
import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add project root to sys.path to allow direct imports of project modules
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Now import main function or specific components from main.py
# Assuming main.py has a callable main_function or similar
try:
    from main import main as main_function
except ImportError:
    # This is a fallback or error for the testing environment if main cannot be imported.
    # The test execution might fail if main_function is not available.
    print("Error: Could not import main_function from main.py. Ensure main.py is structured to allow this.")
    print(f"Current sys.path: {sys.path}")
    print(f"Project root determined as: {project_root}")
    main_function = None # Define it as None to avoid runtime errors in test class if import fails

from schemas import QuoteLLM

# Target for patching in main.py
LLM_HANDLER_ANALYZE_TEXT_PATH = "main.analyze_text_with_gemini"
DATABASE_SAVE_QUOTES_PATH = "main.save_quotes_to_db"
MAIN_GET_DB_PATH = "main.get_db"
EPUB_PARSER_EXTRACT_PATH = "main.extract_text_from_epub"
EPUB_PARSER_CHUNK_PATH = "main.chunk_text"
MAIN_CREATE_DB_AND_TABLES_PATH = "main.create_db_and_tables"


class TestMainProcessing(unittest.TestCase):

    @patch(MAIN_CREATE_DB_AND_TABLES_PATH, MagicMock()) # Mock db creation
    @patch(EPUB_PARSER_CHUNK_PATH, MagicMock(return_value=[{'source': 'Test Source', 'text': 'Test Text'}]))
    @patch(EPUB_PARSER_EXTRACT_PATH, MagicMock(return_value=[{'source': 'Test Source', 'text': 'Test Text'}]))
    @patch(DATABASE_SAVE_QUOTES_PATH)
    @patch(LLM_HANDLER_ANALYZE_TEXT_PATH)
    @patch(MAIN_GET_DB_PATH)
    def test_additional_info_processing_and_structure(
        self, mock_get_db, mock_analyze_text, mock_save_quotes,
        mock_epub_extract, mock_epub_chunk, mock_db_create # Order matters for mock args
    ):
        if main_function is None:
            self.skipTest("Skipping test as main_function could not be imported.")

        mock_db_session = MagicMock()
        mock_get_db.return_value = iter([mock_db_session]) # Simulate generator behavior

        mock_llm_response = [
            {
                "quote_text": "هذا نص عربي", # Arabic quote
                "speaker": "المتحدث", # Farsi as per prompt (example)
                "context": "سياق باللغة الفارسية", # Farsi
                "topic": "موضوع باللغة الفارسية", # Farsi
                "additional_info": { # Will be converted to JSON string by main.py
                    "surah": "سورة الفاتحة", # Farsi
                    "quote_translation": "این ترجمه فارسی است" # Farsi translation of Arabic quote
                }
            },
            {
                "quote_text": "این یک نقل قول فارسی است", # Farsi quote
                "speaker": "سخنران فرضی", # Farsi
                "context": "زمینه نمونه", # Farsi
                "topic": "موضوع نمونه", # Farsi
                "additional_info": '{"surah": "سوره بقره"}' # Already a JSON string, Farsi surah
            },
            {
                "quote_text": "نقل قول سوم بدون اطلاعات اضافی", # Farsi quote
                "speaker": "ناشناس", # Farsi
                "context": "بدون زمینه خاص", # Farsi
                "topic": "عمومی", # Farsi
                "additional_info": None # No additional info
            }
        ]
        mock_analyze_text.return_value = mock_llm_response

        # This list will capture the data passed to save_quotes_to_db
        saved_quotes_capture = []
        def mock_save_quotes_impl(db, quotes_list_dicts):
            # main.py calls quote.model_dump() before appending to batch,
            # so quotes_list_dicts here should be a list of dictionaries.
            saved_quotes_capture.extend(quotes_list_dicts)
            return len(quotes_list_dicts) # Simulate returning number of saved items
        mock_save_quotes.side_effect = mock_save_quotes_impl

        # Mock command line arguments for main_function
        with patch('argparse.ArgumentParser') as mock_arg_parser:
            mock_args = MagicMock()
            mock_args.epub_filepath = "dummy.epub" # Needs to be a string
            mock_args.max_chunk_size = 1000
            mock_args.batch_size = 10 # Ensure all mocked quotes are processed in one batch
            mock_arg_parser.return_value.parse_args.return_value = mock_args

            main_function() # Call the main processing function

        # Assertions
        self.assertEqual(mock_analyze_text.call_count, 1, "LLM should be called once for the single chunk.")
        self.assertEqual(mock_save_quotes.call_count, 1, "Save to DB should be called once for the batch.")
        self.assertEqual(len(saved_quotes_capture), 3, "Should have processed all three mocked quotes.")

        # Detailed check for the first quote (Arabic quote_text, additional_info as dict from LLM)
        quote1_saved = saved_quotes_capture[0]
        self.assertEqual(quote1_saved['quote_text'], "هذا نص عربي", "quote_text should remain untranslated.")
        self.assertEqual(quote1_saved['speaker'], "المتحدث") # Assuming speaker is passed as is

        # Verify additional_info was converted to a JSON string and its content
        self.assertIsInstance(quote1_saved['additional_info'], str, "additional_info should be a string in the saved data.")
        expected_ai1_dict = {"surah": "سورة الفاتحة", "quote_translation": "این ترجمه فارسی است"}
        self.assertDictEqual(json.loads(quote1_saved['additional_info']), expected_ai1_dict, "Content of additional_info JSON string is incorrect.")
        self.assertEqual(quote1_saved['epub_source_identifier'], 'Test Source', "Source identifier should be set.")

        # Detailed check for the second quote (Farsi quote_text, additional_info as string from LLM)
        quote2_saved = saved_quotes_capture[1]
        self.assertEqual(quote2_saved['quote_text'], "این یک نقل قول فارسی است")
        self.assertIsInstance(quote2_saved['additional_info'], str, "additional_info should be a string.")
        expected_ai2_dict = {"surah": "سوره بقره"} # Only surah for Farsi quotes
        self.assertDictEqual(json.loads(quote2_saved['additional_info']), expected_ai2_dict)

        # Detailed check for the third quote (additional_info as None)
        quote3_saved = saved_quotes_capture[2]
        self.assertEqual(quote3_saved['quote_text'], "نقل قول سوم بدون اطلاعات اضافی")
        self.assertIsNone(quote3_saved['additional_info'], "additional_info should be None.")

if __name__ == '__main__':
    unittest.main()
