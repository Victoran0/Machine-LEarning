import numpy as np
# Read the numpy documentation https://numpy.org/doc/stable/reference/routines.array-creation.html

# All 0s matrix, 1D
a = np.zeros(5)
# print(a)

# all zeros 2D
b = np.zeros((2, 3))
# print(a)

# all zeros 3D
c = np.zeros((2, 3, 3))
# print(a)

# all zeros 4D
d = np.zeros((2, 3, 3, 2))
# print(a)

# All ones matrix
e = np.ones((4, 2, 2), dtype='int32')
# print(a)

# Any other number
f = np.full((2, 2), 99, dtype="float32")
# print(a)

# random decimal numbers
g = np.random.rand(4, 2, 3)
# print(g)

# if we want to pass in shape in random decimals, we can use random_sample
h = np.random.random_sample(a.shape)
# print(h)

# Random integer values, the first arg is the start val which is 0 at default, second is end val, if only first arg, then it takes it as end val, second is the size
# i = np.random.randint(7, size=(3, 3))
i = np.random.randint(-4, 7, size=(3, 3))
# print(i)

# identity matrix (by its nature is going to be a square matrix)
j = np.identity(3)
# print(j)

# We can repeat an array, the axis we can use should be less than the dimension of the array and the higher the axis, the lesser the dimension of the array by 1, also second argument is how many times to repeat the array
arr = np.array([[1, 2, 3]])
r1 = np.repeat(arr, 3, axis=0)
# print(r1)

output = np.ones((5, 5))
output[1:4, 1:-1] = np.zeros((3, 3))
output[2, 2] = 9
# print(output)

# Be careful when copying arrays
k = np.array([1, 2, 3])
# l = k
l = k.copy()
l[0] = 100
# changing l changes k
# but using the .copy() function stops that.
# print(k, l)
