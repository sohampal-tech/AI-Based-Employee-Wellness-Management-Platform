"""
security.py
Shared security helpers used by both app.py (Streamlit) and backend.py
(FastAPI), so free-text input (journal entries, chat messages, uploaded file
text) is sanitized both at the point of entry and again, defense-in-depth,
at the API layer.
"""
import bleach

MAX_TEXT_LENGTH = 8000  # generous cap for a journal entry or chat message


def sanitize_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """
    Strips any HTML/script markup and truncates to a sane max length.
    Doesn't reject input outright -- people paste all sorts of things into
    a wellness journal -- it just neutralizes anything that could be
    interpreted as markup if ever rendered unescaped, and caps unbounded
    payloads before they reach the NLP pipeline or the database.
    """
    if not text:
        return text
    cleaned = bleach.clean(text, tags=[], attributes={}, strip=True)
    return cleaned[:max_length]
