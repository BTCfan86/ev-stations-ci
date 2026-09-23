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
    # FIX: MD_Monthly_EVs() built df_total_EVs but only printed it and never
    # returned it, so ci_runner.py had nothing to write to CSV - this is why
    # the CI run produced no artifact.
    #
    # FIX: $limit=3000 silently truncated the dataset (verified live: 9,086
    # rows for fuel_category=Electric alone, before even adding Plug-in
    # Hybrid), so most months/counties were being dropped depending on
    # whatever order Socrata happened to return rows in. Raised the limit
    # well past the current row count.
    #
    # FIX: only pulling fuel_category='Electric' silently excluded every
    # PHEV. Worse, MD's own data has an inconsistent-casing bug - both
    # 'Plug-in Hybrid' and 'Plug-In Hybrid' appear for the same category
    # (verified live) - so even a case-sensitive PHEV filter would still
    # undercount. Pulling all fuel categories and normalizing case fixes
    # both, and produces BEV / PHEV / EV_Total the same way WA's script does.
    URL = 'https://opendata.maryland.gov/resource/qtcv-n3tc.json?$limit=50000'
    data = requests.get(URL).json()
    df = pd.json_normalize(data)
    df['year_month'] = pd.to_datetime(df['year_month'], format='%Y/%m').dt.strftime("%Y-%m-%d")
    df['count'] = df['count'].astype(int)
    df['fuel_category'] = df['fuel_category'].replace({'Plug-In Hybrid': 'Plug-in Hybrid'})

    monthly = df.groupby(['year_month', 'fuel_category'])['count'].sum().unstack(fill_value=0)
    monthly = monthly.rename(columns={'Electric': 'BEV', 'Plug-in Hybrid': 'PHEV'})
    monthly['EV_Total'] = monthly['BEV'] + monthly['PHEV']

    # Match the row-per-metric / column-per-month layout used by the other
    # state scripts (wa_pct.csv, nc.csv, ny_*.csv)
    monthly = monthly.T
    monthly.index.name = None
    return monthly


def MD_Monthly_Total():
    URL = 'https://opendata.maryland.gov/resource/db8v-9ewn.json?' + '&$limit=' + '1000'
    data = requests.get(URL).json()
    df = pd.json_normalize(data)
    print(df)


def main():
    print("MD Monthly Total EVs running as main")
    timestr = datetime.now().strftime("%m-%d-%y")
    filename = "MD Monthly Total EVs " + timestr + ".txt"
    result = MD_Monthly_EVs()
    print(result)
    # MD_Monthly_Total()

if __name__ == "__main__":
    main()
