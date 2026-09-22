import time
import shutil
import pprint
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import json
import requests
import os
import sys
from pathlib import Path
# The following is not needed for Pycharm, but is needed for running from the Command Prompt, or from the Windows Task Scheduler
pd.set_option('display.max_columns', 15, 'display.max_rows', 100, 'display.width', 1000, 'display.max_colwidth', 25)
# FIX (portable version): derived from this file's own location instead of a hardcoded
# 'C:\Users\Michael\...' path, so it's correct on Windows, Linux (CI), wherever.
sys.path.insert(1, str(Path(__file__).resolve().parents[2]))
from Set_API_KEYs import set_NREL_API_KEY
from pandas._libs.tslibs.timestamps import Timestamp
# FIX: 'from cif import cif' removed - nothing in this file ever calls cif, and it's an
# obscure package that fails to build with modern setuptools unless you already have it
# installed, so this import alone could crash the whole script before it does anything.
from mpl_toolkits.basemap import Basemap
from geopy.distance import geodesic

# FIX (portable version): all hardcoded 'C:\Users\Michael\...' paths replaced with
# paths relative to this file, controlled by an optional EV_BASE_DIR env var
# (ci_runner.py sets this for CI runs). Works unchanged on your Windows machine too.
BASE_DIR = Path(os.environ.get("EV_BASE_DIR", Path(__file__).resolve().parent))


def nearest(items, pivot):
    return min(items, key=lambda x: abs(x - pivot))

def EV_Stations_Raw_Data(states):
    set_NREL_API_KEY()
    key = os.environ['NREL_API_KEY']
    last_update = "https://developer.nrel.gov/api/alt-fuel-stations/v1/last-updated.json?api_key=" + key
    last_update_get = requests.get(last_update).json()
    timestr = datetime.strptime(last_update_get['last_updated'], "%Y-%m-%dT%H:%M:%S%z").strftime("%m-%d-%y")  # set as of last date database updated per NREL
    old_path = BASE_DIR

    new_path = BASE_DIR / "JSON_Archives" / datetime.strptime(timestr, "%m-%d-%y").strftime("%Y-%m-%d")

    try:
        os.mkdir(new_path)
    except FileExistsError:
        shutil.rmtree(new_path)
        time.sleep(2)
        os.mkdir(new_path)

    for s in states:  # List of states included under main below
        state = s
        URL = "https://developer.nrel.gov/api/alt-fuel-stations/v1.json?api_key=" + key + "&fuel_type=ELEC&state=" + state + "&limit=all"
        txt_file = "EV_Stations " + state + " " + timestr + ".txt"
        data = requests.get(URL).json()

        with open(txt_file, 'w') as f:
            f.write(json.dumps(data, indent=4))
        f = open(txt_file)

        f.close()
        time.sleep(2)
        old_name = old_path / txt_file
        new_name = new_path / txt_file
        os.rename(old_name, new_name)

def EV_Stations_Closest_City(states):
    EV_Stations_Raw_Data(states)
    time.sleep(3)

    root_path = BASE_DIR / "JSON_Archives"
    dir_list = os.listdir(root_path)
    dates_list = [datetime.strptime(date, '%Y-%m-%d').date() for date in dir_list]
    last_update = max(dates_list).strftime('%Y-%m-%d')

    cols = ['station_name', 'street_address', 'state', 'zip', 'longitude', 'latitude', 'fuel_type_code', 'open_date', 'date_last_confirmed']
    df_comb = pd.DataFrame(columns=cols)

    sub_dir_path = root_path / last_update
    sub_dir_list = os.listdir(sub_dir_path)

    for filename in sub_dir_list:
        filepath = sub_dir_path / filename
        f = open(filepath)
        data = json.load(f)["fuel_stations"]
        df = pd.DataFrame(data, columns=cols)
        df = df.loc[df['fuel_type_code'] == 'ELEC'].reset_index().drop('index', axis=1)  # Electric stations only (no CNG etc.)
        # df = df.drop_duplicates(subset=['street_address'], keep="first")  # If we want in the future to run only discrete locations, uncomment this line
        df_comb = pd.concat([df_comb, df])
    df_comb = df_comb.reset_index().drop('index', axis=1)

    # City Summary Statistics
    cities_file = BASE_DIR / "City_Locations_v01.xlsx"
    cities = pd.read_excel(cities_file, sheet_name="Center_Cities", engine='openpyxl')
    city_names = cities['City'].tolist()

    limit = 20  # this is the number of miles around a city allowed
    df_comb['Closest_City'] = ''  # Adds an empty dataframe column to be populated later
    for station in range(len(df_comb.index)):
        dists = {}
        for city in range(len(city_names)):
            coords_city = cities['LAT'].iloc[city], cities['LON'].iloc[city]
            coords_station = df_comb['latitude'].iloc[station], df_comb['longitude'].iloc[station]
            dist = round(geodesic(coords_city, coords_station).miles, 3)
            dists[cities['City'].iloc[city]] = dist
        closest_city = {i for i in dists if dists[i] == min(dists.values())}  # Finds the closest city by iterating through a list of dictionaries
        closest_city = ''.join(closest_city)  # converts the Set format to a string format to be used as a dictionary key below
        # FIX: 'df_comb['Closest_City'].iloc[station] = closest_city' was a chained
        # assignment. On pandas >=2.x with Copy-on-Write (mandatory as of pandas 3.0)
        # this silently updates a throwaway copy and never touches df_comb, so every
        # row's Closest_City stayed '' and the whole grouping below collapsed to one
        # bucket. .loc on the real dataframe fixes this.
        if dists[closest_city] <= limit:
            df_comb.loc[df_comb.index[station], 'Closest_City'] = closest_city
        else:
            df_comb.loc[df_comb.index[station], 'Closest_City'] = "Other"

    # print(df_comb)
    return df_comb

def Combined_EV_Stations(states):
    df = EV_Stations_Closest_City(states)
    df['Counter'] = int(1)
    df['open_date'] = pd.to_datetime(df['open_date'], errors = 'coerce')
    df['date_last_confirmed'] = pd.to_datetime(df['date_last_confirmed'], errors = 'coerce')  # coerce makes values NaT
    df['open_date'] = df['open_date'].replace('NaT', pd.NA).fillna(df['date_last_confirmed'])  # If open_date isn't provided, I replace the open_date with the last confirmed date
    df = df.sort_values(by='open_date', ascending=True).reset_index().drop('index', axis=1)

    unique_cities = df.Closest_City.unique().tolist()
    df_output = pd.DataFrame()
    dates = pd.date_range(start=min(df['open_date']), end=datetime.today()).tolist()  # Gets the earliest date in the original set of dates, and includes each day until now
    df_output['open_date'] = dates

    for i in unique_cities:
        df_city = df[df.Closest_City == i].reset_index().drop('index', axis=1)
        duration = str((datetime.now() - min(df_city['open_date'])).days + 1) + "d"  # Number of days in the dataset
        amounts = (df_city.groupby(["Closest_City"]).apply(lambda g: (g.groupby('open_date', as_index=False).agg({'Counter': 'sum'}).rolling(duration, on='open_date').sum())))
        df_city[i] = df_city["open_date"].map(amounts.set_index('open_date')['Counter'])  # Finds rolling total of stations in a city, and names that column the city's name
        df_city = df_city.drop_duplicates(subset=['open_date'], keep="last")  # Leaves just the last observation with the total as of that date.  Keeping first vs. last actually doesn't matter here
        df_city = df_city.drop(['station_name', 'street_address', 'state', 'zip', 'longitude', 'latitude', 'fuel_type_code', 'date_last_confirmed', 'Closest_City', 'Counter'], axis=1)
        df_output = df_output.merge(df_city, how="left", on="open_date")
        # print('\n' * 2, df_city)

    df_output.loc[:, df_output.columns[1:]] = df_output.loc[:, df_output.columns[1:]].ffill()  # Flatlines the number of stations between openning dates
    df_output = df_output.fillna(0)  # Assume NaNs (before first observation) are zero

    # Line chart of cumulative stations in each city including all big cities
    df_chart = df_output.drop('Other', axis=1).tail(6 * 365)  # Takes out stations outside of the selected cities.  Also limits dates to last 6 years
    plt.style.use('bmh')
    df_chart.plot(x='open_date', y=df_chart.columns[1:], kind='line', figsize=(10, 6), fontsize='small')
    plt.title("Number of EV Charging Stations in US Cities")
    plt.xlabel(None)
    plt.ylabel("Number of Stations (Incl. Multiple in Single Location)", fontsize='small')
    plt.legend(loc='upper center', fontsize='small', bbox_to_anchor=(0.5, -0.1), fancybox=True, shadow=True, ncol=7)  # This formats the legend below the chart in beautiful way.  bbox_to_anchor sets vertical, horiz position
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.show()

    # Map on a per-state basis
    for s in states:
        df_map = df[df.state == s].reset_index().drop('index', axis=1)
        sites_lat = df_map["latitude"].tolist()
        sites_lon = df_map["longitude"].tolist()
        states_file = BASE_DIR / "Basemap_State_Corners.xlsx"
        states_df = pd.read_excel(states_file, sheet_name="States", engine='openpyxl')
        state_index = states_df[states_df["State"] == s].index
        s_llcrnrlat = states_df['llcrnrlat'].iloc[state_index]
        s_urcrnrlat = states_df['urcrnrlat'].iloc[state_index]
        s_llcrnrlon = states_df['llcrnrlon'].iloc[state_index]
        s_urcrnrlon = states_df['urcrnrlon'].iloc[state_index]
        plt.figure(figsize=(15, 12))
        m = Basemap(projection="mill", llcrnrlat=s_llcrnrlat, urcrnrlat=s_urcrnrlat, llcrnrlon=s_llcrnrlon, urcrnrlon=s_urcrnrlon, resolution="f")
        title = s + " EV Charging Stations"
        m.drawcoastlines()
        m.drawstates(color="black", linewidth=3)
        m.drawcounties(color="grey", linewidth=1)
        plt.title(title, fontsize=20)
        m.scatter(sites_lon, sites_lat, latlon=True, s=5, c="blue", zorder=2)  # order by longitude, latitude... not clear why
        plt.show()  # ci_runner.py patches this to save a PNG instead of blocking

    comb_output = {}
    decile_cols = df_output.columns.tolist()

    for i in decile_cols[1:]:
        index = i.find("+")
        dec_title = i + " Decile"
        df_output[dec_title] = pd.qcut(df_output[i], 10, labels=False, duplicates='drop')  # Add decline of each datapoint.  Change the 10 here to get different intervals (quartiles, quintiles etc.0
        df_output = df_output.copy()
        latest_pt = round(df_output[i].iloc[-1], 3)
        latest_date = df_output['open_date'].iloc[-1]
        latest_decile = df_output[dec_title].iloc[-1]
        url = ''
        source = ''

        _1mo_ago_dt = nearest(pd.to_datetime(df_output['open_date']), Timestamp(pd.Timestamp(latest_date) - pd.DateOffset(months=1)).to_pydatetime()).strftime("%Y-%m-%d")
        _1mo_chg = round(latest_pt - df_output[i].iloc[df_output[df_output['open_date'] == _1mo_ago_dt].index.item()], 4)  # This measures the change in level, not as a growth rate
        _1mo_decile = df_output[dec_title].iloc[df_output[df_output['open_date'] == _1mo_ago_dt].index.item()]

        _3mo_ago_dt = nearest(pd.to_datetime(df_output['open_date']), Timestamp(pd.Timestamp(latest_date) - pd.DateOffset(months=3)).to_pydatetime()).strftime("%Y-%m-%d")
        _3mo_chg = round(latest_pt - df_output[i].iloc[df_output[df_output['open_date'] == _3mo_ago_dt].index.item()], 4)  # This measures the change in level, not as a growth rate
        _3mo_decile = df_output[dec_title].iloc[df_output[df_output['open_date'] == _3mo_ago_dt].index.item()]

        _6mo_ago_dt = nearest(pd.to_datetime(df_output['open_date']), Timestamp(pd.Timestamp(latest_date) - pd.DateOffset(months=6)).to_pydatetime()).strftime("%Y-%m-%d")
        _6mo_chg = round(latest_pt - df_output[i].iloc[df_output[df_output['open_date'] == _6mo_ago_dt].index.item()], 4)  # This measures the change in level, not as a growth rate
        _6mo_decile = df_output[dec_title].iloc[df_output[df_output['open_date'] == _6mo_ago_dt].index.item()]

        _12mo_ago_dt = nearest(pd.to_datetime(df_output['open_date']), Timestamp(pd.Timestamp(latest_date) - pd.DateOffset(months=12)).to_pydatetime()).strftime("%Y-%m-%d")
        _12mo_chg = round(latest_pt - df_output[i].iloc[df_output[df_output['open_date'] == _12mo_ago_dt].index.item()], 4)  # This measures the change in level, not as a growth rate
        _12mo_decile = df_output[dec_title].iloc[df_output[df_output['open_date'] == _12mo_ago_dt].index.item()]

        # Key Output
        output_label = "Electric vehicle charge stations in " + i
        output = {output_label: {'Data': {'Last_Value': latest_pt, '1Mo_Chg': _1mo_chg, '3Mo_Chg': _3mo_chg, '6Mo_Chg': _6mo_chg, '12Mo_Chg': _12mo_chg,
                                          'Decile': latest_decile, '1Mo_Decile': _1mo_decile, '3Mo_Decile': _3mo_decile, '6Mo_Decile': _6mo_decile, '12Mo_Decile': _12mo_decile},
                                 'Dates': {'1Mo_Dt': _1mo_ago_dt, '3Mo_Dt': _3mo_ago_dt, '6Mo_Dt': _6mo_ago_dt, '12Mo_Dt': _12mo_ago_dt, 'Cur_Dt':  pd.Timestamp(latest_date).to_pydatetime().strftime("%Y-%m-%d")},
                                 'Industries': {'Housing': 'TBD', 'Financials': 'TBD', 'Consumer': 'TBD'},
                                 'URL': url, 'Source': source}}
        comb_output[output_label] = output[output_label]

    # print(comb_output)
    # pprint.pprint(comb_output)
    return df_output

def main():
    print("EV Stations Analysis running as main")
    start = datetime.now()
    timestr = start.strftime('%Y-%m-%d')
    filename = "EV Stations Analysis - " + timestr + ".txt"

    states = ['CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI', 'NJ', 'VA', 'WA', 'AZ', 'MA', 'CT', 'MD', 'DC', 'NH']
    # EV_Stations_Raw_Data(states)
    # EV_Stations_Closest_City(states)
    Combined_EV_Stations(states)
    duration = datetime.now() - start
    print('\n' * 2, "Time elapsed to run:", duration, "(H:S:millseconds)")

if __name__ == "__main__":
    main()
