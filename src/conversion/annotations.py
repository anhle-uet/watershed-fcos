"""Annotations

Produces COCO compatible annotations for the DeepScores dataset.

References:
    Binary mask to RLE encoding implementation from
    <https://github.com/waspinator/pycococreator/>, licensed under the Apache
    License 2.0. No changes were made.

Author:
    Yvan Satyawan <y_satyawan@hotmail.com>

Created on:
    November 18, 2019
"""
from xml.etree import ElementTree as ET
from os import listdir
from os.path import join
import numpy as np
from PIL import Image
from math import floor, ceil
from itertools import groupby


def binary_mask_to_rle(binary_mask):
    rle = {'counts': [], 'size': list(binary_mask.shape)}
    counts = rle.get('counts')
    for i, (value, elements) in enumerate(groupby(
            binary_mask.ravel(order='F'))):
        if i == 0 and value == 1:
                counts.append(0)
        counts.append(len(list(elements)))

    return rle


def extract_area_inside_bbox(bbox: list,
                             segmentation_mask: np.ndarray) -> np.ndarray:
    """Extracts just the area inside the bounding box from the seg mask."""
    xmin = floor(bbox[0])
    ymin = floor(bbox[1])
    xmax = ceil((bbox[0] + bbox[2]))
    ymax = ceil((bbox[1] + bbox[3]))

    extracted_mask = segmentation_mask[ymin:ymax, xmin:xmax]
    return np.asfortranarray(extracted_mask)


def generate_binary_mask(seg_mask: np.ndarray, category_code: int) -> tuple:
    """Generates a binary mask of a single category.

    Args:
        seg_mask: The extracted segmentation mask of only the area inside the
            bounding box
        category_code: The gray value of the specific class that is to be
            extracted. This should be taken from class_names.csv

    Returns:
        A tuple with element 1 being the binary mask and element 2 being the
        area of the mask.
    """
    bin_mask = seg_mask == category_code
    return bin_mask.astype('uint8'), np.count_nonzero(bin_mask)


def generate_annotations(pix_annotations_dir: str, xml_annotations_dir: str,
                         category_lookup: dict, img_lookup: dict,
                         class_colors: dict, train_set: set,
                         work_dir: str) -> tuple:
    """Generates COCO-like annotations.

    Args:
        pix_annotations_dir: Path to the pix_annotations directory,
            i.e. where the segmented images are.
        xml_annotations_dir: Path to the xml_annotations directory,
            i.e. where the object annotations are.
        category_lookup: A lookup table to get the category ID of every named
            category.
        img_lookup: A lookup table to get the image_id of every named image.
        class_colors: A lookup table to get the brightness value for every
            category. Used to make sure that we only get the binary mask of
            the one object, in case there's a bounding box overlap.
        train_set: A set that includes the image names of every image in the
            training set. Used to separate which annotation list the
            annotation should be appended to.
        work_dir: The directory to save all the memory-mapped arrays.

    Notes:
        work_dir is the directory where we can put temporary files. If we
        work with the entire deepscores dataset, the number of objects to
        detect is huge, thus we have to write to disk so we don't end up using
        several hundred gigabytes of memory. We do this by using a memmap
        object from numpy.

    Returns:
        A tuple of annotation lists, the 0th element being the training list
        and the 1st being the validation list.
    """
    print("Processing annotations...")
    train_annotation_list = []
    test_annotation_list = []

    counter = 1

    file_list = listdir(xml_annotations_dir)
    len_file_list = len(file_list)
    file_counter = 1

    for file_name in file_list:
        img_name = file_name.split('.')[0]
        xml_path = join(xml_annotations_dir, file_name)
        segmentation_path = join(pix_annotations_dir, img_name + '.png')

        seg_array = np.array(Image.open(segmentation_path))
        # NOTE: seg_array.shape = (height, width)

        # Generate tree from xml
        tree = ET.parse(xml_path)
        root = tree.getroot()
        size = root.find('size')
        # Get width and height to use as multipliers
        w = float(size.find('width').text)
        h = float(size.find('height').text)

        for obj in root.iter('object'):
            # Go through each annotation
            name = obj.find('name').text
            if name != "brace":
                # Get bounding box values
                bndbox = obj.find('bndbox')
                xmin = float(bndbox.find('xmin').text) * w
                ymin = float(bndbox.find('ymin').text) * h
                width = (float(bndbox.find('xmax').text) * w) - xmin
                height = (float(bndbox.find('ymax').text) * h) - ymin

                bbox = [xmin, ymin, round(width, 8), round(height, 8)]

                # Get category ID
                category_id = category_lookup[name]

                # Calculate segmentation
                # First extract the bbox area from the segmentation
                extracted_seg = extract_area_inside_bbox(bbox, seg_array)

                # Then turn it into a binary mask
                class_color = int(class_colors[name])
                bin_mask, area = generate_binary_mask(extracted_seg,
                                                      class_color)
                rle_segmentation = binary_mask_to_rle(bin_mask)

                if img_name in train_set:
                    train_annotation_list.append({
                        'segmentation': rle_segmentation,
                        'area': area,
                        'iscrowd': 0,
                        'image_id': img_lookup[img_name],
                        'bbox': bbox,
                        'category_id': category_id,
                        'id': counter
                    })
                else:
                    test_annotation_list.append({
                        'segmentation': rle_segmentation,
                        'area': area,
                        'iscrowd': 0,
                        'image_id': img_lookup[img_name],
                        'bbox': bbox,
                        'category_id': category_id,
                        'id': counter
                    })
                counter += 1
        if file_counter % 50 == 0 or file_counter == len_file_list:
            print('Processed {} of {} xml files'.format(file_counter,
                                                        len_file_list))

        file_counter += 1

    return train_annotation_list, test_annotation_list
