import re
import json

def scrub_pii(text: str) -> str:
    """
    Advanced PII Detection for FinTech 2026.
    Scans for IBAN, Credit Cards, and Personal Data.
    """
    patterns = {
        "IBAN": r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}",
        "CARD": r"\b(?:\d[ -]*?){13,16}\b",
        "EMAIL": r"[\w\.-]+@[\w\.-]+\.[a-z]{2,}"
    }
    
    for label, pattern in patterns.items():
        text = re.sub(pattern, f"[{label}_REDACTED]", text)
    return text
