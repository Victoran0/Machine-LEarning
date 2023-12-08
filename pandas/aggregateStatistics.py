# AGGREGATE STATISTICS (Groupby)
import pandas as pd

df = pd.read_csv('pokemon_data.csv')
# print(df.head())


# We can get the mean of our data, we have to pass in the numeric_only argument so it does not deal with string columns for this dataframe
# grouped = df.groupby(['Type 1'])
# print(grouped.mean(numeric_only=True).sort_values('HP', ascending=False))

# We can sum up by the groups also
# print(grouped.sum(numeric_only=True))

# We also have a .coount() function which gives the amount of time items in the group have occured
# print(grouped.count())

# We can also make the count simple and ignore recurring data, so we initiate a new count column and get only that column
# df['count'] = 1
# We can also  group by multiple types
# print(df.groupby(['Type 1', 'Type 2']).count()['count'])


# WORKING WITH LARGE AMOUNTS OF DATA
# Chunksize: it can help saving errors if we have a lot of datasef and just want a bit of it. The chunk size would load the dataframe in chunk of tehe amount specified
# new_df = pd.DataFrame(columns=df.columns)

# for df in pd.read_csv('modified.csv', chunksize=5):
#     results = df.groupby(['Type 1']).count()

#     new_df = pd.concat([new_df, results])

df2 = df.groupby(['Type 1'])
print(df2.first)
