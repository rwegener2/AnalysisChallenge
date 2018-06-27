import math


def day(x):
    if x < 0 or x > 30:
        raise RuntimeWarning('day out of bounds 0-30 days')
    else:
        return -1/30*x + 1


def nadir(x):
    if x < 0 or x > 80:
        raise RuntimeWarning('nadir out of bounds 0-80 degrees')
    else:
        return math.exp(-.5*((x-40)/13.33)**2)


def elevation(x):
    if x < 0 or x > 90:
        raise RuntimeWarning('elevation out of bounds 0-90 degrees')
    elif x < 10:
        return 1/20*x + 0.5
    elif x >= 10:
        return -1/80*x + 9/8


def resolution(x):
    if x == 0:
        return 0
    else:
        return 1/(x+1)
