# Why pandas?
# 1. flexibility in python
# 2. Working with big data 
# The docs  http://pandas.pydata.org/pandas-docs/

import pandas as pd
import re

df = pd.read_csv('pokemon_data.csv')
# print(df)

# if we do not want to print the full data frame of our csv file, we can specify the amount oc row we want from the top using the syntax
# print(df.head(3))

# Also reading the bottom 3 rows, we can do
# print(df.tail(3))

# If we want to read our .csv file but it is in a non .csv file attr, we can simply use the beliw syntax
# df_xlsx = pd.read_excel('pokemon_data.xlsx')
# print(df_xlsx.head(3))

# df_txt = pd.read_csv('pokemon_data.txt', delimiter='\t')
# print(df_txt.head(5))



# READING DATA IN PANDAS
# Read headers
# print(df.columns)

# Read a specific column
# print(df['Name'])

# we can also specify that we want only a certain portion of it
# print(df['Name'][0:5])

# We can also get multiple columns at the same time
# print(df[["Name", 'Type 1', 'HP']])

# The easiest way to print out each row is, the iloc stands for integer location
# print(df.iloc[1])

# To get multiple rows, we can do:
# print(df.iloc[1:4])

# The same iloc function can be sued to grab specific location (R, C)
# print(df.iloc[2,1])

# To iterate through each row in the dataset, we can do:
# for index, row in df.iterrows():
    # print(index, row)

# We  can also specify that we only want a certain portion of it with respect to a particular column
# for index, row in df.iterrows():
    # print(index, row["Name"])


# To find a specific data in our dataset, we can use the df.loc
# print(df.loc[df['Type 1'] == 'Fire']) 
# print(df.loc[df['Type 1'] == 'Grass']) 
# And with this this we can use different syntaxes to get different data.

# We can use the .describe() method which can give us alll the high level like the mean, standard deviation, stats etc
# print(df.describe())

# We can do some sorting of the value using the sort_values and it takes a second argument which is ascending=bool
# print(df.sort_values("Name"))
# print(df.sort_values("Name", ascending=False))
# And we also can combine multiple columns in this, e.g:
# print(df.sort_values(['Type 1', 'HP'])) 
# print(df.sort_values(['Type 1', 'HP'], ascending=False))
# And we can  specify different ascending values when we have multiple columns to sort, 1 for true and 0 for false
# print(df.sort_values(['Type 1', 'HP'], ascending=[1, 0])) also means the below
# print(df.sort_values(['Type 1', 'HP'], ascending=[True, False]))



# MAKE CHANGES TO THE DATA 
# We can create a new column to our data by the below:
# df['Total'] = df['HP'] + df['Attack'] + df['Defense'] + df['Sp. Atk'] + df['Sp. Def'] + df['Speed']
# when performing an algorithm like this, we should check that it is actually correct
# print(45+49+49+65+65+45)
# print(df.head(1))

#  the df['total'] defined above, , it we want to remove such from it, we can use the beloe syntax:
# print(df.drop(columns=['Total']))

# We can also declare a new column by using the syntax below:
df['Total'] = df.iloc[:, 4:10].sum(axis=1)
# so we want to get all the rows and only from the 4th column to the 9th column, then we can use the .sum function then we specify axis=1 so we add horizontally, if we did axis = 0, then we are adding vertically
# print(45+49+49+65+65+45)
# print(df)

# Now, we may want to change the column index of total and maybe set it in another position, we can do the below syntax i.e changing the order of our columns, so redefine df
cols = list(df.columns.values)
df = df[cols[0:4] + [cols[-1]] + cols[4:12]]
# print(df.head(5))

# We can now save our csv 
# df.to_csv('modified.csv')

# If we want to remove the indexes in our data, we can use the second arg index=False
# df.to_csv('modified.csv', index=False)

# There is also a to_excel function
# df.to_excel('modified.xlsx', index=False)

# When saving to a non csv or excel file, we have to enter the 3rd arg which is the sep`, from the below we seperate with \t which means tabs intead of comas`
# df.to_csv('modified.txt', index=False, sep='\t')



# FILTERING DATA 
# we can perform multiple operations, for and, we use the & and for or, we use the |
# print(df.loc[(df['Type 1'] == 'Grass') & (df['Type 2'] == 'Poison')])

# using the or | operator
# print(df.loc[(df['Type 1'] == 'Grass') | (df['Type 2'] == 'Poison')])

# print(df.loc[(df['Type 1'] == 'Grass') & (df['Type 2'] == 'Poison') & (df['HP'] > 70)])

# new_df = df.loc[(df['Type 1'] == 'Grass') & (df['Type 2'] == 'Poison') & (df['HP'] > 70)]
# print(new_df)

# When we filter our data, it still retain the same index, so we have to reset the index and to remove the old index, we can use the arg drop=True: and also the inplace arg which conserves a lil bit of memory
# new_df = new_df.reset_index(drop=True)
# new_df.to_csv('filtered.csv')

# new_df.reset_index(drop=True, inplace=True)
# print(new_df)

# If we want to filter by the name of a particular datum in out data frame, we can use the contains by first getting the string property of the selected column, see below example:
# print(df.loc[df['Name'].str.contains('Mega')])

# And to get the reverse of the above, the ~ operator
# print(df.loc[~df['Name'].str.contains('Mega')])

# We can also filter by regular expression, i.e import re which is regex, regex | means or. and regex ia also case sensitive
# print(df.loc[df['Type 1'].str.contains('Fire|Grass', regex=True)])

# We can also ignore case sensitivity by using the flags=re.I argument
# print(df.loc[df['Type 1'].str.contains('fire|grass', flags=re.I, regex=True)])

# To check if a particular element starts with a particular string, for example, a name starts with pi, where ^ means start of line and [a-z means the next letters are either in that alphabet range] and * means any other concat at the end of it.
# print(df.loc[df['Name'].str.contains('^pi[a-z]*', flags=re.I, regex=True)])



# CONDITIONAL CHANGES
# Imagine if we want to change Fire in Type 1 column to flamer
# df.loc[df['Type 1'] == 'Fire', 'Type 1'] = 'Flamer'
# print(df)

# We  can also change other columns/characteristics of this selected elements
# df.loc[df['Type 1'] == 'Fire', 'Legendary'] = True 
# print(df.head(10))

# To modify multiple conditions at the same time, we can pass in a ist, gen, leg e.g:
# df.loc[df['Total'] > 500, ['Generarion', 'Legendary']] = 'TEST VALUE'
# print(df)

# We can modify them individually also by passing their new values in a list also
# df.loc[df['Total'] > 500, ['Generation', 'Legendary']] = ['Test 1', 'Test 2']
# print(df)




