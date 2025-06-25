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
    df = pd.read_csv(csv_file)
    df_cols = df.select_dtypes(include="number").columns
    df_cols = list(df_cols.values)
    return df_cols