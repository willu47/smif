#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

"""
from __future__ import division, print_function, absolute_import
import logging
import pkg_resources
from pint import UnitRegistry

__author__ = "Will Usher"
__copyright__ = "Will Usher"
__license__ = "mit"

_logger = logging.getLogger(__name__)

try:
    __version__ = pkg_resources.get_distribution(__name__).version
except:
    __version__ = 'unknown'

ureg = UnitRegistry()
Q_ = ureg.Quantity

ureg.define('£ = 1 = GBP')
