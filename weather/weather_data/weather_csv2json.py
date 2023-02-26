import json
import csv
import pandas as pd
import numpy as np

def make_json(csvFilePaths, jsonFilePath): 
    #
    df_list = []

    for file in csvFilePaths:
        df_in = pd.read_csv(file, sep=";")
        
        df_in = df_in.drop(columns=["DATA", "LOCALITA", "PUNTORUGIADA °C", "VISIBILITA km",\
            "VENTOMEDIA km/h", "VENTOMAX km/h", "RAFFICA km/h", \
                "PRESSIONEMEDIA mb", "PIOGGIA mm"])

        df_in["FENOMENI"].replace(np.nan, '', regex=True)
        df_in["FENOMENI"] = df_in["FENOMENI"].apply(mapFeature)
        
        df_list.append(df_in)

    full_df = pd.concat(df_list)

    full_df = full_df.reset_index().drop(columns=["index"])

    #### JSON               NOTICE: \u00b0 is °
    full_df.to_json(jsonFilePath, orient="records")

def mapFeature(in_string):
    wordlist = str(in_string).split(" ")
    found = 0
    for wd in wordlist:
        if wd == "pioggia":
            found = 1
    return found

########################################################################

if __name__ == "__main__":
    out_path = "json_ilMeteo/meteo.json"

    inputfilesList = [
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
        "csv_ilMeteo/Torino-2022-11Novembre.csv"
    ]
    make_json(inputfilesList, out_path)
