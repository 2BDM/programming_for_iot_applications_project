import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestClassifier

"""
This program is used to make weather prediction using the sensor data and having
as training set the historical data about the weather
"""

tr_set_file = "weather_data/weather_train.csv"
weather_df = pd.read_csv(tr_set_file)

# Count missing values:
print("Fraction of missing values: ", weather_df.isnull().sum()/len(weather_df.index))

# Since few missing, fill them
weather_df = weather_df.ffill()

# Add 'target' column, to include the label to be predicted - i.e., the next day's precipitations
# ---> Need to 'fill' the last element, which is NaN
weather_df["target"] = weather_df.shift(-1)["FENOMENI"].ffill()
print(weather_df)
print(weather_df.corr())

#rr = Ridge(alpha=.1)
rr = RandomForestClassifier()

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

predictions_backtested = backtest(weather_df, rr, regressors)

print(predictions_backtested)

# TODO: use a classifier on the "target" values.
# TODO: try to find a way to only use the seasonal information as training set
# TODO: to perform validation, shuffle the data

## It may be that, by not shuffling, the model can pick up patterns 
# better among the data - will need to check

# Accuracy
miss = predictions_backtested['diff'].sum()/len(predictions_backtested.index)
acc = 1 - miss

print("Accuracy (backtesting): ", acc)

#######################################################################################
# Random split:

# Shuffle data:

