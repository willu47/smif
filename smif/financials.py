"""Utility functions for performing cost calculations and other financials


"""
import logging

import numpy as np
from smif import ureg

__author__ = "Will Usher"
__copyright__ = "Will Usher"
__license__ = "mit"

logger = logging.getLogger(__name__)


@ureg.wraps(ret=ureg.GBP/ureg.kW, args=[None, ureg.year, ureg.GBP/ureg.kW])
def annualised_cost(discount_rate, economic_life, capital_cost):
    """
    Arguments
    =========
    discount_rate : float, optional, default=5%
        The discount rate
    economic_life : :class:`pint.Quantity`
        The economic life of the asset in years (period over which a loan will
        be paid back)
    capital_cost : :class:`pint.Quantity`
        The capital cost of the asset in currency

    Returns
    =======
    annual_cost : :class:`pint.Quantity`
        The annualised cost of the asset in GBP
    """
    assert 0.0 <= discount_rate <= 1.0

    annual_cost = np.pmt(discount_rate, economic_life, capital_cost)
    return annual_cost


@ureg.wraps(ret=ureg.GBP/ureg.kW, args=[ureg.GBP/ureg.kW, None, None])
def aggregate_costs(annual_cost, year_bucket, discount_rate):
    """Aggregate anualised costs over `year_bucket` size buckets
    """
    npv = np.npv(discount_rate, np.repeat(annual_cost, year_bucket))
    return npv


def discount_factor(year, base_year=2015, discount_rate=0.05):
    """Returns a factor reflecting the time value of future investments

    Arguments
    =========
    year : int, :class:`numpy.ndarray`
        A single or array of years representing the time periods for which
        discount factors are required
    base_year : int, optional
        The year to which all future values are discounted
    discount_rate : float, optional, default=5%
        The discount rate
    """

    msg = "Year must be greater than or equal to `base_year`"
    assert np.all(year >= base_year), msg
    year_difference = year - base_year
    return np.array((1 - discount_rate) ** year_difference)


@ureg.wraps(ret=ureg.year, args=[ureg.year, ureg.year, ureg.year])
def remaining_years(lifetime, current_year, installed_year):
    """

    Arguments
    =========
    lifetime
        An attribute of an asset type
    current_year
        The current time period of the model
    installed_year
        An attribute of the state - the year in which the asset was installed
    """
    return lifetime - (current_year - installed_year)
