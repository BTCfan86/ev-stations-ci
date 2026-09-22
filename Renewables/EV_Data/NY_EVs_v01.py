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


def NY_Registrations():
    URL = 'https://data.ny.gov/resource/w4pv-hbkt.json?' + '$where=model_year>=' + str(2000) + '&record_type=' + 'VEH' + '&registration_class=' + 'PAS' + '&$limit=' + '15000000'
    data = requests.get(URL).json()
    df = pd.json_normalize(data)
    df = df.drop(['city', 'state', 'zip', 'county', 'body_type', 'unladen_weight', 'color', 'scofflaw_indicator', 'suspension_indicator', 'revocation_indicator', 'maximum_gross_weight'], axis=1)
    df['reg_expiration_date'] = pd.to_datetime(df['reg_expiration_date']).dt.strftime("%Y-%m-%d")  # Change dates to better format
    df['reg_valid_date'] = pd.to_datetime(df['reg_valid_date']).dt.strftime("%Y-%m-%d")  # Change dates to better format
    df['reg_month'] = pd.to_datetime(df['reg_valid_date']).dt.to_period('M').astype(str)
    df['reg_month'] = pd.to_datetime(df['reg_month']).dt.strftime("%Y-%m-%d")  # Change dates to better format

    # Order by registration month
    df['reg_month'] = pd.to_datetime(df['reg_month']).dt.strftime("%Y-%m-%d")
    df = df.sort_values(by='reg_month', ascending=True).reset_index().drop('index', axis=1)
    months = df['reg_month'].unique()  # Returns unique months
    df['model_year'] = df['model_year'].astype(int)
    df['make'] = df['make'].replace({'LU/MO': 'LUCID', 'LUCI': 'LUCID', 'RVN': 'RIVIA', 'RIVA': 'RIVIA', 'RIVIN': 'RIVIA', 'VW': 'VOLKS', 'ME/B': 'ME/BE', 'LEXUI': 'LEXUS', 'MERZ': 'ME/BE'})  # Fixing mis-labelings in source
    df['make'] = df['make'].replace({'ME/BE': 'MERCEDES-BENZ', 'TOYOT': 'TOYOTA', 'PONTI': 'PONTIAC', 'VOLKS': 'VOLKSWAGEN', 'RIVIA': 'RIVIAN', 'CHEVR': 'CHEVROLET', 'SUZUK': 'SUZUKI',
                                     'MITSU': 'MITSUI', 'NISSA': 'NISSAN', 'HYUND': 'HYUNDAI'})  # Conforming to Washington State brand names

    # Create fuel type DF
    total_fuel = df['fuel_type'].value_counts()
    df_total_fuel = pd.DataFrame([total_fuel]).T  # .T at the end is for transpose
    df_total_fuel['Total'] = df_total_fuel['count'].astype(int)
    df_total_fuel = df_total_fuel.drop('count', axis=1)

    # Create make breakdown for all fuel types
    total_make = df['make'].value_counts()
    df_total_make = pd.DataFrame([total_make]).T  # .T at the end is for transpose
    df_total_make['Total'] = df_total_make['count'].astype(int)
    df_total_make = df_total_make.drop('count', axis=1)

    # Create make breakdown for only EVs
    df_EV_make = df[df.fuel_type == 'ELECTRIC']  # COMMENT OUT THIS ROW TO INCLUDE ALL FUEL TYPES. LEAVE RUNNING IF YOU ONLY WANT EVs
    total_EV_make = df_EV_make['make'].value_counts()
    df_total_EV_make = pd.DataFrame([total_EV_make]).T  # .T at the end is for transpose
    df_total_EV_make['Total'] = df_total_EV_make['count'].astype(int)
    df_total_EV_make = df_total_EV_make.drop('count', axis=1)

    for m in months:
        df_month = df[df.reg_month == m].reset_index().drop('index', axis=1)

        s_fuel = df_month.fuel_type.value_counts()
        df_fuel = pd.DataFrame([s_fuel]).T
        df_fuel[m] = df_fuel['count'].astype(int)
        df_fuel = df_fuel.drop('count', axis=1)
        df_total_fuel = df_total_fuel.join(df_fuel)
        df_total_fuel[m] = df_total_fuel[m].fillna(0)

        s_make = df_month.make.value_counts()
        df_make = pd.DataFrame([s_make]).T
        df_make[m] = df_make['count'].astype(int)
        df_make = df_make.drop('count', axis=1)
        df_total_make = df_total_make.join(df_make)
        df_total_make[m] = df_total_make[m].fillna(0)

        # Make market shares for EVs only
        df_EV_month = df_month[df_month.fuel_type == 'ELECTRIC']
        s_EV_make = df_EV_month.make.value_counts()
        df_month_EV_make = pd.DataFrame([s_EV_make]).T
        df_month_EV_make[m] = df_month_EV_make['count'].astype(int)
        df_month_EV_make = df_month_EV_make.drop('count', axis=1)
        df_total_EV_make = df_total_EV_make.join(df_month_EV_make)
        df_total_EV_make[m] = df_total_EV_make[m].fillna(0)

    df_total_make = df_total_make.head(15)  # Only include 15 largest brands
    df_total_EV_make = df_total_EV_make.head(15)  # Only include 15 largest brands
    # print(df_total_fuel, '\n', df_total_make, '\n', df_total_EV_make)

    df_total_make = df_total_make.drop('Total', axis=1)
    df_total_fuel = df_total_fuel.drop('Total', axis=1)
    df_total_EV_make = df_total_EV_make.drop('Total', axis=1)

    # Make proportional dataframes
    df_total_make_pct = df_total_make
    df_total_fuel_pct = df_total_fuel
    df_total_EV_pct = df_total_EV_make
    cols = df_total_make_pct.columns.tolist()
    for c in cols:
        df_total_make_pct[c] = round((df_total_make_pct[c] / df_total_make_pct[c].sum()), 4)
        df_total_fuel_pct[c] = round((df_total_fuel_pct[c] / df_total_fuel_pct[c].sum()), 4)
        df_total_EV_pct[c] = round((df_total_EV_pct[c] / df_total_EV_pct[c].sum()), 4)

    # print(df_total_fuel_pct, '\n', df_total_make_pct, '\n', df_total_EV_pct)
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
