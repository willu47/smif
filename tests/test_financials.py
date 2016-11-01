import numpy as np
from numpy.testing import assert_allclose
from smif import Q_
from smif.financials import aggregate_costs, annualised_cost, discount_factor


def test_annualised_cost():
    discount_rate = 0.10
    economic_life = Q_(20, 'year')  # years
    capital_cost = Q_(1500, 'GBP/kW')  # £/kW

    actual = annualised_cost(discount_rate, economic_life, capital_cost)
    expected = Q_(-176.189437, 'MGBP/GW')

    assert_allclose(actual, expected)


def test_discount_factor_base_year():

    actual = discount_factor(2015)
    expected = 1
    assert actual == expected


def test_discount_factor_array():

    years = np.array([2015, 2020, 2025, 2030, 2035,
                      2040, 2045, 2050, 2055, 2060])
    actual = discount_factor(years)
    expected = np.array([1,
                         0.773780938,
                         0.598736939,
                         0.46329123,
                         0.358485922,
                         0.277389573,
                         0.214638764,
                         0.166083384,
                         0.128512157,
                         0.099440257])
    assert_allclose(actual, expected)


def test_discounted_aggregate_costs():
    annual_cost = Q_(-1500, 'GBP/kW')
    actual = aggregate_costs(annual_cost, 5, 0.0)
    expected = Q_(-7500, 'GBP/kW')
    assert actual == expected


def test_discounted_aggregate_costs_bulk():
    annual_cost = Q_(-176.189437, 'GBP/kW')
    actual = aggregate_costs(annual_cost, 20, 0.1)
    expected = Q_(-1650, 'GBP/kW')
    assert_allclose(actual, expected)
