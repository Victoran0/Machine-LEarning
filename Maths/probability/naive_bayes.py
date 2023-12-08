from sklearn import datasets
from sklearn import metrics

# Gaussian naive Bayes Classifier
from sklearn.naive_bayes import GaussianNB

dataset = datasets.load_iris()
model = GaussianNB()

model.fit(dataset.data, dataset.target)
expected = dataset.target

predicted = model.predict(dataset.data)

print(metrics.classification_report(expected, predicted))

print(metrics.confusion_matrix(expected, predicted))

# [[50  0  0]
#  [ 0 47  3]
#  [ 0  3 47]]
# The above result of the confusion matrix means that at first, 50 were classified and none were wrong, the next 50, 47 was right and 3 was wrong same for the next.
