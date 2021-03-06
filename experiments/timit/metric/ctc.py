#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Define evaluation method for CTC network (TIMIT corpus)."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re
import Levenshtein
from tqdm import tqdm

from utils.labels.character import num2char
from utils.labels.phone import num2phone, phone2num
from .mapping import map_to_39phone
from .edit_distance import compute_edit_distance
from utils.sparsetensor import list2sparsetensor, sparsetensor2list
from utils.exception_func import exception


@exception
def do_eval_per(session, decode_op, per_op, network, dataset, label_type,
                eval_batch_size=1, is_progressbar=False, is_multitask=False):
    """Evaluate trained model by Phone Error Rate.
    Args:
        session: session of training model
        decode_op: operation for decoding
        per_op: operation for computing phone error rate
        network: network to evaluate
        dataset: `Dataset' class
        label_type: phone39 or phone48 or phone61 or character
        eval_batch_size: batch size on evaluation
        is_progressbar: if True, visualize the progressbar
        is_multitask: if True, evaluate the multitask model
    Returns:
        per_global: An average of PER
    """
    if label_type not in ['phone39', 'phone48', 'phone61']:
        raise ValueError(
            'data_type is "phone39" or "phone48" or "phone61".')

    batch_size = eval_batch_size
    num_examples = dataset.data_num
    iteration = int(num_examples / batch_size)
    if (num_examples / batch_size) != int(num_examples / batch_size):
        iteration += 1
    per_global = 0

    phone2num_map_file_path = '../metric/mapping_files/ctc/phone2num_' + \
        label_type[5:7] + '.txt'
    phone2num_39_map_file_path = '../metric/mapping_files/ctc/phone2num_39.txt'
    phone2phone_map_file_path = '../metric/mapping_files/phone2phone.txt'
    iterator = tqdm(range(iteration)) if is_progressbar else range(iteration)
    for step in iterator:
        # Create feed dictionary for next mini batch
        if not is_multitask:
            inputs, labels_true, inputs_seq_len, _ = dataset.next_batch(
                batch_size=batch_size)
        else:
            inputs, _, labels_true, inputs_seq_len, _ = dataset.next_batch(
                batch_size=batch_size)

        feed_dict = {
            network.inputs: inputs,
            network.labels: list2sparsetensor(labels_true),
            network.inputs_seq_len: inputs_seq_len,
            network.keep_prob_input: 1.0,
            network.keep_prob_hidden: 1.0
        }

        batch_size_each = len(labels_true)

        if False:
            # Evaluate by 61 phones
            per_local = session.run(per_op, feed_dict=feed_dict)
            per_global += per_local * batch_size_each

        else:
            # Evaluate by 39 phones
            labels_pred_st = session.run(decode_op, feed_dict=feed_dict)
            labels_pred = sparsetensor2list(labels_pred_st, batch_size_each)
            for i_batch in range(batch_size_each):
                # Convert num to phone (list of phone strings)
                phone_pred_seq = num2phone(
                    labels_pred[i_batch], phone2num_map_file_path)
                phone_pred_list = phone_pred_seq.split(' ')

                # Mapping to 39 phones (list of phone strings)
                phone_pred_list = map_to_39phone(
                    phone_pred_list, label_type, phone2phone_map_file_path)

                # Convert phone to num (list of phone indices)
                phone_pred_list = phone2num(
                    phone_pred_list, phone2num_39_map_file_path)
                labels_pred[i_batch] = phone_pred_list

            # Compute edit distance
            labels_true_st = list2sparsetensor(labels_true)
            labels_pred_st = list2sparsetensor(labels_pred)
            per_local = compute_edit_distance(
                session, labels_true_st, labels_pred_st)
            per_global += per_local * batch_size_each

    per_global /= dataset.data_num

    return per_global


@exception
def do_eval_cer(session, decode_op, network, dataset, eval_batch_size=1,
                is_progressbar=False, is_multitask=False):
    """Evaluate trained model by Character Error Rate.
    Args:
        session: session of training model
        decode_op: operation for decoding
        network: network to evaluate
        dataset: Dataset class
        eval_batch_size: batch size on evaluation
        is_progressbar: if True, visualize the progressbar
        is_multitask: if True, evaluate the multitask model
    Return:
        cer_mean: An average of CER
    """
    batch_size = eval_batch_size
    num_examples = dataset.data_num
    iteration = int(num_examples / batch_size)
    if (num_examples / batch_size) != int(num_examples / batch_size):
        iteration += 1
    cer_sum = 0

    map_file_path = '../metric/mapping_files/ctc/char2num.txt'
    iterator = tqdm(range(iteration)) if is_progressbar else range(iteration)
    for step in iterator:
        # Create feed dictionary for next mini batch
        if not is_multitask:
            inputs, labels_true, inputs_seq_len, _ = dataset.next_batch(
                batch_size=batch_size)
        else:
            inputs, labels_true, _, inputs_seq_len, _ = dataset.next_batch(
                batch_size=batch_size)

        feed_dict = {
            network.inputs: inputs,
            network.labels: list2sparsetensor(labels_true),
            network.inputs_seq_len: inputs_seq_len,
            network.keep_prob_input: 1.0,
            network.keep_prob_hidden: 1.0
        }

        batch_size_each = len(labels_true)
        labels_pred_st = session.run(decode_op, feed_dict=feed_dict)
        labels_pred = sparsetensor2list(labels_pred_st, batch_size_each)
        for i_batch in range(batch_size_each):

            # Convert from list to string
            str_pred = num2char(labels_pred[i_batch], map_file_path)
            str_true = num2char(labels_true[i_batch], map_file_path)

            # Remove silence(_) labels
            str_pred = re.sub(r'[_]+', "", str_pred)
            str_true = re.sub(r'[_]+', "", str_true)

            # Compute edit distance
            cer_each = Levenshtein.distance(
                str_pred, str_true) / len(list(str_true))
            cer_sum += cer_each

    cer_mean = cer_sum / dataset.data_num

    return cer_mean
