import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression


def marks_prediction(hrs):
    X = pd.read_csv('Linear_X_Train.csv')
    y = pd.read_csv('Linear_Y_Train.csv')

    X = X.values
    y = y.values

    model = LinearRegression()
    model.fit(X, y)

    # We can not predict with a scalar, i.e a regular 2, we have to make it a  vector ( a vector is a 1-D numpy array)
    X_test = np.array(hrs)
    X_test = X_test.reshape(1, -1)

    return model.predict(X_test)
