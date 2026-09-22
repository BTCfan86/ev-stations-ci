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
pd.set_option('display.max_columns', 13, 'display.max_rows', 100, 'display.width', 1000, 'display.max_colwidth', 18)


def CA_Monthly_EVs():
    URL = 'https://data.ca.gov/api/3/action/datastore_search?resource_id=9aa5b4c5-252c-4d68-b1be-ffe19a2f1d26&limit=1000000'
    data = requests.get(URL).json()
    data = data['result']['records']
    # print(data)
    # pprint.pprint(data, indent=3)
    df = pd.json_normalize(data)
    print(df)


def main():
    print("CA Monthly Total EVs running as main")
    timestr = datetime.now().strftime("%m-%d-%y")
    filename = "CA Monthly Total EVs " + timestr + ".txt"
    CA_Monthly_EVs()

if __name__ == "__main__":
    main()
