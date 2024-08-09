# importando arquivos
import pandas as pd
import streamlit as st
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.core.exceptions import ResourceExistsError
from io import StringIO
import os
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

#------------------------------------------------------------------------------------------------------
st.set_page_config(layout="wide") # Configuração da página larga
#------------------------------------------------------------------------------------------------------

# Uploading data

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

if connection_string is None:
    raise Exception("Environment variable AZURE_STORAGE_CONNECTION_STRING is not set.")

blob_service_client = BlobServiceClient.from_connection_string(connection_string)

container_name = 'expansionbees0001'
local_file_path = r'C:\Users\gabri\OneDrive\Área de Trabalho\DataID'
blob_name = 'blob0001'

container_client = blob_service_client.get_container_client(container_name)

#------------------------------------------------------------------------------------------------------

#### Mandar arquivos na pasta DataID para o Azure Blob Storage
##### Tables from Blob
                
blob_name = 'sales_incentive.csv'
blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
blob_content = blob_client.download_blob().content_as_text()
sales_incentive = StringIO(blob_content)
sales_incentive_df = pd.read_csv(sales_incentive)

#------------------------------------------------------------------------------------------------------

# Manipulating Data
sales_incentive_df['date'] = pd.to_datetime(sales_incentive_df['date'])
current_timestamp = pd.Timestamp.now()
current_day = current_timestamp.day

yesterday_timestamp = current_timestamp - pd.Timedelta(days=1)
yesterday_day = yesterday_timestamp.day

salesman_main = sales_incentive_df[sales_incentive_df['date'] <= yesterday_timestamp]

current_month_start = current_timestamp.replace(day=1)
current_month_df = salesman_main[salesman_main['date'] >= current_month_start]

# Criando visualização MTD
days_passed_current_month = (yesterday_timestamp - current_month_start).days + 1

last_month_start = (current_month_start - pd.DateOffset(months=1)).replace(day=1)
last_month_end = last_month_start + pd.Timedelta(days=days_passed_current_month - 1)
last_month_df = salesman_main[(salesman_main['date'] >= last_month_start) & (salesman_main['date'] <= last_month_end)]

current_month_grouped = current_month_df.groupby('Salesperson_Name')['vendor_account_id'].nunique().reset_index(name='current_month_vendor_count')
last_month_grouped = last_month_df.groupby('Salesperson_Name')['vendor_account_id'].nunique().reset_index(name='last_month_vendor_count')

salesman_main = pd.merge(current_month_grouped, last_month_grouped, on='Salesperson_Name', how='outer').fillna(0)




#------------------------------------------------------------------------------------------------------


st.title('Sales Incentive Data ')

# Display the DataFrame
st.dataframe(salesman_main)





