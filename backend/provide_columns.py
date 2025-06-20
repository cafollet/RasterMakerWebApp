import pandas as pd
import logging
import traceback
from io import BytesIO

# Set up logger for this module
logger = logging.getLogger('processing.columns')


def provide_columns(csv_file: BytesIO | str):
    """
    Extract numeric columns from a CSV file.
    
    Args:
        csv_file: BytesIO stream or file path containing CSV data
        
    Returns:
        List of numeric column names
    """
    logger.info("Extracting numeric columns from CSV")
    
    try:
        # Load CSV data
        if isinstance(csv_file, str):
            logger.debug(f"Loading CSV from file: {csv_file}")
        else:
            logger.debug("Loading CSV from BytesIO stream")
            
        df = pd.read_csv(csv_file)
        logger.info(f"Loaded CSV with shape: {df.shape}")
        logger.debug(f"All columns: {list(df.columns)}")
        
        # Select only numeric columns
        df_numeric = df.select_dtypes(include="number")
        numeric_columns = list(df_numeric.columns.values)
        
        logger.info(f"Found {len(numeric_columns)} numeric columns: {numeric_columns}")
        
        # Log column data types for debugging
        for col in numeric_columns:
            logger.debug(f"Column '{col}': dtype={df[col].dtype}, non-null count={df[col].count()}")
        
        return numeric_columns
        
    except pd.errors.EmptyDataError:
        logger.error("CSV file is empty")
        raise ValueError("The provided CSV file is empty")
        
    except pd.errors.ParserError as e:
        logger.error(f"Failed to parse CSV: {str(e)}")
        raise ValueError(f"Invalid CSV format: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error extracting columns: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    # Set up console logging for standalone execution
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    logger.info("Running provide_columns.py as standalone script")
    
    # Test with sample data
    import io
    
    sample_csv = """lat,lon,value1,value2,text_col
    40.7128,-74.0060,100,200,NYC
    34.0522,-118.2437,150,250,LA
    41.8781,-87.6298,120,180,Chicago
    """
    
    try:
        test_stream = io.StringIO(sample_csv)
        columns = provide_columns(test_stream)
        logger.info(f"Test successful. Columns: {columns}")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
