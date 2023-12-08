import numpy as np

before = np.array([[1, 2, 3, 4], [5, 6, 7, 8]])
# print(before.shape)

# Previously the shape of before was 2 by 4, we can actually give it a reshape as long as the new shape would take the same amount of val before has

after = before.reshape((2, 2, 2))
print(after)
