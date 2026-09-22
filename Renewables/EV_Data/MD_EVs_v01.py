import time
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import json
import requests
import os
import pprint
import sys
pd.set_option('display.max_columns', 13, 'display.max_rows', 100, 'display.width', 1000, 'display.max_colwidth', 18)


def MD_Monthly_EVs():
    URL = 'https://opendata.maryland.gov/resource/qtcv-n3tc.json?' + 'fuel_category=' + 'Electric' + '&$limit=' + '3000'
    data = requests.get(URL).json()
    df = pd.json_normalize(data)
    df['year_month'] = pd.to_datetime(df['year_month']).dt.strftime("%Y-%m-%d")  # Change dates to better format
    df['count'] = df['count'].astype(int)
    months = df['year_month'].unique()  # Returns unique months
    month_EV_totals = []
    # print(df)

    for m in months:
        df_month = df[df.year_month == m].reset_index().drop('index', axis=1)
        df_month.loc['Total'] = pd.Series(df_month['count'].sum(), index=['count'])
        month_EV_totals.append(df_month['count'].loc['Total'])

    df_total_EVs = pd.DataFrame()
    df_total_EVs['Date'] = months
    df_total_EVs['EVs'] = month_EV_totals
    print(df_total_EVs)

def MD_Monthly_Total():
    URL = 'https://opendata.maryland.gov/resource/db8v-9ewn.json?' + '&$limit=' + '1000'
    data = requests.get(URL).json()
    df = pd.json_normalize(data)
    print(df)


def main():
    print("MD Monthly Total EVs running as main")
    timestr = datetime.now().strftime("%m-%d-%y")
    filename = "MD Monthly Total EVs " + timestr + ".txt"
    MD_Monthly_EVs()
    # MD_Monthly_Total()

if __name__ == "__main__":
    main()
