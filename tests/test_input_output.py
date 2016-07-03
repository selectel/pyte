# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import pickle
import os.path

import pytest

import pyte


test_dir = os.path.dirname(__file__)


@pytest.mark.parametrize("name", [
    "vi", "ls", "top", "htop", "mc", "emacs-tetris"
])
def test_input_output(name):
    with open(os.path.join(test_dir, name + ".input"), "rb") as handle:
        input = handle.read()

    with open(os.path.join(test_dir, name + ".output"), "rb") as handle:
        output = pickle.load(handle)

    screen = pyte.Screen(80, 24)
    stream = pyte.Stream(screen)
    stream.feed(input)
    assert screen.display == output
