# approval_prompts.py

from typing import List
from schemas import QuoteDB
import json

# Prompt to approve or decline a single quote
APPROVE_QUOTE_PROMPT_TEMPLATE = """You are an expert in Islamic studies and literature. Your task is to determine if a given text is a "hadith" or "revayat" (a saying or account of the Prophet Muhammad or other religious figures) and not just a direct quote from the Quran (an "ayah").

**Rule:**
- If the text is **only** an ayah from the Quran, you must decline it.
- If the text is a hadith or revayat that *contains* an ayah as part of its narrative, you should approve it.
- If the text is a saying, hadith, or revayat, you must approve it.

**Input:**
- A JSON object representing a quote with the following keys: `quote_text`, `speaker`, `context`, `topic`.

**Output:**
- A single word: `APPROVED` or `DECLINED`.

**Example 1 (Decline):**
- Input: `{{"quote_text": "بسم الله الرحمن الرحيم", "speaker": "...", "context": "...", "topic": "..."}}`
- Output: `DECLINED`

**Example 2 (Approve):**
- Input: `{{"quote_text": "The Prophet said, 'The best of you are those who best treat their families.'", "speaker": "The Prophet", "context": "...", "topic": "..."}}`
- Output: `APPROVED`

**Example 3 (Approve):**
- Input: `{{"quote_text": "Imam Ali said, 'As for the verse, "And hold firmly to the rope of Allah all together," it means...' and then he explained the verse.", "speaker": "Imam Ali", "context": "...", "topic": "..."}}`
- Output: `APPROVED`

Now, analyze the following quote and provide your decision:

{quote_json}
"""

def get_formatted_approve_quote_prompt(quote: QuoteDB) -> str:
    """Formats the approval prompt with the given quote."""
    quote_dict = {
        "quote_text": quote.quote_text,
        "speaker": quote.speaker,
        "context": quote.context,
        "topic": quote.topic,
    }
    return APPROVE_QUOTE_PROMPT_TEMPLATE.format(quote_json=json.dumps(quote_dict, ensure_ascii=False))


# Prompt to group related quotes
GROUP_QUOTES_PROMPT_TEMPLATE = """You are an expert in text analysis and narrative continuity. Your task is to analyze a list of consecutive quotes and determine if they should be grouped together into a single, coherent narrative.

**Rule:**
- Group quotes if they have the same `speaker`, `topic`, and `context`, and their `quote_text` seems to be part of a continuous story or dialogue.
- Do not group quotes if they are on different topics or from different speakers, or if they don't form a coherent whole.

**Input:**
- A JSON list of quote objects.

**Output:**
- A JSON list of lists, where each inner list contains the IDs of the quotes that should be grouped together.

**Example 1 (Grouping):**
- Input: `[
    {{"id": 1, "quote_text": "The man asked, 'What is faith?'", "speaker": "A Wise Man", "context": "A discussion by the river", "topic": "Faith"}},
    {{"id": 2, "quote_text": "The wise man replied, 'It is to believe in the unseen.'", "speaker": "A Wise Man", "context": "A discussion by the river", "topic": "Faith"}},
    {{"id": 3, "quote_text": "A bird flew by.", "speaker": "Narrator", "context": "...", "topic": "..."}}
  ]`
- Output: `[[1, 2]]`

**Example 2 (No Grouping):**
- Input: `[
    {{"id": 4, "quote_text": "Patience is a virtue.", "speaker": "Speaker A", "context": "...", "topic": "Patience"}},
    {{"id": 5, "quote_text": "Knowledge is power.", "speaker": "Speaker B", "context": "...", "topic": "Knowledge"}}
  ]`
- Output: `[]`

Now, analyze the following list of quotes and provide your grouping decision:

{quotes_json}
"""

def get_formatted_group_quotes_prompt(quotes: List[QuoteDB]) -> str:
    """Formats the grouping prompt with the given list of quotes."""
    quotes_list = [
        {
            "id": q.id,
            "quote_text": q.quote_text,
            "speaker": q.speaker,
            "context": q.context,
            "topic": q.topic,
        }
        for q in quotes
    ]
    return GROUP_QUOTES_PROMPT_TEMPLATE.format(quotes_json=json.dumps(quotes_list, ensure_ascii=False, indent=2))
