import json
import csv
import pandas as pd
import numpy as np

def make_json(csvFilePaths, outPath): 
    #
    df_list = []

    for file in csvFilePaths:
        df_in = pd.read_csv(file, sep=";")
        
        df_in = df_in.drop(columns=["LOCALITA", "PUNTORUGIADA °C", "VISIBILITA km",\
            "VENTOMEDIA km/h", "VENTOMAX km/h", "RAFFICA km/h", \
                "PRESSIONEMEDIA mb", "PIOGGIA mm"])

        # Note: The last 2 were dropped because always 0

        df_in["FENOMENI"].replace(np.nan, '', regex=True)
        df_in["FENOMENI"] = df_in["FENOMENI"].apply(mapFeature)

        df_in["STAGIONE"] = df_in["DATA"].apply(mapSeason)
        
        df_in = df_in.drop(columns=["DATA"])

        df_list.append(df_in)

    full_df = pd.concat(df_list)

    full_df = full_df.reset_index().drop(columns=["index"])

    full_df.to_csv(outPath, index=False)

def mapFeature(in_string):
    wordlist = str(in_string).split(" ")
    found = 0
    for wd in wordlist:
        if wd == "pioggia" or wd == "neve":
            found = 1
    return found

def mapSeason(in_string):
    mm = int(in_string.split('/')[1])
    if mm >= 1 and mm <= 2 or mm == 12:
        return "winter"
    elif mm >= 3 and mm <= 5:
        return "spring"
    elif mm >= 6 and mm <= 8:
        return "summer"
    else:
        return "fall"

########################################################################

if __name__ == "__main__":
    out_path = "weather_train.csv"

    inputfilesList = [
        "csv_ilMeteo/Torino-2021-01Gennaio.csv",
        "csv_ilMeteo/Torino-2021-02Febbraio.csv",
        "csv_ilMeteo/Torino-2021-03Marzo.csv",
        "csv_ilMeteo/Torino-2021-04Aprile.csv",
        "csv_ilMeteo/Torino-2021-05Maggio.csv",
        "csv_ilMeteo/Torino-2021-06Giugno.csv",
        "csv_ilMeteo/Torino-2021-07Luglio.csv",
        "csv_ilMeteo/Torino-2021-08Agosto.csv",
        "csv_ilMeteo/Torino-2021-09Settembre.csv",
        "csv_ilMeteo/Torino-2021-10Ottobre.csv",
        "csv_ilMeteo/Torino-2021-11Novembre.csv",
        "csv_ilMeteo/Torino-2021-12Dicembre.csv",
        "csv_ilMeteo/Torino-2022-01Gennaio.csv",
        "csv_ilMeteo/Torino-2022-02Febbraio.csv",
        "csv_ilMeteo/Torino-2022-03Marzo.csv",
        "csv_ilMeteo/Torino-2022-04Aprile.csv",
        "csv_ilMeteo/Torino-2022-05Maggio.csv",
        "csv_ilMeteo/Torino-2022-06Giugno.csv",
        "csv_ilMeteo/Torino-2022-07Luglio.csv",
        "csv_ilMeteo/Torino-2022-08Agosto.csv",
        "csv_ilMeteo/Torino-2022-09Settembre.csv",
        "csv_ilMeteo/Torino-2022-10Ottobre.csv",
        "csv_ilMeteo/Torino-2022-11Novembre.csv",
        "csv_ilMeteo/Torino-2022-12Dicembre.csv"
    ]
    make_json(inputfilesList, out_path)
