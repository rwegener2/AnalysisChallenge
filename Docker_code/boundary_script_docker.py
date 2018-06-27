import geopandas as gpd
import operator
import pandas as pd
from attribute_functions import *


# loading and sorting
change_json = gpd.read_file('/home/data/change_polygons.geojson')
boundaries = gpd.read_file('/home/data/image_strip_boundaries.geojson')
change_json.sort_values(by='pre-date', ascending=False, inplace=True)
boundaries.sort_values(by='acq_date', ascending=False, inplace=True)

from datetime import datetime
# parse datetimes for image boundaries
for i, datestr in boundaries.iterrows():
    new_datestr = datetime.strptime(datestr['acq_date'], '%Y-%m-%d')
    boundaries.at[i, 'acq_date'] = new_datestr

# parse datetimes for change polygons
for i, datestr in change_json.iterrows():
    new_datestr_pre = datetime.strptime(datestr['pre-date'], '%Y%m%d')
    new_datestr_post = datetime.strptime(datestr['post-date'], '%Y%m%d')
    change_json.at[i, 'pre-date'] = new_datestr_pre
    change_json.at[i, 'post-date'] = new_datestr_post

import datetime
# initialize bookend image dataframes
pre_images = pd.DataFrame(columns=['change_poly_index', 'catalog_id', 'acq_date', 'off_nadir', 'multi_res', 'pan_res'])
post_images = pd.DataFrame(columns=['change_poly_index', 'catalog_id', 'acq_date', 'off_nadir', 'multi_res', 'pan_res'])
# loop through change polygons to locate best images
for change_index in range(len(change_json)):
    change = change_json.iloc[change_index]
    # select images within the optimal date range
    pre_index_start = 999999
    pre_index_end = 999999
    pre_date = change['pre-date']
    for index, img_date in enumerate(boundaries['acq_date'].values):
        # comment some of this else if madness
        if pre_index_start == 999999:
            if img_date <= pre_date:
                pre_index_start = index
        else:
            if img_date < pre_date - datetime.timedelta(days=30):
                pre_index_end = index - 1
        if pre_index_end != 999999:
            break
        if index == len(boundaries['acq_date'].values):
            pre_index_end = index

    post_index_start = 999999
    post_index_end = 999999
    post_date = change['post-date']
    for index, img_date in reversed(list(enumerate(boundaries['acq_date'].values[:pre_index_start]))):
        if post_index_start == 999999:
            if img_date >= post_date:
                post_index_start = index
        else:
            if img_date > post_date + datetime.timedelta(days=30):
                post_index_end = index + 1
        if post_index_end != 999999:
            break
        if index == 0:
            post_index_end = 0

    print('pre', pre_index_start, pre_index_end, 'post ', post_index_start, post_index_end)
    potential_images = list(range(post_index_end, post_index_start + 1)) + [-999] + list(range(pre_index_start,
                                                                                               pre_index_end + 1))

    # eliminate poor attributes - glare
    for image_index in reversed(potential_images):
        if image_index == -999:
            continue
        if abs(boundaries.iloc[image_index]['sun_elev'] - boundaries.iloc[image_index]['off_nadir']) < 5 and \
                abs(boundaries.iloc[image_index]['sun_azim'] - boundaries.iloc[image_index]['target_az']) < 5:
            potential_images.remove(image_index)
            print('image removed due to glare')

    # ensure that change polygon is included in image and check for cloud cover
    for image_index in reversed(potential_images):
        if image_index == -999:
            continue
        delta_poly = change['geometry'].buffer(0.0001)
        image_poly = boundaries.iloc[image_index]['geometry']
        print('image intersection', delta_poly.within(image_poly))
        if delta_poly.within(image_poly):
            clouds = gpd.read_file('/home/data/cloud_masks/' + boundaries.iloc[image_index]['catalog_id'] + '.geojson')
            for cloud_poly in clouds['geometry']:
                if cloud_poly == None:
                    continue
                if delta_poly.within(cloud_poly):
                    print('cloud cover found for ', cloud_poly)
                    potential_images.remove(image_index)
        else:
            potential_images.remove(image_index)

    # classifying remaining images
    pre_final = None
    post_final = None
    pre_flag = 0
    # check for lone images
    if potential_images.index(-999) == 1:
        post_final = potential_images[0]
        potential_images.pop(0)
    elif potential_images.index(-999) == len(potential_images) - 1:
        pre_final = potential_images[-1]
        potential_images.pop(-1)
    elif potential_images.index(-999) == 0:
        raise RuntimeWarning('No adequate pre-change image found for change of index ', change_index)
    elif potential_images.index(-999) == len(potential_images):
        raise RuntimeWarning('No adequate post-change image found for change of index ', change_index)

    # determine pre image
    pre_scores = {}
    for image_index in potential_images[(potential_images.index(-999)+1):]:
        time_delta = pre_date - boundaries.iloc[image_index]['acq_date']
        image_score = day(time_delta.days) + nadir(boundaries.iloc[image_index]['off_nadir'] +
                                                   elevation(boundaries.iloc[image_index]['sun_elev']) +
                                                   resolution(boundaries.iloc[image_index]['multi_res']) +
                                                   resolution(boundaries.iloc[image_index]['pan_res']))
        pre_scores[image_index] = image_score
    if len(pre_scores) > 1:
        pre_final = max(pre_scores.items(), key=operator.itemgetter(1))[0]  # review this later

    # determine post image
    post_scores = {}
    for image_index in potential_images[:potential_images.index(-999)]:
        print(image_index)
        time_delta = boundaries.iloc[image_index]['acq_date'] - post_date
        print(time_delta.days)
        image_score = day(time_delta.days) + nadir(boundaries.iloc[image_index]['off_nadir'] +
                                                   elevation(boundaries.iloc[image_index]['sun_elev']) +
                                                   resolution(boundaries.iloc[image_index]['multi_res']) +
                                                   resolution(boundaries.iloc[image_index]['pan_res']))
        post_scores[image_index] = image_score
    if len(post_scores) > 1:
        post_final = max(post_scores.items(), key=operator.itemgetter(1))[0]  # review this later

    # create output pandas dataframes
    pre_images = pre_images.append(boundaries.iloc[pre_final][['catalog_id', 'acq_date', 'off_nadir', 'multi_res',
                                                               'pan_res']], ignore_index=True)
    pre_images.at[change_index, 'change_poly_index'] = change_index

    post_images = post_images.append(boundaries.iloc[post_final][['catalog_id', 'acq_date', 'off_nadir', 'multi_res',
                                                                  'pan_res']], ignore_index=True)
    post_images.at[change_index, 'change_poly_index'] = change_index


# convert to geojson and save
with open('/home/output/pre_images.json', 'w') as f:
    f.write(pre_images.to_json(orient='records', lines=True))
