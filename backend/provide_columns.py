import pandas as pd
from io import BytesIO
def provide_columns(csv_file: BytesIO | str):
    """
    Provides all columns in csv file that contain numerical entries
        Parameters:
                csv_file (BytesIO | str): csv filename or file in Bytes
        Returns:
                A list of columns that contain numerical entries
    """

    try:
        df = pd.read_csv(csv_file, sep=r"[\t,]", engine='python')
    except UnicodeError as _:
        csv_file.seek(0)
        try:
            df = pd.read_csv(csv_file, encoding='utf-16', sep=r"[\t,]", engine='python')
        except Exception as _:
            csv_file.seek(0)
            try:
                df = pd.read_csv(csv_file, encoding='utf_16_be', sep=r"[\t,]", engine='python')
            except Exception as _:
                csv_file.seek(0)
                df = pd.read_csv(csv_file, encoding='utf_16_le', sep=r"[\t,]", engine='python')
    df_cols = df.select_dtypes(include="number").columns
    df_cols = list(df_cols.values)
    return df_cols