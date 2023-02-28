import numpy as np
import pandas as pd
import random

from sklearn.neural_network import MLPClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import RBF
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis

"""
This program is used to make weather prediction using the sensor data and having
as training set the historical data about the weather
"""

# TODO: use a classifier on the "target" values.
# TODO: try to find a way to only use the seasonal information as training set
# TODO: to perform validation, shuffle the data

## It may be that, by not shuffling, the model can pick up patterns 
# better among the data - will need to check



def bar2mb_sealevel(val_bar):
    """
    (Trivial) conversion from bar to millibar w.r.t. sea level atmospheric pressure
    """
    return (1000*val_bar) - 1013.25


#######################################################################################
# Backtesting

def backtest(weather, model, regressors, start=550, step=90):
    """
    This function is used to perform cross-validation on 
    time series (cannot use future data to predict past one...)
    """
    all_predictions = []

    for i in range(start,  weather.shape[0], step):
        train = weather.iloc[:i, :]
        test = weather.iloc[i:(i+step), :]

        model.fit(train[regressors], train["target"])

        preds = model.predict(test[regressors])

        preds = pd.Series(preds, index=test.index)
        combined = pd.concat([test["target"], preds], axis=1)

        combined.columns = ["actual", "prediction"]
        combined["diff"] = (combined["prediction"] - combined["actual"]).abs()

        all_predictions.append(combined)

    return pd.concat(all_predictions)

# predictions_backtested = backtest(weather_df, rfc, regressors)
# print(predictions_backtested)

# # Accuracy
# miss = predictions_backtested['diff'].sum()/len(predictions_backtested.index)
# acc = 1 - miss

# print("Accuracy (backtesting) with random forest: ", acc)

### COMMENTS
# The accuracy is basically the same for the 2-class classifier, meaning backtesting is not
# fundamental (probably)

### TODO: create one classifier per season
# May need much more data...

"""
winter_df = train_set.loc[weather_df["STAGIONE"] == "winter"]
winter_rfc = QuadraticDiscriminantAnalysis().fit(winter_df[regressors], winter_df["target"])

spring_df = train_set.loc[weather_df["STAGIONE"] == "spring"]
spring_rfc = QuadraticDiscriminantAnalysis().fit(spring_df[regressors], spring_df["target"])

summer_df = train_set.loc[weather_df["STAGIONE"] == "summer"]
summer_rfc = QuadraticDiscriminantAnalysis().fit(summer_df[regressors], summer_df["target"])

fall_df = train_set.loc[weather_df["STAGIONE"] == "fall"]
fall_rfc = QuadraticDiscriminantAnalysis().fit(fall_df[regressors], fall_df["target"])

models_seasons = [winter_rfc, spring_rfc, summer_rfc, fall_rfc]

def testBySeason(test_elem):
    season_test = test_elem["STAGIONE"]
    test_elem = test_elem.drop("STAGIONE")

    if season_test == "winter":
        pred = models_seasons[0].predict(test_elem.values.reshape(1, -1))
    elif season_test == "spring":
        pred = models_seasons[1].predict(test_elem.values.reshape(1, -1))
    elif season_test == "summer":
        pred = models_seasons[2].predict(test_elem.values.reshape(1, -1))
    elif season_test == "fall":
        pred = models_seasons[3].predict(test_elem.values.reshape(1, -1))

    return pred

test_set = test_set.reset_index()

reg_new = weather_df.columns[~weather_df.columns.isin(["target", "LOCALITA"])]

test_set_out = test_set[reg_new].apply(testBySeason, axis=1)

compare = pd.concat([test_set["target"], test_set_out], axis=1)
compare.columns = ["actual", "predicted"]

print(compare)

acc_seasons = (compare["actual"] == compare["predicted"]).sum()/n_test
print(f"Accuracy with seasons: {acc_seasons}")

################################################
# Prediction of instant weather
# Using

"""
##########################################################################

def futureRain(test_measurements, model=None):
    """
    Used to predict, season is a feature - test_measurements is a full DF of all test elements
    """
    
    pred_curr = model.predict(test_measurements)

    pred_curr = pd.Series(pred_curr, index=["predicted"])

    return pred_curr
    
def futureRain_2(test_df, model):
    pass

def currWeather(test_measurements, models_list=None):
    """
    Predict current weather.

    test_measurements: single Index (row) object containing the features: 
    'TMEDIA °C', 'TMIN °C', 'TMAX °C', 'UMIDITA %', 'PRESSIONESLM mb', 
    'FENOMENI', 'STAGIONE'

    Accuracy: 0.821
    """
    curr_szn = test_measurements["STAGIONE"]
    te_actual = test_measurements["FENOMENI"]
    
    test_nd = test_measurements.drop(["STAGIONE", "FENOMENI"]).values.reshape(1, -1)

    if curr_szn == "winter":
        pred_curr = models_list[0].predict(test_nd)
        return pred_curr
    if curr_szn == "spring":
        pred_curr = models_list[1].predict(test_nd)
        return pred_curr
    if curr_szn == "summer":
        pred_curr = models_list[2].predict(test_nd)
        return pred_curr
    if curr_szn == "fall":
        pred_curr = models_list[3].predict(test_nd)
        return pred_curr


##########################################################################

if __name__ == "__main__":
    tr_set_file = "weather_data/weather_train.csv"
    try:
        weather_df = pd.read_csv(tr_set_file)
    except:
        weather_df = pd.read_csv(("weather/" + tr_set_file))

    colnames = weather_df.columns
    print(colnames)

    # 'LOCALITA', 'TMEDIA °C', 'TMIN °C', 'TMAX °C', 'UMIDITA %', 'PRESSIONESLM mb', 'FENOMENI', 'STAGIONE'

    # Count missing values:
    # print("Fraction of missing values: ", weather_df.isnull().sum()/len(weather_df.index))

    # Since few missing, fill them
    weather_df = weather_df.ffill().drop(columns=["LOCALITA"])

    # Stats
    n_tot = len(weather_df.index)
    n_rain = weather_df["FENOMENI"].sum()
    n_no_rain = n_tot - n_rain

    print(f"Number of rain records: {n_rain}\nNumber of no rain: {n_no_rain}")
    print(f"Fraction of no rain: {n_no_rain/n_tot}")
    
    ############### Current weather prediction
    # Predict 'FENOMENI'
    # Based on values of "STAGIONE"

    ### Train/test:
    # Shuffle data:
    sh_range = list(range(len(weather_df.index)))
    random.shuffle(sh_range)

    sh_weather = weather_df.iloc[sh_range]        # SHUFFLED DF

    n_train = round(0.75*n_tot)
    n_test = n_tot - n_train

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

    for i in range(n_test):
        curr_row = te_set_1.iloc[i]

        curr_pred = currWeather(curr_row, models_list_1)
        
        te_pred_1[i] = curr_pred
        
    acc_te_1 = (te_pred_1 == te_label_1).sum()/n_test

    print(f"Accuracy on current values (current weather prediction): {acc_te_1}")


    ############### Future rain prediction:
    # Add 'target' column, to include the label to be predicted - i.e., the next day's precipitations
    # ---> Need to 'fill' the last element, which is NaN
    weather_df["target"] = weather_df.shift(-1)["FENOMENI"].ffill()
    
    # 'LOCALITA', 'TMEDIA °C', 'TMIN °C', 'TMAX °C', 'UMIDITA %', 'PRESSIONESLM mb', 'FENOMENI', 'STAGIONE', 'target'

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

    for i in range(n_test):
        curr_row = te_set_2.iloc[i]

        curr_pred = futureRain(curr_row, models_list_2)
        
        te_pred_2[i] = curr_pred
        
    acc_te_2 = (te_pred_2 == te_label_2).sum()/n_test

    print(f"Accuracy on current values (future rain forecasting, by season): {acc_te_2}")

    attr_2 = tr_set_2.columns[~(tr_set_2.columns.isin('target'))]
    mod_2 = QuadraticDiscriminantAnalysis().fit(tr_set_2[attr_2], tr_set_2['target'])

    
    

