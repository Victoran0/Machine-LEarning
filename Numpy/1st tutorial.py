import numpy as np
# how to initialize an array using numpy
a = np.array([1, 2, 3])
# print(a)

# a 2d array of float
b = np.array([[9.0, 8.0, 7.0], [6.0, 5.0, 4.0]])
# print(b)

# get dimension of our np array
# print(b.ndim)

# Get shape
# print(a.shape)

# Get Type
# print(b.dtype)

# We can specify what type we want out numpy array to be, e.g
c = np.array([4, 5, 7], dtype='int16')
# print(c.dtype)

# Get size
# print(c.itemsize)

# Get total size (total number of elements)
# print(a.size)


# Get total size (a.size * a.itemsize)
# print(a.nbytes)


# Accessing or changing specific elements, rows, columns etc
d = np.array([[1, 2, 3, 4, 5, 6, 7], [8, 9, 10, 11, 12, 13, 14]])

# Get a specific element [row index, column index], index starts from 0
# print(d[1, 5])
# print(d[1, -2])

# Get a specific row
# print(d[0, :])

# Get a specific column
# print(d[:, -2])

# Getting a little more fancy [startIndex:endIndex:stepSize]
# print(d[0, 1:6:2])

# Changing the element at a particular position
d[1, 5] = 20
# print(d)

# changing a whole row/column
d[:, 2] = [1, 1]
# print(d)

# 3D example
e = np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]])
# print(e)

# Get specific element in 3d (work outside in)
# print(e[0, 0, 0]) which gives 1(the first of the first of the first)
# print(e[1, 1, 0]) which gives 7
# print(e[:, 0, :1])

# replace: it works as long as the new value is in the same dimension
e[:, 1, :] = [[9, 9], [0, 0]]
# print(e)

# Any other number full_like, it takes the same dimension as the referenced np array
# f = np.full(b.shape, 4)
# or
f = np.full_like(b, 4)
# print(f)
