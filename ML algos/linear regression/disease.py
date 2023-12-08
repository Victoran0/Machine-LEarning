import matplotlib.pyplot as plt
import numpy as np
from sklearn import datasets, linear_model
from sklearn.metrics import mean_squared_error


disease = datasets.load_diabetes()

# print(disease)
disease_X = disease.data[:, np.newaxis, 2]
disease_Y = disease.target

disease_X_train = disease_X[:-30]
disease_X_test = disease_X[-20:]

disease_y_train = disease_Y[:-30]
disease_y_test = disease_Y[-20:]

reg = linear_model.LinearRegression()
reg.fit(disease_X_train, disease_y_train)

y_predict = reg.predict(disease_X_test)

accuracy = mean_squared_error(disease_y_test, y_predict)

# print('accuracy:', accuracy)

weights = reg.coef_
intercept = reg.intercept_

# print('weights:', weights, '\n intercept:',intercept)

plt.scatter(disease_X_test, disease_y_test)
plt.plot(disease_X_test, y_predict)
plt.show() 


