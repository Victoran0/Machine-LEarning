import numpy as np

# Dimensions are important in variaverticalble stack as well

v1 = np.array([1, 2, 3, 4])
v2 = np.array([5, 6, 7, 8])

# if we want to stack v1 on top of v2 to form a new array, we can use the syntax below and arrays we are trying to stack together should have the same vertical shape/size
# print(np.vstack([v1, v2]))

# With the vstack function, we can even make multiple stacks using previous np arrays,  see below:
# print(np.vstack([v1, v2, v1]))


# Horizontal stack
h1 = np.ones((2, 4))
h2 = np.zeros((2, 2))
# We can stack the above np arrays using the hstack if the arrays have the same horizontal  size/shape
print(np.hstack((h1, h2)))
# and we can see that the zeros would be to the right of the ones
