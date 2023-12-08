import numpy as np
import pandas as pd
import matplotlib.pylab as plt
from sklearn.linear_model import LinearRegression


cars = pd.read_csv('Car_sales.csv')
# print(cars)

# plt.figure(figsize=(16,8))
# plt.scatter(
#     cars['Horsepower'],
#     cars['Price_in_thousands'],
#     c = 'black'
# )


X = cars['Horsepower'].values.reshape(-1,1)
y = cars['Price_in_thousands'].values.reshape(-1,1)

reg = LinearRegression()
reg.fit(X, y)

print(reg.coef_[0][0]) 
print(reg.intercept_[0])

predictions = reg.predict(X)

plt.figure(figsize=(16,8))
plt.scatter(
    cars['Horsepower'],
    cars['Price_in_thousands'],
    c = 'black'
)

plt.plot(
    cars['Horsepower'],
    predictions,
    c = 'blue',
    linewidth=2
)
plt.xlabel("horsepower")
plt.ylabel("price")
plt.show()
