import time
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import json
import requests
import os
import pprint
import urllib.request
import sys
pd.set_option('display.max_columns', 12, 'display.max_rows', 200, 'display.width', 1000, 'display.max_colwidth', 30)


def WA_EV_Pct():
    # FIX: this dataset (3d5d-sdqb) covers every US state/territory, not just WA.
    # Without &state=WA the aggregation below silently mixes in every other state
    # (confirmed live: KS, CA, PR, GU, DC, NC, etc. are all present), and since the
    # 'state' column gets dropped a few lines down, the result was actually
    # nationwide EV%, mislabeled as Washington's.
    URL = 'https://data.wa.gov/resource/3d5d-sdqb.json?' + '&state=' + 'WA' + '&vehicle_primary_use=' + 'Passenger' +'&$limit=' + '1000000'
    data = requests.get(URL).json()
    df = pd.json_normalize(data)
    df['date'] = pd.to_datetime(df['date']).dt.strftime("%Y-%m-%d")

    df = df.sort_values(by='date', ascending=True).reset_index().drop('index', axis=1)
    cols_to_int = ['battery_electric_vehicles_bevs_', 'plug_in_hybrid_electric_vehicles_phevs_', 'electric_vehicle_ev_total', 'non_electric_vehicles', 'total_vehicles',]
    for c in cols_to_int:
        df[c] = df[c].astype(int)
    df = df.drop('percent_electric_vehicles', axis=1)

    # Set up a starting DF to add monthly totals to
    df_to_total = df.drop(['vehicle_primary_use', 'county', 'state'], axis=1)
    df_total = df_to_total.sum(axis=0).to_frame()
    df_total = df_total.drop(['date'], axis=0)  # delete row with date in it, because the data doesn't make sense
    df_total['Total'] = df_total[0]
    df_total = df_total.drop(0, axis=1)

    months = df['date'].unique()
    for m in months:
        df_month = df[df.date == m].reset_index().drop(['index', 'vehicle_primary_use', 'county', 'state'], axis=1)
        df_EV_month = df_month.sum(axis=0).to_frame()
        df_EV_month = df_EV_month.drop('date', axis=0)  # delete row with date in it, because the data doesn't make sense
        m = datetime.strptime(m, "%Y-%m-%d").replace(day=1).strftime("%Y-%m-%d")  # Change the date of the month to the first day to make compatible with other formats
        df_EV_month[m] = df_EV_month[0].astype(int)
        df_EV_month = df_EV_month.drop(0, axis=1)
        df_total = df_total.join(df_EV_month)

    df_total = df_total.drop('Total', axis=1)
    df_total.loc['percent_EVs'] = round(df_total.loc['electric_vehicle_ev_total'] / df_total.loc['total_vehicles'], 4)

    # print(df_total)
    return df_total


def _soda_query_wa_mkt(select, where, group, order, limit=50000):
    """One request to WA's Socrata (SODA) API, doing the aggregation server-side."""
    url = 'https://data.wa.gov/resource/rpr4-cgyd.json'
    params = {
        '$select': select,
        '$where': where,
        '$group': group,
        '$order': order,
        '$limit': str(limit),
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def WA_EV_Mkt_Share():
    # FIX: two real bugs here, both verified live.
    # (1) $limit=10000 against a dataset with ~1.9 million rows, with no
    # $order specified - only ~0.5% of the data was ever being pulled, and
    # which slice you got was arbitrary (whatever order Socrata felt like
    # returning rows in).
    # (2) df.drop([...'base_msrp'...]) referenced a column that does not
    # exist anywhere in this dataset (checked against its actual 33 fields) -
    # this raised a KeyError and crashed the script outright, which is what
    # you just hit.
    #
    # Rather than pulling ~1.9M individual vehicle records just to count them
    # in pandas, this asks Socrata to do the monthly-count-by-make
    # aggregation server-side (same approach used for NY_EVs_v01.py), so only
    # the aggregated result (a few thousand rows at most) comes back.
    where = ("vehicle_primary_use='Passenger' and transaction_type in"
             "('Original Registration','Registration Renewal')")
    rows = _soda_query_wa_mkt(
        select="date_trunc_ym(transaction_date) as reg_month, make, count(*) as cnt",
        where=where,
        group="date_trunc_ym(transaction_date), make",
        order="reg_month",
    )
    df = pd.DataFrame(rows)
    df['cnt'] = df['cnt'].astype(int)
    df['reg_month'] = pd.to_datetime(df['reg_month']).dt.strftime('%Y-%m-%d')

    df_total_make = df.pivot_table(index='make', columns='reg_month', values='cnt', aggfunc='sum', fill_value=0)
    df_total_make = df_total_make.loc[df_total_make.sum(axis=1).sort_values(ascending=False).head(15).index]  # Only include 15 largest brands

    df_total_make_pct = df_total_make.div(df_total_make.sum(axis=0), axis=1).round(4)

    # print(df_total_make_pct)
    return df_total_make_pct

def WA_EVs():
    WA_EV_pct = WA_EV_Pct()
    WA_EV_Mkt_Shr = WA_EV_Mkt_Share()
    # print(WA_EV_pct, '\n', WA_EV_Mkt_Shr)

def main():
    start = datetime.now()
    print("WA Monthly Registrations running as main")
    timestr = datetime.now().strftime("%m-%d-%y")
    filename = "WA Monthly Total EVs " + timestr + ".txt"
    WA_EVs()
    duration = datetime.now() - start
    print('\n' * 2, "Time elapsed to run:", duration, "(H:S:millseconds)")

if __name__ == "__main__":
    main()
