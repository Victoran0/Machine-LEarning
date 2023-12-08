# %%
import pandas as pd
from sklearn.naive_bayes import MultinomialNB

df = pd.read_csv('golf-dataset.csv').sort_values(by=['Outlook'])

print(df)
# %%
print(df.info())
# Converting our data to categorical data
1
df = df.apply(lambda x: x.astype('category'))

df1 = df.apply(lambda x : x.cat.codes)

# %%
train = df1[:10]
test = df1[-4:]

y_train = train.pop('Play Golf')
x_train = train

y_test = test.pop('Play Golf')
x_test = test

y_test
# %%
model = MultinomialNB()
model_obj = model.fit(x_train, y_train)
# %%

y_out = model.predict(x_test)
# %%
y_out

# %%
# Training and testing accuracy

print('Training Accuracy:', model.score(x_train, y_train))
print('Testing Accuracy:', model.score(x_test, y_test))
# %%
