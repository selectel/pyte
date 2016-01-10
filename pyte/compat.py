# -*- coding: utf-8 -*-
"""
    pyte.compat
    ~~~~~~~~~~~

    Python version specific compatibility fixes.

    :copyright: (c) 2011-2013 Selectel, see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

import sys

if sys.version_info[0] == 2:
    from future_builtins import map

    range = xrange
    str = unicode
    chr = unichr
else:
    from builtins import map, range, str, chr
