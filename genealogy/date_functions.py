import re
from dateutil import parser

# Dictionary for translating month names from other languages to English
MONTH_TRANSLATIONS = {
    "januari": "january",
    "februari": "february",
    "mars": "march",
    "april": "april",
    "maj": "may",
    "juni": "june",
    "juli": "july",
    "augusti": "august",
    "september": "september",
    "oktober": "october",
    "november": "november",
    "december": "december",
}

def translate_months(date_str):
    # Replace non-English month names with English equivalents
    for non_english, english in MONTH_TRANSLATIONS.items():
        date_str = re.sub(rf'\b{non_english}\b', english, date_str, flags=re.IGNORECASE)
    return date_str

def extract_year(date_str):
    try:
        # Translate month names to English
        date_str = translate_months(date_str)

        # Use regex to isolate date components
        # This regex is more flexible to capture years in various contexts
        year_match = re.search(r'\b(\d{4})\b', date_str)
        if year_match:
            # Extract the year
            year = year_match.group(1)
            
            # Attempt to parse the string for additional validation
            # (e.g., if there's enough context for a proper date)
            parsed_date = parser.parse(date_str, dayfirst=True, fuzzy=True)
            return int(year)
        
        print(f"No valid year found in string: {date_str}.")
        return None
    except ValueError:
        print(f"Invalid date string: {date_str}")
        return None