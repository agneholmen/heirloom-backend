import re
from dateutil import parser

# Dictionary for translating month names from other languages to English
MONTH_TRANSLATIONS = {
    "january": ["januari", "jan"],
    "february": ["februari", "feb"],
    "march": ["mars", "mar"],
    "april": ["april", "apr"],
    "may": ["maj"],
    "june": ["juni", "jun"],
    "july": ["juli", "jul"],
    "august": ["augusti", "aug"],
    "september": ["september", "sep", "sept"],
    "october": ["oktober", "okt"],
    "november": ["november", "nov"],
    "december": ["december", "dec"]
}

def translate_months(date_str):
    # Replace non-English month names with English equivalents
    for english, non_english in MONTH_TRANSLATIONS.items():
        for ne in non_english:
            date_str = re.sub(rf'\b{ne}\b', english, date_str, flags=re.IGNORECASE)
    return date_str

def extract_year(date_str):
    try:
        # Translate month names to English
        date_str = translate_months(date_str)

        if date_str.isdigit():
            if len(date_str) == 8 or len(date_str) == 6:
                year = date_str[:4]
                return int(year)
            
        year_match = re.search(r'(\d\d\d\d)-\d\d-\d\d', date_str)
        if year_match:
            year = year_match.group(1)

            return int(year)
        
        year_match = re.search(r'(\d\d\d\d)-\d\d', date_str)
        if year_match:
            year = year_match.group(1)

            return int(year)

        # Use regex to isolate date components
        # This regex is more flexible to capture years in various contexts
        year_match = re.search(r'\b(\d{4})\b', date_str)
        if year_match:
            # Extract the year
            year = year_match.group(1)
            
            # Attempt to parse the string for additional validation
            # (e.g., if there's enough context for a proper date)
            # Disable for now. It's a good check, but still it doesn't allow for mistakes, for example 31 september
            #parsed_date = parser.parse(date_str, dayfirst=True, fuzzy=True)
            return int(year)
        
        print(f"No valid year found in string: {date_str}.")
        return None
    except ValueError:
        print(f"Invalid date string: {date_str}")
        return None