#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


def phone2num(phone_list, map_file_path):
    """Convert from phone to number.
    Args:
        phone_list: list of phones (string)
        map_file_path: path to the mapping file
    Returns:
        phone_list: list of phone indices (int)
    """
    # Read mapping file
    map_dict = {}
    with open(map_file_path, 'r') as f:
        for line in f:
            line = line.strip().split('  ')
            map_dict[str(line[0])] = int(line[1])

    # Convert from phone to number
    for i in range(len(phone_list)):
        phone_list[i] = map_dict[phone_list[i]]

    return phone_list


def num2phone(num_list, map_file_path):
    """Convert from number to phone.
    Args:
        num_list: list of phone indices
        map_file_path: path to the mapping file
    Returns:
        str_phone: string of phones
    """
    # Read mapping file
    map_dict = {}
    with open(map_file_path, 'r') as f:
        for line in f:
            line = line.strip().split()
            map_dict[int(line[1])] = line[0]

    # Convert from indices to the corresponding phones
    phone_list = []
    for i in range(len(num_list)):
        phone_list.append(map_dict[num_list[i]])
    str_phone = ' '.join(phone_list)

    return str_phone
