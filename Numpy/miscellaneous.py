import numpy as np

# LOAD DATA FROM FILE
# load a txt file(tip: enter initiates a new matrix)
# we cna change the delimiter based on how our data is split
data = np.genfromtxt('data.txt', delimiter=',')
# we can change from float type to int type
data = data.astype('int32')
# print(data)


# BOOLEAN MASKING AND ADVANCED INDEXING
# print(data > 50)
# The above returns our data array but with a boolean val that satisfies the given condition
# print(data == 4)
# we can do so many other cool boolean stuffs
# print(data[data > 50])
# The above shows only data elements that satisfies the condition
# The reason why the above work is that we can index with a list in numpy

# indexing with a list in numpy
# a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9])
# print(a[[1, 2, 8]])

# we can perform the boolean mask on  each column to know which columns have ANY val > 50
# print(np.any(data > 50, axis=0))

# also on each row
# print(np.any(data > 50, axis=1))

# Then we have the np all function
# print(np.all(data > 50, axis=0))

# Also using multiple bools
# print((data > 50) & (data < 100))

# then we have the not operator ~
print(~((data > 50) & (data < 100)))
