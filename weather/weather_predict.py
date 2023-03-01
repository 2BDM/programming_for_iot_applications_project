import numpy as np
import pandas as pd
import random
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis

"""
This program is used to make weather prediction using the sensor data and having
as training set the historical data about the weather
"""

#######################################################################################

COLS_CURRENT = ['TMEDIA °C', 'TMIN °C', 'TMAX °C', 'UMIDITA %', 'PRESSIONESLM mb', 'STAGIONE']
COLS_FUTURE = ['TMEDIA °C', 'TMIN °C', 'TMAX °C', 'UMIDITA %', 'PRESSIONESLM mb', 'STAGIONE', 'FENOMENI']
SEASON2INDEX = {
        'winter': 0,
        'spring': 1,
        'summer': 2,
        'fall': 3
    }

#######################################################################################
### Exported methods
#######################################################################################

def futureRain(test_measurements, models_list=None):
    """
    Perform estimation of future precipitations
    """
    curr_szn = test_measurements["STAGIONE"]
    
    test_nd = test_measurements.drop(["STAGIONE"]).values.reshape(1, -1)

    if curr_szn == "winter" or curr_szn == 0:
        pred_curr = models_list[0].predict(test_nd)
        return pred_curr
    if curr_szn == "spring" or curr_szn == 1:
        pred_curr = models_list[1].predict(test_nd)
        return pred_curr
    if curr_szn == "summer" or curr_szn == 2:
        pred_curr = models_list[2].predict(test_nd)
        return pred_curr
    if curr_szn == "fall" or curr_szn == 3:
        pred_curr = models_list[3].predict(test_nd)
        return pred_curr
    
def futureRain_2(test_df, model=None, index="predicted"):
    """
    Used to predict, season is a feature - test_measurements is 
    a pd.Series object consisting in the tested element.
    The index name of the prediction is "predicted".
    """
    pred_curr = model.predict(test_df.values.reshape(1, -1))

    pred_curr = pd.Series(pred_curr, index=[index])

    return pred_curr

def currWeather(test_measurements, models_list=None):
    """
    Predict current weather.

    test_measurements: single Index (row) object containing the features: 
    'TMEDIA °C', 'TMIN °C', 'TMAX °C', 'UMIDITA %', 'PRESSIONESLM mb', 
    'STAGIONE'

    Accuracy: 0.821

    BEST FOR CURRENT WEATHER PREDICTION
    """
    curr_szn = test_measurements["STAGIONE"]
    # te_actual = test_measurements["FENOMENI"]         # --> Should not be present at testing
    
    test_nd = test_measurements.drop(["STAGIONE"]).values.reshape(1, -1)

    if curr_szn == "winter" or curr_szn == 0:
        pred_curr = models_list[0].predict(test_nd)
        return pred_curr
    if curr_szn == "spring" or curr_szn == 1:
        pred_curr = models_list[1].predict(test_nd)
        return pred_curr
    if curr_szn == "summer" or curr_szn == 2:
        pred_curr = models_list[2].predict(test_nd)
        return pred_curr
    if curr_szn == "fall" or curr_szn == 3:
        pred_curr = models_list[3].predict(test_nd)
        return pred_curr

def currWeather_2(test_series, model=None, index="predicted"):
    """
    Used to predict, season is a feature - test_series is 
    a pd.Series object consisting in the tested element.
    The index name is "predicted".
    """
    pred_curr = model.predict(test_series.values.reshape(1, -1))

    pred_curr = pd.Series(pred_curr, index=[index])

    return pred_curr

#######################################################################################

if __name__ == "__main__":
    tr_set_file = "weather_data/weather_train.csv"
    try:
        weather_df = pd.read_csv(tr_set_file)
    except:
        weather_df = pd.read_csv(("weather/" + tr_set_file))

    colnames = weather_df.columns
    print(colnames)

    # 'LOCALITA', 'TMEDIA °C', 'TMIN °C', 'TMAX °C', 'UMIDITA %', 'PRESSIONESLM mb', 'FENOMENI', 'STAGIONE'

    # Since few missing, fill them and drop location
    weather_df = weather_df.ffill().drop(columns=["LOCALITA"])

    # Stats
    n_tot = len(weather_df.index)
    n_rain = weather_df["FENOMENI"].sum()
    n_no_rain = n_tot - n_rain

    print(f"Number of rain records: {n_rain}\nNumber of no rain: {n_no_rain}")
    print(f"Fraction of no rain: {n_no_rain/n_tot}")
    
    ############### Current weather prediction ########################################
    # Predict 'FENOMENI'
    # Based on values of "STAGIONE"

    ### Train/test:
    # Shuffle data:
    sh_range = list(range(len(weather_df.index)))
    random.shuffle(sh_range)

    sh_weather = weather_df.iloc[sh_range]        # SHUFFLED DF

    n_train = round(0.75*n_tot)
    n_test = n_tot - n_train

    # Split
    tr_set_1 = sh_weather.iloc[:n_train]
    te_set_1 = sh_weather.iloc[n_train:]

    # Separate based on seasons - NDARRAYS
    tr_win_1 = tr_set_1.loc[tr_set_1["STAGIONE"] == "winter"].drop(columns=["STAGIONE"]).values
    tr_spr_1 = tr_set_1.loc[tr_set_1["STAGIONE"] == "spring"].drop(columns=["STAGIONE"]).values
    tr_sum_1 = tr_set_1.loc[tr_set_1["STAGIONE"] == "summer"].drop(columns=["STAGIONE"]).values
    tr_fal_1 = tr_set_1.loc[tr_set_1["STAGIONE"] == "fall"].drop(columns=["STAGIONE"]).values

    rfc_win_1 = QuadraticDiscriminantAnalysis().fit(tr_win_1[:, :-1], tr_win_1[:, -1])
    rfc_spr_1 = QuadraticDiscriminantAnalysis().fit(tr_spr_1[:, :-1], tr_spr_1[:, -1])
    rfc_sum_1 = QuadraticDiscriminantAnalysis().fit(tr_sum_1[:, :-1], tr_sum_1[:, -1])
    rfc_fal_1 = QuadraticDiscriminantAnalysis().fit(tr_fal_1[:, :-1], tr_fal_1[:, -1])

    models_list_1 = [rfc_win_1, rfc_spr_1, rfc_sum_1, rfc_fal_1]

    te_nd_1 = te_set_1.drop(columns=["STAGIONE", "FENOMENI"]).values

    te_pred_1 = np.zeros((n_test,))
    te_label_1 = te_set_1["FENOMENI"].values
    te_val_1 = te_set_1.drop(columns=["FENOMENI"])

    for i in range(n_test):
        curr_row = te_val_1.iloc[i]

        curr_pred = currWeather(curr_row, models_list_1)
        
        te_pred_1[i] = curr_pred
        
    acc_te_1 = (te_pred_1 == te_label_1).sum()/n_test

    print(f"Accuracy on current values (current weather prediction): {acc_te_1}")

    ##### Alternative model: use the season as an additional feature
    attr_2 = tr_set_1.columns[~(tr_set_1.columns.isin(["FENOMENI"]))]

    tr_set_1a = tr_set_1.copy()

    # Map the month to the season index (need numerical features)
    tr_set_1a["STAGIONE"] = tr_set_1a.loc[:, "STAGIONE"].map(SEASON2INDEX)

    mod_1a = QuadraticDiscriminantAnalysis().fit(tr_set_1a[attr_2].values, tr_set_1a['FENOMENI'].values)

    te_pred_1a = np.zeros((n_test, ))
    te_label_1a = te_set_1["FENOMENI"].values
    te_set_1a = te_set_1.copy()
    te_set_1a["STAGIONE"] = te_set_1a.loc[:, "STAGIONE"].map(SEASON2INDEX)
    print(te_set_1a.columns)
    te_set_1a = te_set_1a[attr_2]

    for i in range(n_test):
        curr_row = te_set_1a.iloc[i]

        curr_pred = currWeather_2(curr_row, mod_1a)
        
        te_pred_1a[i] = curr_pred
        
    acc_te_1a = (te_pred_1a == te_label_1a).sum()/n_test    

    print(f"Accuracy with season as a feature - current weather: {acc_te_1a}")

    ############### Future rain prediction: ##########################################################################################
    # Add 'target' column, to include the label to be predicted - i.e., the next day's precipitations
    # ---> Need to 'fill' the last element, which is NaN
    weather_df["target"] = weather_df.shift(-1)["FENOMENI"].ffill()
    
    # Rearrange column order
    # 'TMEDIA °C', 'TMIN °C', 'TMAX °C', 'UMIDITA %', 'PRESSIONESLM mb', 'FENOMENI', <---> 'STAGIONE', 'target'
    cols = weather_df.columns.tolist()
    cols = cols[:5] + [cols[6]] + [cols[5]] + [cols[7]]
    weather_df = weather_df[cols]

    # Shuffle cols
    sh_weather_2 = weather_df.iloc[sh_range]

    tr_set_2 = sh_weather_2.iloc[:n_train]
    te_set_2 = sh_weather_2.iloc[n_train:]

    # Separate based on seasons - NDARRAYS
    tr_win_2 = tr_set_2.loc[tr_set_2["STAGIONE"] == "winter"].drop(columns=["STAGIONE"]).values
    tr_spr_2 = tr_set_2.loc[tr_set_2["STAGIONE"] == "spring"].drop(columns=["STAGIONE"]).values
    tr_sum_2 = tr_set_2.loc[tr_set_2["STAGIONE"] == "summer"].drop(columns=["STAGIONE"]).values
    tr_fal_2 = tr_set_2.loc[tr_set_2["STAGIONE"] == "fall"].drop(columns=["STAGIONE"]).values

    rfc_win_2 = QuadraticDiscriminantAnalysis().fit(tr_win_2[:, :-1], tr_win_2[:, -1])
    rfc_spr_2 = QuadraticDiscriminantAnalysis().fit(tr_spr_2[:, :-1], tr_spr_2[:, -1])
    rfc_sum_2 = QuadraticDiscriminantAnalysis().fit(tr_sum_2[:, :-1], tr_sum_2[:, -1])
    rfc_fal_2 = QuadraticDiscriminantAnalysis().fit(tr_fal_2[:, :-1], tr_fal_2[:, -1])

    models_list_2 = [rfc_win_2, rfc_spr_2, rfc_sum_2, rfc_fal_2]

    te_pred_2 = np.zeros((n_test, ))
    te_label_2 = te_set_2["target"].values
    te_feat_2 = te_set_2.drop(columns=["target"])

    for i in range(n_test):
        curr_row = te_feat_2.iloc[i]

        curr_pred = futureRain(curr_row, models_list_2)
        
        te_pred_2[i] = curr_pred
        
    acc_te_2 = (te_pred_2 == te_label_2).sum()/n_test

    print(f"Accuracy on current values (future rain forecasting, by season): {acc_te_2}")

    attr_2 = tr_set_2.columns[~(tr_set_2.columns.isin(['target', "STAGIONE"]))]

    # Apply SEASON2INDEX on seasons:
    SEASON2INDEX = {
        'winter': 0,
        'spring': 1,
        'summer': 2,
        'fall': 3
    }

    tr_set_2["STAGIONE_index"] = tr_set_2.loc[:, "STAGIONE"].map(SEASON2INDEX)

    print()

    mod_2 = QuadraticDiscriminantAnalysis().fit(tr_set_2[attr_2].values, tr_set_2['target'].values)

    te_pred_2a = np.zeros((n_test, ))
    te_label_2a = te_label_2.copy()
    te_set_2a = te_set_2.copy()
    te_set_2a["STAGIONE_index"] = te_set_2a.loc[:, "STAGIONE"].map(SEASON2INDEX)
    te_set_2a = te_set_2a[attr_2]

    for i in range(n_test):
        curr_row = te_set_2a.iloc[i]

        curr_pred = futureRain_2(curr_row, mod_2)
        
        te_pred_2a[i] = curr_pred
        
    acc_te_2a = (te_pred_2a == te_label_2a).sum()/n_test    

    print(f"Accuracy with season as a feature - rain forecast: {acc_te_2a}")
