import numpy


def sigmoid(sop):
    return 1.0 / (1 + numpy.exp(-1 * sop))  # (1/(1+e^-sop))


def error(predicted, target):
    return numpy.power(predicted - target, 2)  # (pred-tar)^2 or x^2


def error_predicted_deriv(predicted, target):
    return 2 * (predicted - target)  # 2*(pred-tar) or  2x


def activation_sop_deriv(sop):
    return sigmoid(sop) * (1.0 - sigmoid(sop))  # actual function


def sop_w_deriv(x):
    return x


def update_w(w, grad, learning_rate):
    return w - learning_rate * grad  # update the weight


x = 0.1
target = 0.3
learning_rate = 0.01
w = numpy.random.rand()
print('initial W : ', w)

for k in range(10000):
    # Forward pass
    y = w * x
    predicted = sigmoid(y)
    err = error(predicted, target)

    # Backward Pass
    g1 = error_predicted_deriv(predicted, target)
    g2 = activation_sop_deriv(predicted)
    g3 = sop_w_deriv(x)

    grad = g3 * g2 * g1
    print(predicted)

    w = update_w(w, grad, learning_rate)

# The more the iterations k, the closer we can be to our target
# THis is how gradient descent works in helping our machine learn, it uses differentiation and derivation, (we have 2 deriv functions) and we use our error functions to adjust our weight so we can get closer to our desired output
