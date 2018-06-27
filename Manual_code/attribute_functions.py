import math
import operator
import warnings


# the four functions describing the optimal values of the attributes used to score the images
def day(x, day_buffer):
    if x < 0 or x > day_buffer:
        raise RuntimeWarning('day out of bounds 0-30 days')
    else:
        return -1/day_buffer*x + 1


def nadir(x):
    if x < 0 or x > 80:
        raise RuntimeWarning('nadir out of bounds 0-80 degrees')
    else:
        return math.exp(-.5*((x-35)/13.33)**2)


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


# this function looks at each of the images, scores it, and outputs a list with the index of the 1 best image
def select_optimal_image(images_to_score, boundary_image, change, **kwargs):
    scores = {}
    for image_index in images_to_score:
        if kwargs['type'] == 'pre':
            time_delta = change['pre-date'] - boundary_image.iloc[image_index]['acq_date']
        elif kwargs['type'] == 'post':
            time_delta = boundary_image.iloc[image_index]['acq_date'] - change['post-date']
        else:
            warnings.warn("select_optimal_images must include keyword 'type' = 'pre', or 'post'")
        score = kwargs['day_weight']*day(time_delta.days, kwargs['day_buffer']) + \
                kwargs['nadir_weight']*nadir(boundary_image.iloc[image_index]['off_nadir'] +
                kwargs['elev_weight']*elevation(boundary_image.iloc[image_index]['sun_elev']) +
                kwargs['multi_res_weight']*resolution(boundary_image.iloc[image_index]['multi_res']) +
                kwargs['pan_res_weight']*resolution(boundary_image.iloc[image_index]['pan_res']))
        scores[image_index] = score
    best_image = max(scores.items(), key=operator.itemgetter(1))[0]
    return [best_image]
