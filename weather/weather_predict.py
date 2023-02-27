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


tr_set_file = "weather_data/weather_train.csv"
try:
    weather_df = pd.read_csv(tr_set_file)
except:
    weather_df = pd.read_csv(("weather/" + tr_set_file))

# Count missing values:
print("Fraction of missing values: ", weather_df.isnull().sum()/len(weather_df.index))

# Since few missing, fill them
weather_df = weather_df.ffill()

# Add 'target' column, to include the label to be predicted - i.e., the next day's precipitations
# ---> Need to 'fill' the last element, which is NaN
weather_df["target"] = weather_df.shift(-1)["FENOMENI"].ffill()
print(weather_df)
print(weather_df.corr())

# Stats
n_tot = len(weather_df.index)
n_rain = weather_df["FENOMENI"].sum()
n_no_rain = n_tot - n_rain

print(f"Number of rain records: {n_rain}\nNumber of no rain: {n_no_rain}")
print(f"Fraction of no rain: {n_no_rain/n_tot}")

#rr = Ridge(alpha=.1)
rfc = KNeighborsClassifier(n_neighbors=20)

# Regressors - labels of the columns used as regressors
regressors = weather_df.columns[~weather_df.columns.isin(["target", "STAGIONE"])]

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

predictions_backtested = backtest(weather_df, rfc, regressors)
print(predictions_backtested)

# Accuracy
miss = predictions_backtested['diff'].sum()/len(predictions_backtested.index)
acc = 1 - miss

print("Accuracy (backtesting) with random forest: ", acc)

#######################################################################################
# Random split:

# Shuffle data:
sh_range = list(range(len(weather_df.index)))
random.shuffle(sh_range)

sh_weather = weather_df.iloc[sh_range]        # SHUFFLED DF

n_elem = len(sh_weather.index)
n_train = round(0.7*n_elem)
n_test = n_elem - n_train

train_set = sh_weather.iloc[:n_train]
test_set = sh_weather[n_train:]

# Check
print(f"\nTot len: {n_elem}\nTr len: {len(train_set.index)}\nTest len: {len(test_set.index)}\n")

rfc.fit(train_set[regressors], train_set["target"])
predict = rfc.predict(test_set[regressors])

# Make result a DF
predict = pd.Series(predict, index=test_set.index)

# Include info about actual classes
out = pd.concat([test_set["target"], predict], axis=1)
out.columns = ["actual", "prediction"]

acc_rfc = (out["actual"] == out["prediction"]).sum()/n_test

print(f"Accuracy - random forest on shuffled data: {acc_rfc}")

### COMMENTS
# The accuracy is basically the same for the 2-class classifier, meaning backtesting is not
# fundamental (probably)

### TODO: create one classifier per season
# May need much more data...



################################################
# Prediction of instant weather
