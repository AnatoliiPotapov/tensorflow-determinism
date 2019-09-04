import random
import numpy as np
import tensorflow as tf


def set_seed(seed = 1):
    """Seeds random number generators

      Returns: nothing
    """
    random.seed(seed)
    np.random.seed(seed)
    tf.compat.v1.set_random_seed(seed)
    print(f"Random seed == {seed}")

