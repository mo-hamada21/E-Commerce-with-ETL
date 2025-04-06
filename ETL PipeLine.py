import pandas as pd
from sqlalchemy import create_engine, Date, String
import numpy as np
import pyodbc
import logging


# Convert Excel files to JSON files
Paths = ['Area Managers.xlsx', 'Invoices.xlsx', 'Returns.xlsx']
for path in Paths:
    pd.read_excel(path).to_json(path.replace('.xlsx', '.json'), orient='records', indent=4)
    print("All Excel files have been converted to JSON files.")
    
# Ensure that shape of excel file is same as json file
for path in Paths:
    excel_df = pd.read_excel(path)
    json_df = pd.read_json(path.replace('.xlsx', '.json'))
    if excel_df.shape == json_df.shape:
        print(f"Excel file '{path}' has been converted to JSON file '{path.replace('.xlsx', '.json')}'.")
    else:
        print(f"Excel file '{path}' has not been converted to JSON file '{path.replace('.xlsx', '.json')}'.")
  
        

# Create a Database in the SQL Server
CR_Connection = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=server name;"
    "UID=user name;"
    "PWD=Password;"
    "DATABASE=master",
    autocommit=True 
)

Cursor = CR_Connection.cursor()
Database_name = "ECommerce"
DBCreation_query = f"CREATE DATABASE [{Database_name}]"

try:
    Cursor.execute(DBCreation_query)
    print(f'Database {Database_name} Created Successfully')
except Exception as e:
    print(f'Error Creating Database {Database_name}: {e}')

# Close the connection
Cursor.close()


################################# ETL Pipeline #################################

#Extract function to extract Data From Json Files 

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Database Connection Setup
try:
    Connection = create_engine(
        "mssql+pyodbc://user_name:Password@server_name/ECommerce?driver=ODBC+Driver+17+for+SQL+Server",
        fast_executemany=True
    )
    logging.info("Database connection established successfully.")
except Exception as e:
    logging.error(f"Database connection failed: {e}")
    raise

# Extract Function
def Extract():
    try:
        logging.info("Extracting data...")
        AreaManagers = pd.read_json('Area Managers.json')
        Invoices = pd.read_json('Invoices.json')
        Returns = pd.read_json('Returns.json')
        logging.info("Data extraction completed successfully.")
        return AreaManagers, Invoices, Returns
    except Exception as e:
        logging.error(f"Error in extraction: {e}")
        raise

# Transform Function
def Transform(AreaManagers, Invoices, Returns):
    try:
        logging.info("Transforming data...")
        datasets = [AreaManagers, Invoices, Returns]

        for df in datasets:
            # Standardize column names (replace spaces with underscores)
            df.columns = df.columns.str.replace(' ', '_')

            # Convert Unix timestamps to datetime for specific columns
            if 'Order_Date' in df.columns:
                # Convert Unix timestamp to datetime (milliseconds)
                df['Order_Date'] = pd.to_datetime(df['Order_Date'], unit='ms').dt.date
            if 'Ship_Date' in df.columns:
                df['Ship_Date'] = pd.to_datetime(df['Ship_Date'], unit='ms').dt.date

            # Convert text columns to categorical for efficiency
            str_cols = df.select_dtypes(include=[object]).columns
            for col in str_cols:
                df[col] = df[col].astype('category')

            # Log memory usage
            logging.info(f"Transformed dataset memory usage: {df.memory_usage(deep=True).sum() / (1024 ** 2):.2f} MB")
        
        # Drop duplicates
        AreaManagers.drop_duplicates(inplace=True)
        Invoices.drop_duplicates(inplace=True)
        Returns.drop_duplicates(inplace=True)

        logging.info("Data transformation completed successfully.")
        return AreaManagers, Invoices, Returns
    except Exception as e:
        logging.error(f"Error in transformation: {e}")
        raise

# Load Function
def Load(AreaManagers, Invoices, Returns):
    try:
        logging.info("Loading data into SQL Server...")

        # Define column types
        dtype_invoices = {
            'Order_Date': Date(),
            'Ship_Date': Date()
        }

        AreaManagers.to_sql('AreaManagers', Connection, if_exists='replace', index=False)
        Invoices.to_sql('Invoices', Connection, if_exists='replace', index=False, dtype=dtype_invoices)
        Returns.to_sql('Returns', Connection, if_exists='replace', index=False)

        logging.info("Data has been successfully loaded into SQL Server.")
    except Exception as e:
        logging.error(f"Error in loading: {e}")
        raise

# ETL Pipeline Function
def ETL():
    try:
        logging.info("ETL process started.")
        # Extract
        AreaManagers, Invoices, Returns = Extract()
        
        # Transform
        AreaManagers, Invoices, Returns = Transform(AreaManagers, Invoices, Returns)
        
        # Load
        Load(AreaManagers, Invoices, Returns)

        logging.info("ETL process completed successfully.")
    except Exception as e:
        logging.error(f"ETL process failed: {e}")

# Run the ETL pipeline
if __name__ == "__main__":
    ETL()