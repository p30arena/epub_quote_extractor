import unittest
import json # For context, though not directly used by the sanitization logic itself

class TestKeySanitization(unittest.TestCase):

    def sanitize_llm_output_keys(self, parsed_json_list: list) -> list:
        """
        Mirrors the key sanitization logic from llm_handler.analyze_text_with_gemini.
        Cleans keys of each dictionary within the list.
        For each key:
        1. Strips leading/trailing whitespace.
        2. If the stripped key starts with a double quote and ends with a double quote,
           removes these surrounding quotes.
        """
        sanitized_list = []
        if isinstance(parsed_json_list, list):
            for item_dict in parsed_json_list:
                if isinstance(item_dict, dict):
                    sanitized_dict = {}
                    for key, value in item_dict.items():
                        sanitized_key = key.strip()
                        if sanitized_key.startswith('"') and sanitized_key.endswith('"'):
                            sanitized_key = sanitized_key[1:-1]
                        sanitized_dict[sanitized_key] = value
                    sanitized_list.append(sanitized_dict)
                else:
                    # If an item in the list is not a dict, keep it as is.
                    sanitized_list.append(item_dict) # Keep non-dict items
        return sanitized_list

    def test_sanitize_keys_in_llm_output(self):
        """
        Tests the key sanitization logic for various cases including:
        - Leading/trailing whitespace
        - Keys that are themselves quoted strings
        - Keys with newlines and mixed whitespace/quotes
        - Keys that are already clean
        - Non-dictionary items in the list (should pass through)
        - Empty list
        - List with empty dictionary
        """
        raw_data = [
            {
                "  key_with_spaces  ": "value1",
                "\"quoted_key\"": "value2",
                "  \"quoted_key_with_spaces\"  ": "value3",
                "\n  \"key_with_newline_and_quotes\"  \t": "value4",
                "already_clean_key": "value5"
            },
            {
                "  another_spaced_key  ": "value6",
                "\"another_quoted_key\"": "value7"
            },
            "this_is_not_a_dict", # Should pass through
            {}, # Empty dictionary
            {"": "empty_key_value"} # Key is an empty string after stripping (if it was spaces)
        ]

        expected_data = [
            {
                "key_with_spaces": "value1",
                "quoted_key": "value2",
                "quoted_key_with_spaces": "value3",
                "key_with_newline_and_quotes": "value4",
                "already_clean_key": "value5"
            },
            {
                "another_spaced_key": "value6",
                "another_quoted_key": "value7"
            },
            "this_is_not_a_dict",
            {},
            {"": "empty_key_value"}
        ]

        # Test with varied inputs
        self.assertEqual(self.sanitize_llm_output_keys(raw_data), expected_data)
        
        # Test with empty list
        self.assertEqual(self.sanitize_llm_output_keys([]), [])

        # Test with keys that become empty after stripping
        edge_case_raw = [{"   ": "value_for_empty_key_after_strip"}]
        edge_case_expected = [{"": "value_for_empty_key_after_strip"}]
        self.assertEqual(self.sanitize_llm_output_keys(edge_case_raw), edge_case_expected)

        # Test with keys that are just quotes (should become empty)
        edge_case_raw_quotes = [{"\"\"": "value_for_empty_key_from_quotes"}]
        edge_case_expected_quotes = [{"": "value_for_empty_key_from_quotes"}]
        self.assertEqual(self.sanitize_llm_output_keys(edge_case_raw_quotes), edge_case_expected_quotes)


if __name__ == '__main__':
    unittest.main()

