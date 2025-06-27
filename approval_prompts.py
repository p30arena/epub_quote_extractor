# approval_prompts.py

from typing import List
from schemas import QuoteDB
import json

# Prompt to approve or decline a single quote (used for ungrouped quotes)
APPROVE_QUOTE_PROMPT_TEMPLATE = """You are an expert in Islamic studies and literature. Your task is to determine if a given text, which was *not* grouped with any other quotes, should be approved or declined.

**Rule:**
- If the text is a "hadith" or "revayat" (a saying or account of the Prophet Muhammad or other religious figures), or a general significant saying, you must `APPROVED` it.
- If the text is **only** an ayah from the Quran and appears to be isolated (i.e., not part of a larger narrative or explanation within its context), you must `DECLINED` it.
- If the text is a hadith or revayat that *contains* an ayah as part of its narrative, you should `APPROVED` it.
- If the `speaker` field indicates a narrator (e.g., "Narrator", "راوی", "نویسنده", "Author", "کاتب", "Writer", "مترجم", "Translator", "مؤلف", "Compiler", "گردآورنده", "Editor", "ناشر", "Publisher", "ویراستار", "Commentator", "شارح", "مصحح", "Corrector", "محقق", "Researcher", "مقدمه نویس", "Introducer", "پاورقی", "توضیح", "حاشیه", "متن", "کتاب", "فصل", "بخش", "مقدمه", "Introduction", "Footnote", "Explanation", "Marginalia", "Text", "Book", "Chapter", "Section"), you must `DECLINED` it. The LLM should be able to recognize these and similar terms in both English and Farsi, and other languages if contextually appropriate.

**Input:**
- A JSON object representing a quote with the following keys: `quote_text`, `speaker`, `context`, `topic`.

**Output:**
- A single word: `APPROVED` or `DECLINED`.

**Example 1 (Decline - Quranic Ayah):**
- Input: `{{"quote_text": "بسم الله الرحمن الرحيم", "speaker": "...", "context": "...", "topic": "..."}}`
- Output: `DECLINED`

**Example 2 (Approve - Hadith):**
- Input: `{{"quote_text": "The Prophet said, 'The best of you are those who best treat their families.'", "speaker": "The Prophet", "context": "...", "topic": "..."}}`
- Output: `APPROVED`

**Example 3 (Approve - Hadith with Ayah):**
- Input: `{{"quote_text": "Imam Ali said, 'As for the verse, "And hold firmly to the rope of Allah all together," it means...' and then he explained the verse.", "speaker": "Imam Ali", "context": "...", "topic": "..."}}`
- Output: `APPROVED`

**Example 4 (Decline - Narrator in English):**
- Input: `{{"quote_text": "In this chapter, the author discusses the importance of knowledge.", "speaker": "Author", "context": "Introduction to the book", "topic": "Knowledge"}}`
- Output: `DECLINED`

**Example 5 (Decline - Narrator in Farsi):**
- Input: `{{"quote_text": "در این بخش، راوی به توضیح وقایع می‌پردازد.", "speaker": "راوی", "context": "ادامه داستان", "topic": "تاریخ"}}`
- Output: `DECLINED`

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
- **Crucially, quotes in a group must not be more than 2 estimated pages apart.** The estimated page number is available in the `epub_source_identifier` field (e.g., "Section ID: html7928 (Est. Page: 6)"). You must parse this to determine the page distance.

**Input:**
- A JSON list of quote objects. Each quote object will also include `epub_source_identifier`.

**Output:**
- A JSON list of lists, where each inner list contains the IDs of the quotes that should be grouped together.

**Example 1 (Grouping - within page limit):**
- Input: `[
    {{"id": 1, "quote_text": "The man asked, 'What is faith?'", "speaker": "A Wise Man", "context": "A discussion by the river", "topic": "Faith", "epub_source_identifier": "Section ID: html1 (Est. Page: 5)"}},
    {{"id": 2, "quote_text": "The wise man replied, 'It is to believe in the unseen.'", "speaker": "A Wise Man", "context": "A discussion by the river", "topic": "Faith", "epub_source_identifier": "Section ID: html2 (Est. Page: 6)"}},
    {{"id": 3, "quote_text": "A bird flew by.", "speaker": "Narrator", "context": "...", "topic": "...", "epub_source_identifier": "Section ID: html3 (Est. Page: 9)"}}
  ]`
- Output: `[[1, 2]]` (Quotes 1 and 2 are within 2 pages: 6-5=1)

**Example 2 (No Grouping - page limit exceeded):**
- Input: `[
    {{"id": 4, "quote_text": "Patience is a virtue.", "speaker": "Speaker A", "context": "...", "topic": "Patience", "epub_source_identifier": "Section ID: html4 (Est. Page: 10)"}},
    {{"id": 5, "quote_text": "Knowledge is power.", "speaker": "Speaker B", "context": "...", "topic": "Knowledge", "epub_source_identifier": "Section ID: html5 (Est. Page: 13)"}}
  ]`
- Output: `[]` (Quotes 4 and 5 are more than 2 pages apart: 13-10=3)

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
