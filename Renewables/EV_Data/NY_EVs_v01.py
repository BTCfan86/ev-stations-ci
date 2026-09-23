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
pd.set_option('display.max_columns', 10, 'display.max_rows', 100, 'display.width', 1000, 'display.max_colwidth', 25)

# FIX: history now starts here (was pulling back to model year 2000 with no real
# floor on the actual registration event date - see note in NY_Registrations below).
NY_MIN_REG_DATE = '2015-01-01T00:00:00'


def _soda_query(select, where, group, order, limit=50000):
    """One request to NY's Socrata (SODA) API, doing the aggregation server-side."""
    url = 'https://data.ny.gov/resource/w4pv-hbkt.json'
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


def _clean_make_labels(df):
    # Same mis-labeling fixes as before, just applied after the server-side grouping
    # instead of before. Multiple raw codes can now map to the same label (e.g. both
    # 'RVN' and 'RIVA' -> 'RIVIAN'), so re-sum after renaming.
    df['make'] = df['make'].replace({'LU/MO': 'LUCID', 'LUCI': 'LUCID', 'RVN': 'RIVIA', 'RIVA': 'RIVIA', 'RIVIN': 'RIVIA', 'VW': 'VOLKS', 'ME/B': 'ME/BE', 'LEXUI': 'LEXUS', 'MERZ': 'ME/BE'})  # Fixing mis-labelings in source
    df['make'] = df['make'].replace({'ME/BE': 'MERCEDES-BENZ', 'TOYOT': 'TOYOTA', 'PONTI': 'PONTIAC', 'VOLKS': 'VOLKSWAGEN', 'RIVIA': 'RIVIAN', 'CHEVR': 'CHEVROLET', 'SUZUK': 'SUZUKI',
                                     'MITSU': 'MITSUI', 'NISSA': 'NISSAN', 'HYUND': 'HYUNDAI'})  # Conforming to Washington State brand names
    return df.groupby(['reg_month', 'make'], as_index=False)['cnt'].sum()


def _pivot(rows, index_col):
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame()
    df['cnt'] = df['cnt'].astype(int)
    df['reg_month'] = pd.to_datetime(df['reg_month']).dt.strftime('%Y-%m-%d')
    if index_col == 'make':
        df = _clean_make_labels(df)
    return df.pivot_table(index=index_col, columns='reg_month', values='cnt', aggfunc='sum', fill_value=0)


def NY_Registrations():
    # FIX: the original version pulled every individual vehicle registration record
    # from NY's open-data portal - 9+ million rows even before considering a date
    # cutoff (verified live: model_year>=2000 alone already returns 9,022,693 rows;
    # adding a reg_valid_date>=2015 filter on top of that, as requested, actually
    # returns MORE rows - 12,545,280 - because reg_valid_date marks renewal events,
    # not first-registration dates, so a later cutoff catches more renewal cycles,
    # not fewer). Downloading and pandas-aggregating that many raw JSON records was
    # never going to finish reliably, with or without a date filter.
    #
    # Instead, this asks Socrata (the platform this dataset lives on) to do the
    # monthly counting itself via $group + count(*), so only the aggregated result
    # (at most a few thousand rows: one per month per fuel type / make) comes back.
    base_where = ("model_year>=2000 AND record_type='VEH' AND registration_class='PAS' "
                  f"AND reg_valid_date>='{NY_MIN_REG_DATE}'")

    fuel_rows = _soda_query(
        select="date_trunc_ym(reg_valid_date) as reg_month, fuel_type, count(*) as cnt",
        where=base_where,
        group="date_trunc_ym(reg_valid_date), fuel_type",
        order="reg_month",
    )
    make_rows = _soda_query(
        select="date_trunc_ym(reg_valid_date) as reg_month, make, count(*) as cnt",
        where=base_where,
        group="date_trunc_ym(reg_valid_date), make",
        order="reg_month",
    )
    ev_make_rows = _soda_query(
        select="date_trunc_ym(reg_valid_date) as reg_month, make, count(*) as cnt",
        where=base_where + " AND fuel_type='ELECTRIC'",
        group="date_trunc_ym(reg_valid_date), make",
        order="reg_month",
    )

    df_total_fuel = _pivot(fuel_rows, 'fuel_type')
    df_total_make = _pivot(make_rows, 'make')
    df_total_EV_make = _pivot(ev_make_rows, 'make')

    # Only include the 15 largest brands overall (same behavior as the original)
    df_total_make = df_total_make.loc[df_total_make.sum(axis=1).sort_values(ascending=False).head(15).index]
    df_total_EV_make = df_total_EV_make.loc[df_total_EV_make.sum(axis=1).sort_values(ascending=False).head(15).index]

    # Make proportional dataframes (share within the returned rows, per month - same as original)
    df_total_make_pct = df_total_make.div(df_total_make.sum(axis=0), axis=1).round(4)
    df_total_fuel_pct = df_total_fuel.div(df_total_fuel.sum(axis=0), axis=1).round(4)
    df_total_EV_pct = df_total_EV_make.div(df_total_EV_make.sum(axis=0), axis=1).round(4)

    return [df_total_fuel_pct, df_total_make_pct, df_total_EV_pct]

def main():
    start = datetime.now()
    print("NY Monthly Registrations running as main")
    timestr = datetime.now().strftime("%m-%d-%y")
    filename = "NY Monthly Total EVs " + timestr + ".txt"
    NY_Registrations()
    duration = datetime.now() - start
    print('\n' * 2, "Time elapsed to run:", duration, "(H:S:millseconds)")

if __name__ == "__main__":
    main()
