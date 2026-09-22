import time
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
# FIX (portable version): original had sys.path.insert(1, '/Users/Michael/PycharmProjects/pythonProject'),
# a macOS path baked into an otherwise all-Windows-paths script. Derived from this
# file's own location instead, so it's correct on whatever machine runs it.
sys.path.insert(1, str(Path(__file__).resolve().parents[2]))
from Set_API_KEYs import set_NREL_API_KEY
from mpl_toolkits.basemap import Basemap
from geopy.distance import geodesic

# FIX (portable version): all the original hardcoded 'C:\Users\Michael\...' paths are
# replaced with paths relative to this file, controlled by an optional EV_BASE_DIR env
# var (ci_runner.py sets this for CI runs). Works unchanged on your Windows machine too.
BASE_DIR = Path(os.environ.get("EV_BASE_DIR", Path(__file__).resolve().parent))


def EV_Stations():
    set_NREL_API_KEY()
    key = os.environ['NREL_API_KEY']
    last_update = "https://developer.nrel.gov/api/alt-fuel-stations/v1/last-updated.json?api_key=" + key
    last_update_get = requests.get(last_update).json()
    timestr = datetime.strptime(last_update_get['last_updated'], "%Y-%m-%dT%H:%M:%S%z").strftime("%m-%d-%y")  # set as of last date database updated per NREL
    old_path = BASE_DIR
    new_path = BASE_DIR / "JSON_Archives"

    states = ['CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI', 'NJ', 'VA', 'WA', 'AZ', 'MA', 'CT', 'MD', 'DC']
    for s in states:
        state = s
        URL = "https://developer.nrel.gov/api/alt-fuel-stations/v1.json?api_key=" + key + "&fuel_type=ELEC&state=" + state + "&limit=all"
        txt_file = "EV_Stations " + state + " " + timestr + ".txt"
        data = requests.get(URL).json()
        with open(txt_file, 'w') as f:
            f.write(json.dumps(data, indent=4))
        f = open(txt_file)
        data = json.load(f)["fuel_stations"]
        df = pd.DataFrame(data, columns=['station_name', 'street_address', 'zip', 'longitude', 'latitude'])
        df = df.drop_duplicates(subset=['street_address'], keep="first")

        # City Summary Statistics
        cities_file = BASE_DIR / "City_Locations_v01.xlsx"
        cities = pd.read_excel(cities_file, sheet_name="Cities", engine='openpyxl')
        cities = cities.drop('State', axis=1)  # 1 is the column index.  0 would be or a row
        state_cities = cities[cities.State_Adj.isin([state])]
        city_names = state_cities['City'].tolist()

        limit = 20  # this is the number of miles around a city allowed
        for city in range(len(city_names)):
            coords_city = state_cities['LAT'].iloc[city], state_cities['LON'].iloc[city]
            dists = []
            for station in range(len(df.index)):
                coords_station = df['latitude'].iloc[station], df['longitude'].iloc[station]
                dist = round(geodesic(coords_city, coords_station).miles, 2)
                dists.append(dist)
            df[city_names[city]] = dists

        nearest_city = []
        for station in range(len(df.index)):
            station_city = []
            for city in city_names:
                if df[city].iloc[station] < limit:
                    station_city.append(city)
            if len(station_city) >= 1:
                nearest_city.append(station_city[0])  # if the station is within limit of 2+ cities, just take the first in the list
            if not station_city:
                nearest_city.append("NA")
        df["Nearest_City"] = nearest_city
        summary = df["Nearest_City"].value_counts()

        state_csv = state + " EV_Stations " + timestr + ".csv"
        state_csv_path = BASE_DIR / "Historical" / state_csv
        summary.reset_index().to_csv(state_csv_path)

        print("-------------------------------------------")
        print(state, " Cities Charging Stations")
        print("-------------------------------------------")
        print(summary)

        # Map
        sites_lat = df["latitude"].tolist()
        sites_lon = df["longitude"].tolist()
        states_file = BASE_DIR / "Basemap_State_Corners.xlsx"
        states_df = pd.read_excel(states_file, sheet_name="States", engine='openpyxl')
        state_index = states_df[states_df["State"] == state].index
        s_llcrnrlat = states_df['llcrnrlat'].iloc[state_index]
        s_urcrnrlat = states_df['urcrnrlat'].iloc[state_index]
        s_llcrnrlon = states_df['llcrnrlon'].iloc[state_index]
        s_urcrnrlon = states_df['urcrnrlon'].iloc[state_index]
        fig = plt.figure(figsize=(15,12))
        m = Basemap(projection="mill", llcrnrlat=s_llcrnrlat, urcrnrlat=s_urcrnrlat, llcrnrlon=s_llcrnrlon, urcrnrlon=s_urcrnrlon, resolution="f")
        title = state + " EV Charging Stations"
        m.drawcoastlines()
        m.drawstates(color="black", linewidth=3)
        m.drawcounties(color="grey", linewidth=1)
        plt.title(title, fontsize=20)
        m.scatter(sites_lon, sites_lat, latlon=True, s=5, c="blue", zorder=2)  # order by longitude, latitude... not clear why
        plt.show()  # ci_runner.py patches this to save a PNG instead of blocking

        f.close()
        time.sleep(2)
        old_name = old_path / txt_file
        new_name = new_path / txt_file
        os.rename(old_name, new_name)

def main():
    print("EV Stations running as main")
    EV_Stations()

if __name__ == "__main__":
    main()
