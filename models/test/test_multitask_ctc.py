#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import time
import tensorflow as tf
from tensorflow.python import debug as tf_debug

sys.path.append('../')
sys.path.append('../../')
from ctc.multitask_blstm_ctc import Multitask_BLSTM_CTC
from util import measure_time
from data import generate_data, num2alpha, num2phone
from experiments.utils.sparsetensor import list2sparsetensor, sparsetensor2list


class TestCTC(tf.test.TestCase):

    @measure_time
    def test_ctc(self):
        print("CTC Working check.")
        self.check_training()

    def check_training(self):
        print('----- multitask -----')
        tf.reset_default_graph()
        with tf.Graph().as_default():
            # Load batch data
            batch_size = 4
            inputs, labels_char, labels_phone, inputs_seq_len = generate_data(
                label_type='multitask',
                model='ctc',
                batch_size=batch_size)

            # Define placeholders
            inputs_pl = tf.placeholder(tf.float32,
                                       shape=[None, None, inputs.shape[-1]],
                                       name='input')
            indices_pl = tf.placeholder(tf.int64, name='indices')
            values_pl = tf.placeholder(tf.int32, name='values')
            shape_pl = tf.placeholder(tf.int64, name='shape')
            labels_pl = tf.SparseTensor(indices_pl, values_pl, shape_pl)
            indices_second_pl = tf.placeholder(tf.int64, name='indices_second')
            values_second_pl = tf.placeholder(tf.int32, name='values_second')
            shape_second_pl = tf.placeholder(tf.int64, name='shape_second')
            labels_second_pl = tf.SparseTensor(indices_second_pl,
                                               values_second_pl,
                                               shape_second_pl)
            inputs_seq_len_pl = tf.placeholder(tf.int64,
                                               shape=[None],
                                               name='inputs_seq_len')

            # Define model graph
            output_size_main = 26
            output_size_second = 61
            network = Multitask_BLSTM_CTC(
                batch_size=batch_size,
                input_size=inputs[0].shape[1],
                num_unit=256,
                num_layer_main=2,
                num_layer_second=1,
                output_size_main=output_size_main,
                output_size_second=output_size_second,
                main_task_weight=0.8,
                parameter_init=0.1,
                clip_grad=5.0,
                clip_activation=50,
                dropout_ratio_input=1.0,
                dropout_ratio_hidden=1.0,
                num_proj=None,
                weight_decay=1e-6)

            # Add to the graph each operation
            loss_op, logits_main, logits_second = network.compute_loss(
                inputs_pl,
                labels_pl,
                labels_second_pl,
                inputs_seq_len_pl)
            learning_rate = 1e-3
            train_op = network.train(loss_op,
                                     optimizer='rmsprop',
                                     learning_rate_init=learning_rate,
                                     is_scheduled=False)
            decode_op_main, decode_op_second = network.decoder(
                logits_main,
                logits_second,
                inputs_seq_len_pl,
                decode_type='beam_search',
                beam_width=20)
            ler_op_main, ler_op_second = network.compute_ler(
                decode_op_main, decode_op_second, labels_pl, labels_second_pl)

            # Add the variable initializer operation
            init_op = tf.global_variables_initializer()

            # Make feed dict
            feed_dict = {
                inputs_pl: inputs,
                labels_pl: list2sparsetensor(labels_char),
                labels_second_pl: list2sparsetensor(labels_phone),
                inputs_seq_len_pl: inputs_seq_len,
                network.keep_prob_input: network.dropout_ratio_input,
                network.keep_prob_hidden: network.dropout_ratio_hidden,
                network.lr: learning_rate
            }

            with tf.Session() as sess:
                # Initialize parameters
                sess.run(init_op)

                # Wrapper for tfdbg
                # sess = tf_debug.LocalCLIDebugWrapperSession(sess)

                # Train model
                max_steps = 400
                start_time_global = time.time()
                start_time_step = time.time()
                ler_train_char_pre = 1
                not_improved_count = 0
                for step in range(max_steps):

                    # Compute loss
                    _, loss_train = sess.run(
                        [train_op, loss_op], feed_dict=feed_dict)

                    # Gradient check
                    # grads = sess.run(network.clipped_grads, feed_dict=feed_dict)
                    # for grad in grads:
                    #     print(np.max(grad))

                    if (step + 1) % 10 == 0:
                        # Change to evaluation mode
                        feed_dict[network.keep_prob_input] = 1.0
                        feed_dict[network.keep_prob_hidden] = 1.0

                        # Compute accuracy
                        ler_train_char, ler_train_phone = sess.run(
                            [ler_op_main, ler_op_second], feed_dict=feed_dict)

                        duration_step = time.time() - start_time_step
                        print('Step %d: loss = %.3f / cer = %.4f / per = %.4f (%.3f sec)\n' %
                              (step + 1, loss_train, ler_train_char, ler_train_phone, duration_step))
                        start_time_step = time.time()

                        # Visualize
                        labels_st_char, labels_st_phone = sess.run(
                            [decode_op_main, decode_op_main], feed_dict=feed_dict)
                        labels_pred_char = sparsetensor2list(
                            labels_st_char, batch_size=1)
                        labels_pred_phone = sparsetensor2list(
                            labels_st_phone, batch_size=1)

                        # character
                        print('Character')
                        print('  True: %s' % num2alpha(labels_char[0]))
                        print('  Pred: %s' % num2alpha(labels_pred_char[0]))
                        print('Phone')
                        print('  True: %s' % num2phone(labels_phone[0]))
                        print('  Pred: %s' % num2phone(labels_pred_phone[0]))
                        print('----------------------------------------')

                        if ler_train_char >= ler_train_char_pre:
                            not_improved_count += 1
                        else:
                            not_improved_count = 0
                        if not_improved_count >= 3:
                            print('Modle is Converged.')
                            break
                        ler_train_char_pre = ler_train_char

                        # Change to training mode
                        network.is_training = True

                duration_global = time.time() - start_time_global
                print('Total time: %.3f sec' % (duration_global))


if __name__ == "__main__":
    tf.test.main()
