import geopandas as gpd
import pandas as pd
import warnings
import datetime as dt
from datetime import datetime as dt_sub
from attribute_functions import select_optimal_image
import argparse


# parse out arguments
parser = argparse.ArgumentParser()
parser.add_argument('-db', '--day_buffer', type=int, help='number of days before pre-date or after post-date to '
                                                          'inspect for images')
parser.add_argument('-sb', '--spatial_buffer', type=float, help='number of degrees around change polygon that should be'
                                                                ' clear of clouds and included in the image')

args = parser.parse_args()
if args.day_buffer:
    day_buffer = args.day_buffer
else:
    day_buffer = 30
if args.spatial_buffer:
    spatial_buffer = args.spatial_buffer
else:
    spatial_buffer = 0.0001

# variable parameters - weights for image scores and buffers
day_weight = 1
nadir_weight = 1
elev_weight = 1
multi_res_weight = 1
pan_res_weight = 1

# loading change detection polygons and ground truth imagery as geopandas dataframes
changes_json = gpd.read_file('/home/data/change_polygons.geojson')
boundaries = gpd.read_file('/home/data/image_strip_boundaries.geojson')

# sort changes and image boundaries such that the 0 index row is the most recently captured image and subsequent images
# move backwards in time
changes_json.sort_values(by='pre-date', ascending=False, inplace=True)
changes_json = changes_json.reset_index(drop=True)
boundaries.sort_values(by='acq_date', ascending=False, inplace=True)
boundaries = boundaries.reset_index(drop=True)

# parse date string into datetimes for image boundaries
for i, datestr in boundaries.iterrows():
    boundaries.at[i, 'acq_date'] = dt_sub.strptime(datestr['acq_date'], '%Y-%m-%d')

# parse date string into datetimes for change polygons
for i, datestr in changes_json.iterrows():
    changes_json.at[i, 'pre-date'] = dt_sub.strptime(datestr['pre-date'], '%Y%m%d')
    changes_json.at[i, 'post-date'] = dt_sub.strptime(datestr['post-date'], '%Y%m%d')

# initialize dataframes for the final selection of pre and post image boundaries
pre_images = pd.DataFrame(columns=['change_poly_index', 'catalog_id', 'acq_date', 'off_nadir', 'multi_res', 'pan_res'])
post_images = pd.DataFrame(columns=['change_poly_index', 'catalog_id', 'acq_date', 'off_nadir', 'multi_res', 'pan_res'])

# loop through each change polygon by index to identify best images
for change_index in range(len(changes_json)):
    change = changes_json.iloc[change_index]

    # loop through the boundary images starting with the most recent image then backwards in time to find 1) the index
    # of the image closest to but before the pre-change date and 2) the index of the image closest to but not exceeding
    # 30 days of the pre-change date
    post_index_start = None
    post_index_buffer = None
    for img_index, img_date in enumerate(boundaries['acq_date'].values):
        if not post_index_buffer and (img_date <= (change['post-date'] + dt.timedelta(days=day_buffer))) and img_date > change['post-date']:
                post_index_buffer = img_index
        else:
            if post_index_buffer and img_date < change['post-date']:
                post_index_start = img_index - 1
                potential_post_images = list(range(post_index_buffer, post_index_start + 1))
                break
    if not post_index_buffer:
        warnings.warn('no acceptable post-change image found')
        potential_post_images = []

    # loop through the boundary images starting with the most recent image then backwards in time to find 1) the index
    # of the image closest to but before the post-change date and 2) the index of the image closest to but not exceeding
    # 30 days of the pre-change date
    pre_index_start = None
    pre_index_buffer = len(boundaries['acq_date'].values[post_index_start:])
    for img_index, img_date in enumerate(boundaries['acq_date'].values):
        if not pre_index_start and (img_date <= change['pre-date']) and img_date > (change['pre-date'] - dt.timedelta(days=day_buffer)):
                pre_index_start = img_index
        else:
            if pre_index_start and img_date < (change['pre-date'] - dt.timedelta(days=day_buffer)):
                pre_index_buffer = img_index - 1
                potential_pre_images = list(range(pre_index_start, pre_index_buffer + 1))
                break
    if not pre_index_start:
        warnings.warn('no acceptable pre-change image found within date buffer for change polygon')
        potential_pre_images = []

    # create a list of potential pre images and post images separated in the list by the place holder -999
    potential_images = potential_post_images + [-999] + potential_pre_images

    print('image indices within date range: ', potential_images)
    for x in potential_images:
        if x != -999:
            print(boundaries.iloc[x]['acq_date'])

    # eliminate images with conditions of probable glare
    for image_index in reversed(potential_images):
        if image_index == -999:
            continue
        if abs(boundaries.iloc[image_index]['sun_elev'] - boundaries.iloc[image_index]['off_nadir']) < 5 and \
                abs(boundaries.iloc[image_index]['sun_azim'] - boundaries.iloc[image_index]['target_az']) < 5:
            potential_images.remove(image_index)
            print('image removed due to glare')

    # ensure that change polygon is included in image; check for cloud cover
    for image_index in reversed(potential_images):
        if image_index == -999:
            continue
        change_poly = change['geometry'].buffer(spatial_buffer)
        image_poly = boundaries.iloc[image_index]['geometry']
        if change_poly.within(image_poly):
            clouds = gpd.read_file('home/data/cloud_masks/' + boundaries.iloc[image_index]['catalog_id']
                                   + '.geojson')
            for cloud_poly in clouds['geometry']:
                # checking if cloud list is empty
                if cloud_poly != None and change_poly.within(cloud_poly):
                    print('image removed due to cloud cover')
                    potential_images.remove(image_index)
                    break
        else:
            potential_images.remove(image_index)

    # convert list of potential images into two lists of pre images and post images
    potential_post_images = potential_images[:potential_images.index(-999)]
    potential_pre_images = potential_images[(potential_images.index(-999)+1):]
    print('post images ', potential_post_images, 'length', len(potential_post_images))
    print('pre images ', potential_pre_images, 'length', len(potential_pre_images))

    # check if there is only 1 acceptable image; if so start populating the final images
    if len(potential_post_images) == 1:
        post_final = potential_post_images
        print('post image assigned')
    elif len(potential_post_images) == 0:
        warnings.warn('No adequate post-change image found for change polygon')
        post_final = [None]
    elif len(potential_post_images) > 1:
        post_final = select_optimal_image(potential_post_images, boundaries, change,
                                          day_weight=day_weight, nadir_weight=nadir_weight, elev_weight=elev_weight,
                                          multi_res_weight=multi_res_weight, pan_res_weight=pan_res_weight, type='post',
                                          day_buffer=day_buffer)
    else:
        print('something is off kilter')

    if len(potential_pre_images) == 1:
        pre_final = potential_pre_images
    elif len(potential_pre_images) == 0:
        warnings.warn('No adequate pre-change image found for change polygon')
        pre_final = [None]
        print('pre image assigned')
    elif len(potential_pre_images) > 1:
        # if there is more than one potential image remaining look at important attributes and select the best image
        pre_final = select_optimal_image(potential_pre_images, boundaries, change,
                                         day_weight=day_weight, nadir_weight=nadir_weight, elev_weight=elev_weight,
                                         multi_res_weight=multi_res_weight, pan_res_weight=pan_res_weight, type='pre',
                                         day_buffer=day_buffer)
    else:
        print('something is off kilter')

    print('pre final ', pre_final, 'post final ', post_final, 'got to line 154')
    # create output pandas dataframes for pre images and post images
    if pre_final[0] is not None:
        print('writing full data')
        pre_images = pre_images.append(boundaries.iloc[pre_final][['catalog_id', 'acq_date', 'off_nadir', 'multi_res',
                                                                   'pan_res']], ignore_index=True)
        pre_images.at[change_index, 'change_poly_index'] = change_index
    else:
        print('writing null pre data', change_index)
        null_data = {'change_poly_index': [change_index], 'catalog_id': [None], 'acq_date':
            [None], 'off_nadir': [None], 'multi_res': [None], 'pan_res': [None]}
        pre_images = pre_images.append(pd.DataFrame(data=null_data))

    if post_final[0] is not None:
        print('writing full data')
        post_images = post_images.append(boundaries.iloc[post_final][['catalog_id', 'acq_date', 'off_nadir', 'multi_res',
                                                                      'pan_res']], ignore_index=True)
        post_images.at[change_index, 'change_poly_index'] = change_index
    else:
        print('writing null post data', change_index)
        null_data = {'change_poly_index': [change_index], 'catalog_id': [None], 'acq_date':
            [None], 'off_nadir': [None], 'multi_res': [None], 'pan_res': [None]}
        post_images = post_images.append(pd.DataFrame(data=null_data))

    print('FINISHED ONE IMAGE', len(pre_images), len(post_images))

# convert to geojsons and save
with open('/home/output/pre_images.json', 'w') as f:
    f.write(pre_images.to_json(orient='records', lines=True))

with open('/home/output/post_images.json', 'w') as f:
    f.write(post_images.to_json(orient='records', lines=True))
print('save complete')
