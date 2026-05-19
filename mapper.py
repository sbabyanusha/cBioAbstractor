import pandas as pd
from rapidfuzz import fuzz

from schemas import SCHEMA_SYNONYMS
from normalizer import normalize_column
from validator import REQUIRED_FIELDS


def map_column(column_name):

    normalized = normalize_column(column_name)

    best_match = None
    highest_score = 0
    matched_synonym = None

    for schema_field, synonyms in SCHEMA_SYNONYMS.items():

        for synonym in synonyms:

            score = fuzz.ratio(normalized, synonym)

            if score > highest_score:
                highest_score = score
                best_match = schema_field
                matched_synonym = synonym

    if highest_score >= 90:
        status = "AUTO_MAPPED"

    elif highest_score >= 70:
        status = "REVIEW_REQUIRED"

    else:
        status = "UNKNOWN"

    return {
        "original_column": column_name,
        "normalized_column": normalized,
        "mapped_to": best_match,
        "matched_synonym": matched_synonym,
        "confidence": highest_score,
        "status": status
    }


def detect_schema(columns):

    normalized_columns = [
        normalize_column(col)
        for col in columns
    ]

    mutation_keywords = [
        "gene",
        "gene_symbol",
        "hugo_symbol",
        "chromosome",
        "start_position",
        "end_position"
    ]

    mutation_score = 0

    for col in normalized_columns:

        if col in mutation_keywords:
            mutation_score += 1

    if mutation_score > 0:
        return "MUTATION"

    return "UNKNOWN"


def validate_mappings(mapped_results, schema_type):

    mapped_fields = [
        item["mapped_to"]
        for item in mapped_results
    ]

    required_fields = REQUIRED_FIELDS.get(schema_type, [])

    errors = []

    for field in required_fields:

        if field not in mapped_fields:

            errors.append(
                f"Missing required field: {field}"
            )

    return errors


def print_preview(results):

    print("\nCOLUMN MAPPINGS:\n")

    for result in results:

        print(
            f"{result['original_column']}"
            f" --> "
            f"{result['mapped_to']}"
            f" ({result['confidence']}%)"
        )


def process_file(csv_file):

    df = pd.read_csv(csv_file)

    columns = list(df.columns)

    schema_type = detect_schema(columns)

    print(f"\nDetected Schema: {schema_type}")

    mapped_results = []

    for col in columns:

        result = map_column(col)

        mapped_results.append(result)

    print_preview(mapped_results)

    errors = validate_mappings(
        mapped_results,
        schema_type
    )

    print("\nVALIDATION:\n")

    if not errors:

        print("Validation Passed ✅")

    else:

        for error in errors:
            print(error)


if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:

        print(
            "Usage:\n"
            "python mapper.py input.csv"
        )

    else:

        process_file(sys.argv[1])