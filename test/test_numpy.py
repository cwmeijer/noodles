from noodles import schedule, run_process, serial
from noodles.storable import PickleString

import numpy as np
from numpy import (random, fft, exp)


def registry():
    return serial.base() + serial.numpy()


@schedule
def do_fft(a):
    return fft.fft(a)


@schedule
def make_kernel(n, sigma):
    return exp(-fft.fftfreq(n)**2 * sigma**2)


@schedule
def do_ifft(a):
    return fft.ifft(a).real


@schedule
def apply_filter(a, b):
    return a * b


@schedule
def make_noise(n):
    return random.normal(0, 1, n)


def test_pickle():
    x = make_noise(256)
    k = make_kernel(256, 10)
    x_smooth = do_ifft(apply_filter(do_fft(x), k))

    result = run_process(x_smooth, 1, registry)

    assert isinstance(result, np.ndarray)
    assert result.size == 256
    # np.savetxt("curve.txt", result.data)
