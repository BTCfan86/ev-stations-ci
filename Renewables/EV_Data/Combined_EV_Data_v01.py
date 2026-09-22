import time
from datetime import datetime
from matplotlib.ticker import PercentFormatter
import pandas as pd
import matplotlib.pyplot as plt
import json
import requests
import os
import pprint
import urllib.request
import sys
from pathlib import Path
# FIX (portable version): the original hardcoded
# sys.path.insert(1, r'C:\Users\Michael\PycharmProjects\pythonProject'), which only
# works on that one Windows machine. This derives the project root from this file's
# own location instead, so it works unchanged on Windows, Linux (CI), or anywhere else:
# this file lives at <root>/Renewables/EV_Data/Combined_EV_Data_v01.py, so root is two
# levels up.
sys.path.insert(1, str(Path(__file__).resolve().parents[2]))
from Renewables.EV_Data.WA_EVs_v01 import WA_EV_Pct, WA_EV_Mkt_Share
from Renewables.EV_Data.NY_EVs_v01 import NY_Registrations
from Renewables.EV_Data.NC_EVs_v01 import NC_Monthly_EVs
pd.set_option('display.max_columns', 12, 'display.max_rows', 200, 'display.width', 1000, 'display.max_colwidth', 30)


def combined_EV_share():
    # WA EV % data
    WA_EV = WA_EV_Pct()
    WA_EV = WA_EV.drop(['battery_electric_vehicles_bevs_', 'plug_in_hybrid_electric_vehicles_phevs_', 'electric_vehicle_ev_total', 'non_electric_vehicles', 'total_vehicles'], axis=0)
    WA_EV = WA_EV.rename(index={'percent_EVs': 'WA Pct EVs'})

    # NC EV % data
    NC_EV = NC_Monthly_EVs()
    NC_EV = NC_EV.rename(index={'Pct_EVs': 'NC Pct EVs'})

    # NY EV % data
    NY_EV_return = NY_Registrations()
    NY_EV_pct = NY_EV_return[0]  # first item returned is percentages by type of fuel

    NY_rows_drop = ['GAS', 'DIESEL', 'NONE', 'OTHER', 'FLEX', 'COMP N/G', 'PROPANE']
    for i in NY_EV_pct.index.tolist():
        if i in NY_rows_drop:
            NY_EV_pct = NY_EV_pct.drop(i, axis=0)
    NY_EV_pct = NY_EV_pct.iloc[:, :-1]  # the last argument in this row drops the last column b/c it's a partial month of data
    NY_EV_pct = NY_EV_pct.rename(index={'ELECTRIC': 'NY Pct EVs'})
    combined_EV_pct = pd.concat([WA_EV, NY_EV_pct, NC_EV], axis=0)

    brands_to_keep = ['TESLA']  # Include the brands you want to show.  Need to conform the names of brands in the source files to make this work properly
    WA_brands = WA_EV_Mkt_Share()
    NY_brands = NY_EV_return[2].iloc[:, :-1]  # the last argument in this row drops the last column b/c it's a partial month of data

    WA_brands = WA_brands.loc[brands_to_keep]
    NY_brands = NY_brands.loc[brands_to_keep]

    for b in brands_to_keep:   # Changes just the name of the brand to state EV market share
        WA_brands = WA_brands.rename(index={b: 'WA ' + b + " EV Share %"})
        NY_brands = NY_brands.rename(index={b: 'NY ' + b + " EV Share %"})

    combined_EV_Share = pd.concat([WA_brands, NY_brands], axis=0)

    # Chart for EV adoption by state
    EV_pct_chart = combined_EV_pct.T  # Transpose to get into the format the chart tool below uses
    for c in EV_pct_chart.columns.tolist():
        x = c + " Rolling 3Mo Avg."
        EV_pct_chart[x] = EV_pct_chart[c].rolling(3).mean()
        EV_pct_chart = EV_pct_chart.drop(c, axis=1)
    EV_pct_chart.index = pd.to_datetime(EV_pct_chart.index)  # Need to switch to datetime so the chart can recognize the dates
    plt.style.use('bmh')
    EV_pct_chart.plot(kind='line', figsize=(10, 6), color=["r", "b", "g"])
    plt.title('EV Penetration of Registered Autos')
    plt.xlabel('Year')
    plt.ylabel('% EV of Total Registered Autos')
    plt.legend(EV_pct_chart.columns)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1.0))
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.show()

    # Chart for EV brands
    df_brand_chart = combined_EV_Share.T  # Transpose to get into the format the chart tool below uses
    for d in df_brand_chart.columns.tolist():
        y = d + " Rolling 3Mo Avg."
        df_brand_chart[y] = df_brand_chart[d].rolling(3).mean()
        df_brand_chart = df_brand_chart.drop(d, axis=1)
    df_brand_chart.index = pd.to_datetime(df_brand_chart.index)  # Need to switch to datetime so the chart can recognize the dates
    plt.style.use('bmh')
    df_brand_chart.plot(kind='line', figsize=(10, 6), color=["r", "b", "g"])
    plt.title('Brand Market Share of Registered EVs')
    plt.xlabel('Year')
    plt.ylabel('Brand % of Total EV Registrations')
    plt.legend(df_brand_chart.columns)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1.0))
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.show()

def main():
    start = datetime.now()
    print("Combined EV Statistics running as main")
    timestr = datetime.now().strftime("%m-%d-%y")
    filename = "Combined EV Statistics " + timestr + ".txt"
    combined_EV_share()
    duration = datetime.now() - start
    print('\n' * 2, "Time elapsed to run:", duration, "(H:S:millseconds)")

if __name__ == "__main__":
    main()
