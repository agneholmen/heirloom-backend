import date_functions as df

def main():
    # Test cases
    examples = [
        "22 januari 1914",
        "november 22 1785",
        "ca 22 november 1785",
        "22 nov 1785",
        "1785",
        "35 december 1785",
        "random text 1785",
        "nov 22 1675",
        "runt 1567",
        "NOV 1678",
        "jun 1676",
        "noviembre 1656",
        "dec 1700"
    ]

    for example in examples:
        print(f"Input: {example} -> Year: {df.extract_year(example)}")

if __name__ == "__main__":
    main()