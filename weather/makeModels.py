import numpy as np
import pandas as pd
import random
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
import pickle
import sys

from weather_predict import COLS_CURRENT, COLS_FUTURE, SEASON2INDEX


# User can insert path to data and output models
if len(sys.argv) == 1:
    tr_set_file = "weather_data/weather_train.csv"
    model_today = "models/weather_today.sav"
    model_tomorrow = "models/rain_tomorrow.sav"
elif len(sys.argv) == 2:
    tr_set_file = sys.argv[1]
    model_today = "models/weather_today.sav"
    model_tomorrow = "models/rain_tomorrow.sav"
elif len(sys.argv) == 4:
    tr_set_file = sys.argv[1]
    model_today = sys.argv[2]
    model_tomorrow = sys.argv[3]

try:
    weather_df = pd.read_csv(tr_set_file)
except:
    weather_df = pd.read_csv(("weather/" + tr_set_file))

# Fill dataframe - easy way to deal with missing values 
# (if few, else it may be problematic)
weather_df = weather_df.ffill()

############################################
# 1 - Current day weather prediction model #
############################################

# Only keep relevant columns:
# 'TMEDIA °C', 'TMIN °C', 'TMAX °C', 'UMIDITA %', 'PRESSIONESLM mb', 'STAGIONE'
training_features_1 = weather_df[COLS_CURRENT]
training_features_1["STAGIONE"] = training_features_1.loc[:, "STAGIONE"].map(SEASON2INDEX)
training_labels_1 = weather_df["FENOMENI"]

print(f"\n##################################################\nFeatures - current weather estimation: {training_features_1.columns.to_list()}\n##################################################\n")

model_1 = QuadraticDiscriminantAnalysis().fit(training_features_1.values, training_labels_1.values)

# TODO: make models for different seasons - in this case they have been 
# observed to work better


#########################################
# 2 - Next day weather prediction model #
#########################################

training_features_2 = weather_df[COLS_CURRENT]
training_features_2["STAGIONE"] = training_features_2.loc[:, "STAGIONE"].map(SEASON2INDEX)
training_features_2["FENOMENI"] = weather_df["FENOMENI"]
features_2_slide = training_features_2.copy()
features_2_slide["TARGET"] = features_2_slide.shift(-1)["FENOMENI"].ffill()
training_labels_2 = features_2_slide["TARGET"]

print(training_features_2)
print(training_labels_2)

assert ((training_features_2["STAGIONE"] != 0).sum() > 0), "All winter"

print(f"\n##################################################\nFeatures - rain prediction: {training_features_2.columns.to_list()}\n##################################################\n")

assert (training_features_2.values.shape[1] == 7), f"Not 7 elements - {training_features_2.values.shape[1]}"

model_2 = QuadraticDiscriminantAnalysis().fit(training_features_2.values, training_labels_2.values)

######### Save models ####################################
pickle.dump(model_1, open(model_today, 'wb'))
pickle.dump(model_2, open(model_tomorrow, 'wb'))
