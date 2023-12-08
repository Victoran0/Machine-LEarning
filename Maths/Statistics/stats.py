import statistics as s
from sklearn import datasets
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

my_data = [1, 2, 3, 4, 5, 10, 15, 20, 25, 30,
           35, 100, 200, 300, 2, 3, 2, 2, 2, 2, 2, 2, 2]

print('The mean, Median and Mode are:')
print(s.mean(my_data))
print(s.median(my_data))
print(s.mode(my_data))

print('The Variance and Standard Deviation are:')
print(s.pvariance(my_data))
print(s.stdev(my_data))

iris = datasets.load_iris()
data = pd.DataFrame(iris['data'], columns=[
                    'Petal length', 'Petal Width', 'Sepal Length', 'Sepal Width'])
data['Species'] = iris['target']
data['Species'] = data['Species'].apply(lambda x: iris['target_names'][x])
print(data.describe())

sns.pairplot(data)
plt.show()
# From the plot we can see that there a lot of normal dsitributions in the dataframe, so we can use eour gaussian NB to movoe forward with it etc.
