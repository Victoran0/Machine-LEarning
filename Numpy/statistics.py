import numpy as np

stats = np.array([[1, 2, 3], [4, 5, 6]])

# Getting the minimum val of a np array
# print(np.min(stats))

# Getting the max val of a np array
# print(np.max(stats))

# We can  also perform this actions depending on the role, which gives us the minimum of both rows
# print(np.min(stats, axis=1))

# we can also get the max of all columns by setting the axis to 0
# print(np.max(stats, axis=0))

# We can sum up all the values in the matrix
# print(np.sum(stats))

# Also we can find the sum row and column wise
# print(np.sum(stats, axis=1))
