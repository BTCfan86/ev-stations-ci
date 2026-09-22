import time
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import json
import requests
import os
import pprint
import sys
pd.set_option('display.max_columns', 15, 'display.max_rows', 100, 'display.width', 1000, 'display.max_colwidth', 15)


def NC_Monthly_EVs():
    cur_year = int(datetime.now().strftime("%Y"))
    df_NC = pd.DataFrame()
    for i in range(2019, cur_year+1): # 2019 is the earliest year available
        for x in range(1, 13):
            time.sleep(2)
            try:
                URL = 'https://linc.osbm.nc.gov/api/explore/v2.1/catalog/datasets/vehicle-registration/records?limit=' + '100' + '&refine=year%3A%22' + str(i) + '%22&refine=month%3A%22' + str("{:0>{}}".format(x, 2)) + '%22'
                response = requests.get(URL).json()
                data = response['results']
                df = pd.json_normalize(data)
                df['date'] = pd.to_datetime(df['date']).dt.strftime("%Y-%m")  # Change dates to better format
                df['date'] = pd.to_datetime(df['date']).dt.strftime("%Y-%m-%d")
                df = df.drop(['year', 'month', 'electric_difference', 'plug_in_hybrid_difference', 'hybrid_difference', 'all_hybrids_difference', 'gas_difference', 'diesel_difference'], axis=1)
                df.loc["Total"] = df.sum()
                df.at['Total', 'date'] = df['date'].iloc[-2]
                df.at['Total', 'county'] = 'NC'
                df = df.tail(1).reset_index(drop=True)
                df_NC = pd.concat([df_NC, df]).reset_index(drop=True)
                # print(df_NC)
            except: break

    df_NC['Total_EV'] = df_NC['electric'] + df_NC['plug_in_hybrid']
    df_NC['Total'] = df_NC['electric'] + df_NC['all_hybrids'] + df_NC['diesel'] + df_NC['gas']
    df_NC['Pct_EVs'] = round(df_NC['Total_EV'] / df_NC['Total'], 4)
    df_NC = df_NC.drop(['county', 'electric', 'plug_in_hybrid', 'hybrid', 'all_hybrids', 'diesel', 'gas', 'Total_EV', 'Total'], axis=1)
    df_NC = df_NC.set_index('date')
    df_NC = pd.DataFrame(df_NC).T  # Transpose dataframe

    # print(df_NC)
    return df_NC

def main():
    print("NC Monthly Total EVs running as main")
    timestr = datetime.now().strftime("%m-%d-%y")
    filename = "NC Monthly Total EVs " + timestr + ".txt"
    NC_Monthly_EVs()

if __name__ == "__main__":
    main()
