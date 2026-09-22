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

def WA_EV_Mkt_Share():
    URL = 'https://data.wa.gov/resource/rpr4-cgyd.json?' + '&vehicle_primary_use=' + 'Passenger' + '&$limit=' + '10000'
    data = requests.get(URL).json()
    df = pd.json_normalize(data)
    df = df.drop(['county', 'city', 'state_of_residence', 'zip', 'meets_2019_hb_2042_sale_price_value_requirement', '_2019_hb_2042_sale_price_value_requirement', 'electric_vehicle_fee_paid',
                  'transportation_electrification_fee_paid', 'hybrid_vehicle_electrification_fee_paid', 'census_tract_2020', 'legislative_district', 'electric_range', 'base_msrp', 'transaction_year',
                  'electric_utility', 'vin_1_10', 'odometer_code', 'vehicle_primary_use', 'odometer_reading', 'sale_price', 'new_or_used_vehicle'], axis=1)
    # The VINs included above are not the whole VIN, just the first 10 digits.  So, need to use the DOL numbers instead

    reg_types = ['Original Registration', 'Registration Renewal']
    df = df[df['transaction_type'].isin(reg_types)].reset_index().drop('index', axis=1)
    df['transaction_date'] = pd.to_datetime(df['transaction_date']).dt.strftime("%Y-%m-%d")
    df['date_of_vehicle_sale'] = pd.to_datetime(df['date_of_vehicle_sale']).dt.strftime("%Y-%m-%d")
    df = df.sort_values(by='transaction_date', ascending=True).reset_index().drop('index', axis=1)
    df['reg_month'] = pd.to_datetime(df['transaction_date']).dt.to_period('M').astype(str)
    df['reg_month'] = pd.to_datetime(df['reg_month']).dt.strftime("%Y-%m-%d")  # Change dates to better format
    months = df['reg_month'].unique()  # Returns unique months

    # Create total DF of car brands
    total_make = df['make'].value_counts()
    df_total_make = pd.DataFrame([total_make]).T  # .T at the end is for transpose
    df_total_make['Total'] = df_total_make['count'].astype(int)
    df_total_make = df_total_make.drop('count', axis=1)

    for m in months:
        df_month = df[df.reg_month == m].reset_index().drop('index', axis=1)
        s_make = df_month.make.value_counts()
        df_make = pd.DataFrame([s_make]).T
        df_make[m] = df_make['count'].astype(int)
        df_make = df_make.drop('count', axis=1)
        df_total_make = df_total_make.join(df_make)
        df_total_make[m] = df_total_make[m].fillna(0)

    df_total_make = df_total_make.head(15)  # Only include 15 largest brands
    df_total_make = df_total_make.drop('Total', axis=1)

    df_total_make_pct = df_total_make
    cols = df_total_make_pct.columns.tolist()
    for c in cols:
        df_total_make_pct[c] = round((df_total_make_pct[c] / df_total_make_pct[c].sum()), 4)

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
