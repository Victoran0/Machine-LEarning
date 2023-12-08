import numpy as np

a = np.ones((2, 3))
b = np.full((3, 2), 2)

# multiplying a and b which result in a 2 by 2 matrix whcih is theyr compatible row and column
c = np.matmul(a, b)
# print(c)

# getting the determinant of a matrix
d = np.identity(3)
print(np.linalg.det(d))


# There are so much linear algebra we can do with numpy, Trace, Singular vector decomposition, Eigen values, Matrix Norm, inverse etc, we can check the numpy.org documentation for these functions
