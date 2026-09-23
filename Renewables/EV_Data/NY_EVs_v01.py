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

# FIX: switched data sources entirely. NY's DMV vehicle-registration dataset
# (w4pv-hbkt) only retains registrations that are still active or expired
# within the last 2 years - old records are purged, not just filtered out -
# so no query against it can ever reconstruct history back to 2015 (verified
# live: even with a 2015 date floor, virtually every row returned dated from
# mid-2024 onward, because that's the true edge of what the table still holds).
#
# NYSERDA's Drive Clean Rebate dataset (thd2-fu8y) tracks every NY EV rebate
# application since the program started in March 2017, as a real historical
# log (not a rolling snapshot), including manufacturer (make), EV type
# (BEV/PHEV), and submission date. This trades "vehicles currently on the
# road" for "vehicles purchased/leased with a rebate" - it won't include EVs
# bought without a rebate (used EVs, or new EVs during any stretch a given
# make/model didn't qualify) - but it's the only NY source that actually has
# monthly history going back further than ~2 years.
NY_REBATE_MIN_DATE = '2017-01-01T00:00:00'


def _soda_query(select, where, group, order, limit=50000):
    """One request to NYSERDA's Socrata (SODA) API, doing the aggregation server-side."""
    url = 'https://data.ny.gov/resource/thd2-fu8y.json'
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


def _pivot(rows, index_col):
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame()
    df['cnt'] = df['cnt'].astype(int)
    df['reg_month'] = pd.to_datetime(df['reg_month']).dt.strftime('%Y-%m-%d')
    return df.pivot_table(index=index_col, columns='reg_month', values='cnt', aggfunc='sum', fill_value=0)


def NY_Registrations():
    # NOTE: kept this function name so ci_runner.py's dispatch doesn't need
    # editing, but this is now rebate applications, not DMV registrations -
    # see the module-level comment above for why the source changed.
    base_where = f"submitted_date>='{NY_REBATE_MIN_DATE}'"

    type_rows = _soda_query(
        select="date_trunc_ym(submitted_date) as reg_month, ev_type, count(*) as cnt",
        where=base_where,
        group="date_trunc_ym(submitted_date), ev_type",
        order="reg_month",
    )
    make_rows = _soda_query(
        select="date_trunc_ym(submitted_date) as reg_month, make, count(*) as cnt",
        where=base_where,
        group="date_trunc_ym(submitted_date), make",
        order="reg_month",
    )

    df_total_type = _pivot(type_rows, 'ev_type')
    df_total_make = _pivot(make_rows, 'make')

    # Only include the 15 largest brands overall (same behavior as before)
    df_total_make = df_total_make.loc[df_total_make.sum(axis=1).sort_values(ascending=False).head(15).index]

    # Make proportional dataframes (share of that month's rebates)
    df_total_type_pct = df_total_type.div(df_total_type.sum(axis=0), axis=1).round(4)
    df_total_make_pct = df_total_make.div(df_total_make.sum(axis=0), axis=1).round(4)

    return [df_total_type_pct, df_total_make_pct]


def main():
    start = datetime.now()
    print("NY Monthly EV Rebates running as main")
    timestr = datetime.now().strftime("%m-%d-%y")
    filename = "NY Monthly EV Rebates " + timestr + ".txt"
    NY_Registrations()
    duration = datetime.now() - start
    print('\n' * 2, "Time elapsed to run:", duration, "(H:S:millseconds)")


if __name__ == "__main__":
    main()
