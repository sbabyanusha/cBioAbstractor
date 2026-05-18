import pandas as pd


# -----------------------------------------------------------------------------
# Canonical cBioPortal column mappings
# -----------------------------------------------------------------------------
COLUMN_MAP = {
    # Patient identifiers
    "patient": "PATIENT_ID",
    "patient_id": "PATIENT_ID",
    "patient id": "PATIENT_ID",
    "sample_patient": "PATIENT_ID",

    # Sample identifiers
    "sample": "SAMPLE_ID",
    "sample_id": "SAMPLE_ID",
    "sample id": "SAMPLE_ID",

    # Sex / gender
    "gender": "SEX",
    "sex": "SEX",

    # Age
    "age": "AGE",
    "age_at_diagnosis": "AGE",

    # Cancer type
    "cancer_type": "CANCER_TYPE",
    "tumor_type": "CANCER_TYPE",

    # Survival
    "os_status": "OS_STATUS",
    "os_months": "OS_MONTHS",
}


# -----------------------------------------------------------------------------
# Normalize text helper
# -----------------------------------------------------------------------------
def normalize_text(text):
    """
    Normalize text for matching:
    - lowercase
    - strip spaces
    - replace underscores
    """
    return (
        str(text)
        .strip()
        .lower()
        .replace("_", " ")
    )


# -----------------------------------------------------------------------------
# Normalize column names
# -----------------------------------------------------------------------------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename messy columns into canonical cBioPortal columns.
    """

    new_columns = {}

    for col in df.columns:
        normalized = normalize_text(col)

        if normalized in COLUMN_MAP:
            new_columns[col] = COLUMN_MAP[normalized]
        else:
            # fallback → uppercase cleaned version
            new_columns[col] = (
                normalized
                .replace(" ", "_")
                .upper()
            )

    df = df.rename(columns=new_columns)

    return df


# -----------------------------------------------------------------------------
# Normalize values inside columns
# -----------------------------------------------------------------------------
def normalize_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize categorical values.
    """

    # Normalize SEX column
    if "SEX" in df.columns:

        sex_map = {
            "m": "MALE",
            "male": "MALE",
            "f": "FEMALE",
            "female": "FEMALE",
        }

        df["SEX"] = (
            df["SEX"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map(lambda x: sex_map.get(x, x.upper()))
        )

    # Normalize OS_STATUS
    if "OS_STATUS" in df.columns:

        os_map = {
            "0": "LIVING",
            "1": "DECEASED",
            "living": "LIVING",
            "deceased": "DECEASED",
        }

        df["OS_STATUS"] = (
            df["OS_STATUS"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map(lambda x: os_map.get(x, x.upper()))
        )

    return df


# -----------------------------------------------------------------------------
# Main normalization pipeline
# -----------------------------------------------------------------------------
def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full normalization pipeline.
    """

    df = normalize_columns(df)

    df = normalize_values(df)

    return df


# -----------------------------------------------------------------------------
# Example local testing
# -----------------------------------------------------------------------------
if __name__ == "__main__":

    # Example messy dataset
    data = {
        "patient": ["P1", "P2"],
        "gender": ["male", "f"],
        "age": [45, 60],
    }

    df = pd.DataFrame(data)

    print("ORIGINAL DATAFRAME")
    print(df)

    print("\nNORMALIZED DATAFRAME")

    normalized_df = normalize_dataframe(df)

    print(normalized_df)