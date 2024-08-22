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
container_client = blob_service_client.get_container_client(container_name)

bees_logo = "bezinho.jpg"
blob_client_logo = blob_service_client.get_blob_client(container=container_name, blob=bees_logo)
blob_content_logo = blob_client_logo.download_blob().readall()


col1, col2 = st.columns([1, 5])

with col1:
    st.image(blob_content_logo, use_column_width=True)

with col2:
    st.title("BEES Sales Leaderboard Report")


#------------------------------------------------------------------------------------------------------

#### Mandar arquivos na pasta DataID para o Azure Blob Storage
##### Tables from Blob
                
blob_name = 'sales_incentive.csv'
blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
blob_content = blob_client.download_blob().content_as_text()
sales_incentive = StringIO(blob_content)
sales_incentive_df = pd.read_csv(sales_incentive)



##### Import Images

bees_logo = "bezinho.jpg"
blob_client_logo = blob_service_client.get_blob_client(container=container_name, blob=bees_logo)
blob_content_logo = blob_client_logo.download_blob().readall()



#------------------------------------------------------------------------------------------------------

sales_incentive_df['date'] = pd.to_datetime(sales_incentive_df['date'])
current_timestamp = sales_incentive_df['date'].max() + pd.Timedelta(days=1)

supervisors = ['All'] + list(sales_incentive_df['Supervisor'].unique())
selected_supervisor = st.selectbox('Select a GTM', supervisors)

if selected_supervisor != 'All':
    filtered_df = sales_incentive_df[sales_incentive_df['Supervisor'] == selected_supervisor]
else:
    filtered_df = sales_incentive_df

positions = ['All'] + list(filtered_df['Salesperson_Position'].unique())
selected_position = st.selectbox('Select a Salesperson Position', positions)

# Apply Salesperson Position filter
if selected_position != 'All':
    filtered_df = filtered_df[filtered_df['Salesperson_Position'] == selected_position]

filtered_df['placement_date'] = pd.to_datetime(filtered_df['placement_date'])
current_timestamp = filtered_df['placement_date'].max() + pd.Timedelta(days=1)

def get_day_with_suffix(day):
    if 11 <= day <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return f"{day}{suffix}"

current_day = current_timestamp.day
yesterday_timestamp = current_timestamp - pd.Timedelta(days=1)

salesman_main = filtered_df[filtered_df['placement_date'] <= yesterday_timestamp]
current_month_start = current_timestamp.replace(day=1)
current_month_df = salesman_main[salesman_main['placement_date'] >= current_month_start]

days_passed_current_month = (yesterday_timestamp - current_month_start).days + 1
last_month_start = (current_month_start - pd.DateOffset(months=1)).replace(day=1)
last_month_end = last_month_start + pd.Timedelta(days=days_passed_current_month - 1)
last_month_df = salesman_main[(salesman_main['placement_date'] >= last_month_start) & (salesman_main['placement_date'] <= last_month_end)]

current_month_grouped = current_month_df.groupby('Salesperson_Name')['vendor_account_id'].nunique().reset_index(name='current_month_vendor_count')
last_month_grouped = last_month_df.groupby('Salesperson_Name')['vendor_account_id'].nunique().reset_index(name='last_month_vendor_count')

salesman_main_grouped = pd.merge(current_month_grouped, last_month_grouped, on='Salesperson_Name', how='outer').fillna(0)
salesman_main_grouped['current_month_vendor_count'] = salesman_main_grouped['current_month_vendor_count'].astype(int)
salesman_main_grouped['last_month_vendor_count'] = salesman_main_grouped['last_month_vendor_count'].astype(int)

current_month_name = current_timestamp.strftime('%B')
current_month_column = f'{get_day_with_suffix(current_day - 1)} of {current_month_name}'
last_month_name = last_month_start.strftime('%B')
last_month_column = f'{last_month_name} MTD'
salesman_main_grouped.columns = ['Salesperson', current_month_column, last_month_column]

salesman_main_grouped['Increment'] = salesman_main_grouped[current_month_column] - salesman_main_grouped[last_month_column]

def classify_performance(diff):
    if diff >= 10:
        return 'Top performer'
    elif 4 < diff < 10:
        return 'Increasing'
    elif 0 <= diff <= 4:
        return 'Stable'
    else:
        return 'Decreasing'

salesman_main_grouped['Performance'] = salesman_main_grouped['Increment'].apply(classify_performance)
salesman_main_grouped = salesman_main_grouped.sort_values(by='Increment', ascending=False)
#------------------------------------------------------------------------------------------------------
# Totals table

last_month_sum = salesman_main_grouped[last_month_column].sum()
current_month_sum = salesman_main_grouped[current_month_column].sum()

# Creating a new DataFrame with the sums
summary_table = pd.DataFrame({
    'Total Current Month': [current_month_sum],
    'Total Last Month': [last_month_sum]
})
#------------------------------------------------------------------------------------------------------
# Pandas Styler
def style_salesman_df(df, font_size='14px'):
    def performance_color(val):
        color = ''
        if val == "Top performer":
            color = '#99FF99'
        elif val == "Increasing":
            color = 'orange'
        elif val == "Stable":
            color = 'lightyellow'
        elif val == "Decreasing":
            color = '#FF9999'
        return f'background-color: {color}'

    # Criar o Styler
    styler = df.style.format(na_rep="-", precision=0)\
        .set_table_styles([
            # Estilo do cabeçalho
            {'selector': 'thead th',
             'props': [('background-color', '#1a2634'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center')]},
            # Estilo da fonte e tamanho para toda a tabela
            {'selector': 'table, th, td',
             'props': [('font-size', font_size), ('text-align', 'center')]}, 
            # Removendo linhas de grade
            {'selector': 'table',
             'props': [('border-collapse', 'collapse'), ('border-spacing', '0'), ('border', '0')]}
        ])\
        .applymap(performance_color, subset=['Performance'])
    
    # Ocultar o índice
    styler = styler.hide(axis='index')

    return styler


def style_salesman_df_2(df, font_size='14px'):

    # Criar o Styler
    styler = df.style.format(na_rep="-", precision=0)\
        .set_table_styles([
            # Estilo do cabeçalho
            {'selector': 'thead th',
             'props': [('background-color', '#1a2634'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center')]},
            # Estilo da fonte e tamanho para toda a tabela
            {'selector': 'table, th, td',
             'props': [('font-size', font_size), ('text-align', 'center')]}, 
            # Removendo linhas de grade
            {'selector': 'table',
             'props': [('border-collapse', 'collapse'), ('border-spacing', '0'), ('border', '0')]}
        ])
    # Ocultar o índice
    styler = styler.hide(axis='index')

    return styler
#------------------------------------------------------------------------------------------------------
# Styled dataframes
salesman_main_df = style_salesman_df(salesman_main_grouped)
salesman_html = salesman_main_df.to_html()

centered_html = f"""
<div style="display: flex; justify-content: center; align-items: center; height: 100%;">
    {salesman_html}
</div>
"""
#-----------------------------------------------------------------------------------------------------
salesman_total = style_salesman_df_2(summary_table)
salesman_html_total = salesman_total.to_html()

centered_html_total = f"""
<div style="display: flex; justify-content: center; align-items: center; height: 100%;">
    {salesman_html_total}
</div>
"""
#------------------------------------------------------------------------------------------------------

colA_1 = st.columns(1)
colB_1 = st.columns(1)
colB = st.columns(1)


with colA_1[0]:
    st.markdown(f"<i style='font-size: smaller;'>Update up to {current_day - 1}th of {current_month_name}</i>", unsafe_allow_html=True)

with colB_1[0]:
    st.markdown(centered_html_total, unsafe_allow_html=True)

with colB[0]:
    st.markdown(centered_html, unsafe_allow_html=True)





