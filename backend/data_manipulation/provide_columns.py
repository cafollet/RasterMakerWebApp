import pandas as pd
import csv
from io import BytesIO, StringIO


def detect_delimiter(file_obj, num_bytes=4096):
    """
    Detect the delimiter used in a CSV file.

    Parameters:
        file_obj: File object or BytesIO object
        num_bytes: Number of bytes to read for detection

    Returns:
        Detected delimiter character
    """
    # Save current position
    pos = file_obj.tell()

    # Read sample for detection
    sample = file_obj.read(num_bytes)
    file_obj.seek(pos)  # Reset to original position

    # Handle bytes vs string
    if isinstance(sample, bytes):
        sample = sample.decode('utf-8', errors='ignore')

    # Use csv.Sniffer to detect delimiter
    sniffer = csv.Sniffer()
    try:
        delimiter = sniffer.sniff(sample).delimiter
        return delimiter
    except:
        # Fallback: count occurrences of common delimiters
        delimiters = [',', '\t', ';', '|', ' ']
        delimiter_counts = {d: sample.count(d) for d in delimiters}
        return max(delimiter_counts, key=delimiter_counts.get)


def provide_columns(csv_file: BytesIO | str):
    """
    Provides all columns in csv file that contain numerical entries
        Parameters:
                csv_file (BytesIO | str): csv filename or file in Bytes
        Returns:
                A list of columns that contain numerical entries
    """

    # Detect delimiter first
    delimiter = detect_delimiter(csv_file)

    encodings = ['utf-8', 'utf-16', 'utf-16-be', 'utf-16-le', 'latin-1', 'iso-8859-1']

    for encoding in encodings:
        try:
            csv_file.seek(0)
            df = pd.read_csv(csv_file, sep=delimiter, encoding=encoding, engine='python')

            # Verify we got reasonable data
            if len(df.columns) > 1 or len(df) > 0:
                df_cols = df.select_dtypes(include="number").columns
                df_cols = list(df_cols.values)
                return df_cols

        except (UnicodeError, UnicodeDecodeError, pd.errors.ParserError):
            continue
        except Exception as e:
            # Log unexpected errors but continue trying
            print(f"Unexpected error with encoding {encoding}: {e}")
            continue

    # If all encodings fail, raise an error
    raise ValueError("Unable to read CSV file with any supported encoding")