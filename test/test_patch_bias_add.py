# Copyright 2019 The TensorFlow Authors. All Rights Reserved
#
# _new_biad_add_1_14() derived from source in
# https://github/tensorflow/tensorflow and therefore
# Copyright 2019 The TensorFlow Authors. All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========================================================================

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import os

import tensorflow as tf
from tensorflow.python.framework import constant_op
from tensorflow.python.framework import dtypes
from tensorflow.python.framework import test_util
from tensorflow.python.ops import array_ops
from tensorflow.python.ops import gradient_checker
from tensorflow.python.ops import gradients_impl
from tensorflow.python.ops import nn
from tensorflow.python.ops import nn_ops
import tensorflow.python.ops.nn_grad  # pylint: disable=unused-import
from tensorflow.python.platform import test


class BiasAddTest(test.TestCase):

  def _npBias(self, inputs, bias):
    assert len(bias.shape) == 1
    assert inputs.shape[-1] == bias.shape[0]
    return inputs + bias.reshape(([1] * (len(inputs.shape) - 1)) +
                                 [bias.shape[0]])

  def testNpBias(self):
    self.assertAllClose(
        np.array([[11, 22, 33], [41, 52, 63]]),
        self._npBias(
            np.array([[10, 20, 30], [40, 50, 60]]), np.array([1, 2, 3])))

  def _testBias(self, np_inputs, np_bias, use_gpu=False):
    np_val = self._npBias(np_inputs, np_bias)
    with self.cached_session(use_gpu=use_gpu):
      tf_val = nn_ops.bias_add(np_inputs, np_bias).eval()
    self.assertAllCloseAccordingToType(np_val, tf_val)

  def _AtLeast3d(self, np_value):
    # fill the input value to at least 3-dimension
    if np_value.ndim < 3:
      return np.reshape(np_value, (1,) * (3 - np_value.ndim) + np_value.shape)
    return np_value

  def _NHWCToNCHW(self, np_value):
    # fill the input value to at least 3-dimension
    np_value = self._AtLeast3d(np_value)
    # move the last dimension to second
    np_dim = list(range(np_value.ndim))
    np_dim_new = list(np_dim[0:1]) + list(np_dim[-1:]) + list(np_dim[1:-1])
    return np.transpose(np_value, np_dim_new)

  def _NCHWToNHWC(self, np_value):
    assert len(np_value.shape) >= 3
    np_dim = list(range(np_value.ndim))
    # move the second dimension to the last
    np_dim_new = list(np_dim[0:1]) + list(np_dim[2:]) + list(np_dim[1:2])
    return np.transpose(np_value, np_dim_new)

  def _testBiasNCHW(self, np_inputs, np_bias, use_gpu):
    np_val = self._npBias(np_inputs, np_bias)
    np_inputs = self._NHWCToNCHW(np_inputs)
    with self.cached_session(use_gpu=use_gpu):
      tf_val = nn_ops.bias_add(np_inputs, np_bias, data_format="NCHW").eval()
    tf_val = self._NCHWToNHWC(tf_val)
    self.assertAllCloseAccordingToType(self._AtLeast3d(np_val), tf_val)

  def _testAll(self, np_inputs, np_bias):
    self._testBias(np_inputs, np_bias, use_gpu=False)
    self._testBiasNCHW(np_inputs, np_bias, use_gpu=False)
    if np_inputs.dtype in [np.float16, np.float32, np.float64]:
      self._testBias(np_inputs, np_bias, use_gpu=True)
      self._testBiasNCHW(np_inputs, np_bias, use_gpu=True)

  @test_util.run_deprecated_v1
  def testIntTypes(self):
    for t in [np.int8, np.int16, np.int32, np.int64]:
      self._testAll(
          np.array([[10, 20, 30], [40, 50, 60]]).astype(t),
          np.array([1, 2, 3]).astype(t))

  @test_util.run_deprecated_v1
  def testFloatTypes(self):
    for t in [np.float16, np.float32, np.float64]:
      self._testAll(
          np.random.rand(4, 3, 3).astype(t), np.random.rand(3).astype(t))

  @test_util.run_deprecated_v1
  def test4DFloatTypes(self):
    for t in [np.float16, np.float32, np.float64]:
      self._testAll(
          np.random.rand(4, 3, 2, 3).astype(t),
          np.random.rand(3).astype(t))
      self._testAll(
          np.random.rand(2048, 4, 4, 4).astype(t),
          np.random.rand(4).astype(t))
      self._testAll(
          np.random.rand(4, 4, 4, 2048).astype(t),
          np.random.rand(2048).astype(t))

  @test_util.run_deprecated_v1
  def test5DFloatTypes(self):
    for t in [np.float16, np.float32, np.float64]:
      self._testAll(
          np.random.rand(4, 3, 2, 3, 4).astype(t),
          np.random.rand(4).astype(t))

  def _testGradient(self, np_input, bias, dtype, data_format, use_gpu):
    with self.cached_session(use_gpu=use_gpu):
      if data_format == "NCHW":
        np_input = self._NHWCToNCHW(np_input)
      input_tensor = constant_op.constant(
          np_input, shape=np_input.shape, dtype=dtype)
      bias_tensor = constant_op.constant(bias, shape=bias.shape, dtype=dtype)
      output_tensor = nn_ops.bias_add(
          input_tensor, bias_tensor, data_format=data_format)
      tensor_jacob_t, tensor_jacob_n = gradient_checker.compute_gradient(
          input_tensor, np_input.shape, output_tensor, np_input.shape)
      bias_jacob_t, bias_jacob_n = gradient_checker.compute_gradient(
          bias_tensor, bias.shape, output_tensor, np_input.shape)

      # Test gradient of BiasAddGrad
      bias_add_grad = gradients_impl.gradients(
          nn_ops.l2_loss(output_tensor), bias_tensor)[0]
      grad_jacob_t, grad_jacob_n = gradient_checker.compute_gradient(
          output_tensor, np_input.shape, bias_add_grad, bias.shape)

      if dtype == np.float16:
        # Compare fp16 analytical gradients to fp32 numerical gradients,
        # since fp16 numerical gradients are too imprecise unless great
        # care is taken with choosing the inputs and the delta. This is
        # a weaker, but pragmatic, check (in particular, it does not test
        # the op itself, only its gradient).
        input_tensor = constant_op.constant(
            np_input, shape=np_input.shape, dtype=np.float32)
        bias_tensor = constant_op.constant(
            bias, shape=bias.shape, dtype=np.float32)
        output_tensor = nn_ops.bias_add(
            input_tensor, bias_tensor, data_format=data_format)
        _, tensor_jacob_n = gradient_checker.compute_gradient(input_tensor,
                                                              np_input.shape,
                                                              output_tensor,
                                                              np_input.shape)
        _, bias_jacob_n = gradient_checker.compute_gradient(bias_tensor,
                                                            bias.shape,
                                                            output_tensor,
                                                            np_input.shape)

        bias_add_grad = gradients_impl.gradients(
            nn_ops.l2_loss(output_tensor), bias_tensor)[0]
        _, grad_jacob_n = gradient_checker.compute_gradient(output_tensor,
                                                            np_input.shape,
                                                            bias_add_grad,
                                                            bias.shape)

      threshold = 5e-3
      if dtype == dtypes.float64:
        threshold = 1e-10
      self.assertAllClose(tensor_jacob_t, tensor_jacob_n, threshold, threshold)
      self.assertAllClose(bias_jacob_t, bias_jacob_n, threshold, threshold)
      self.assertAllClose(grad_jacob_t, grad_jacob_n, threshold, threshold)

  @test_util.run_deprecated_v1
  def testGradientTensor2D(self):
    for (data_format, use_gpu) in ("NHWC", False), ("NHWC", True):
      for dtype in (dtypes.float16, dtypes.float32, dtypes.float64):
        np_input = np.array(
            [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            dtype=dtype.as_numpy_dtype).reshape(3, 2)
        bias = np.array([1.3, 2.4], dtype=dtype.as_numpy_dtype)
        self._testGradient(np_input, bias, dtype, data_format, use_gpu)

  @test_util.run_deprecated_v1
  def testGradientTensor3D(self):
    for (data_format, use_gpu) in [("NHWC", False), ("NHWC", True),
                                   ("NCHW", False), ("NCHW", True)]:
      for dtype in (dtypes.float16, dtypes.float32, dtypes.float64):
        np_input = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
                            dtype=dtype.as_numpy_dtype).reshape(1, 3, 2)
        bias = np.array([1.3, 2.4], dtype=dtype.as_numpy_dtype)
        self._testGradient(np_input, bias, dtype, data_format, use_gpu)

  @test_util.run_deprecated_v1
  def testGradientTensor4D(self):
    for (data_format, use_gpu) in [("NHWC", False)]:
      for dtype in (dtypes.float16, dtypes.float32, dtypes.float64):
        np_input = np.arange(
            1.0, 49.0, dtype=dtype.as_numpy_dtype).reshape(
                [2, 3, 4, 2]).astype(np.float32)
        bias = np.array([1.3, 2.4], dtype=dtype.as_numpy_dtype)
        self._testGradient(np_input, bias, dtype, data_format, use_gpu)
        np_input = np.arange(
            1.0, 513.0, dtype=dtype.as_numpy_dtype).reshape(
                [64, 2, 2, 2]).astype(np.float32)
        self._testGradient(np_input, bias, dtype, data_format, use_gpu)
        np_input = np.arange(
            1.0, 513.0, dtype=dtype.as_numpy_dtype).reshape(
                [2, 2, 2, 64]).astype(np.float32)
        self._testGradient(np_input,
                           np.random.rand(64).astype(dtype.as_numpy_dtype),
                           dtype, data_format, use_gpu)

  @test_util.run_deprecated_v1
  def testGradientTensor5D(self):
    for (data_format, use_gpu) in [("NHWC", False), ("NHWC", True),
                                   ("NCHW", False), ("NCHW", True)]:
      for dtype in (dtypes.float16, dtypes.float32, dtypes.float64):
        np_input = np.arange(
            1.0, 49.0, dtype=dtype.as_numpy_dtype).reshape(
                [1, 2, 3, 4, 2]).astype(np.float32)
        bias = np.array([1.3, 2.4], dtype=dtype.as_numpy_dtype)
        self._testGradient(np_input, bias, dtype, data_format, use_gpu)

  @test_util.run_deprecated_v1
  def testEmpty(self):
    np.random.seed(7)
    for shape in (0, 0), (2, 0), (0, 2), (4, 3, 0), (4, 0, 3), (0, 4, 3):
      self._testAll(np.random.randn(*shape), np.random.randn(shape[-1]))

  @test_util.run_deprecated_v1
  def testEmptyGradient(self):
    for (data_format, use_gpu) in ("NHWC", False), ("NHWC", True):
      for shape in (0, 0), (2, 0), (0, 2):
        self._testGradient(
            np.random.randn(*shape), np.random.randn(shape[-1]), dtypes.float64,
            data_format, use_gpu)

    for (data_format, use_gpu) in [("NHWC", False), ("NHWC", True),
                                   ("NCHW", False), ("NCHW", True)]:
      for shape in (4, 3, 0), (4, 0, 3), (0, 4, 3):
        self._testGradient(
            np.random.randn(*shape),
            np.random.randn(shape[-1]), dtypes.float64, data_format, use_gpu)

  # Deterministic testing starts here

  def _make_shape_tuple(self, batch_size, channel_count, data_rank, data_dim,
                        data_layout):
    data_dims = data_rank * (data_dim,)
    if data_layout == 'channels_first':
      shape = (batch_size,) + (channel_count,) + data_dims
    elif data_layout == 'channels_last':
      shape = (batch_size,) + data_dims + (channel_count,)
    else:
      raise ValueError("Unknown data format")
    return shape

  def _data_format_from_data_layout(self, data_layout=None):
    if data_layout == 'channels_first':
      return 'NCHW'
    elif data_layout == 'channels_last':
      return 'NHWC'
    else:
      raise ValueError("Unknown data_layout")

  def _random_data_op(self, shape, data_type):
    return constant_op.constant(
        2 * np.random.random_sample(shape) - 1, dtype=data_type)

  def _random_ndarray(self, shape):
    return 2 * np.random.random_sample(shape) - 1

  def _assert_reproducible(self, operation, feed_dict={}):
    with self.cached_session(force_gpu=True):
      result_a = operation[0].eval(feed_dict=feed_dict)
      result_b = operation[0].eval(feed_dict=feed_dict)
      self.assertAllEqual(result_a, result_b)

  def _testDeterministicGradientsCase(self, op_binding, data_layout, data_rank,
                                      data_type):
    seed = (hash(data_layout) % 256 +
            hash(data_rank) % 256 +
            hash(data_type) % 256)
    np.random.seed(seed)
    batch_size = 10
    channel_count = 8
    data_dim = 14
    in_shape = self._make_shape_tuple(batch_size, channel_count, data_rank,
                                      data_dim, data_layout)
    bias_shape = (channel_count,)
    out_shape = in_shape
    in_op = self._random_data_op(in_shape, data_type)
    bias_op = self._random_data_op(bias_shape, data_type)
    data_format = self._data_format_from_data_layout(data_layout)
    bias_add_op = op_binding(in_op, bias_op, data_format=data_format)
    upstream_gradients = array_ops.placeholder(data_type, shape=out_shape,
                                               name='upstream_gradients')
    gradient_injector_op = bias_add_op * upstream_gradients
    # The gradient function behaves as if grad_ys is multiplied by the op
    # gradient result, not passing the upstram gradients through the op's
    # gradient generation graph. This is the reason for using the
    # gradient_injector_op
    grad_ys = None
    bias_gradients_op = gradients_impl.gradients(
        gradient_injector_op, bias_op, grad_ys=grad_ys,
        colocate_gradients_with_ops=True)
    for i in range(5):
      feed_dict = {upstream_gradients: self._random_ndarray(out_shape)}
      self._assert_reproducible(bias_gradients_op, feed_dict=feed_dict)

  @test_util.run_cuda_only
  def testDeterministicGradients(self):
    for op_binding in (tf.nn.bias_add, nn.bias_add, nn_ops.bias_add):
      for data_layout in ('channels_first', 'channels_last'):
        for data_rank in (1, 2, 3):
          for data_type in (dtypes.float16, dtypes.float32, dtypes.float64):
            self._testDeterministicGradientsCase(op_binding, data_layout,
                                                 data_rank, data_type)


if __name__ == "__main__":
  import sys
  sys.path.append('..')
  from tfdeterminism import patch
  patch()
  test.main()
