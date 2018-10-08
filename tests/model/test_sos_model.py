# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
from copy import copy
from unittest import TestCase
from unittest.mock import Mock

from pytest import fixture, raises
from smif.metadata import RelativeTimestep, Spec
from smif.model.dependency import Dependency
from smif.model.model import ScenarioModel
from smif.model.sector_model import SectorModel
from smif.model.sos_model import SosModel


class EmptySectorModel(SectorModel):
    """Simulate nothing
    """
    def simulate(self, data):
        return data


@fixture(scope='function')
def empty_sector_model():
    """SectorModel ready for customisation
    """
    return EmptySectorModel('test')


@fixture(scope='function')
def scenario_model():
    """ScenarioModel providing precipitation
    """
    model = ScenarioModel('climate')
    model.add_output(
        Spec.from_dict({
            'name': 'precipitation',
            'dims': ['LSOA'],
            'coords': {'LSOA': [1, 2, 3]},
            'dtype': 'float',
            'unit': 'ml'
        })
    )
    model.add_output(
        Spec.from_dict({
            'name': 'reservoir_level',
            'dims': ['LSOA'],
            'coords': {'LSOA': [1, 2, 3]},
            'dtype': 'float',
            'unit': 'ml'
        })
    )
    model.scenario = 'UKCP09 High emissions'
    return model


@fixture(scope='function')
def sector_model():
    """SectorModel requiring precipitation and cost, providing water
    """
    model = EmptySectorModel('water_supply')
    model.add_input(
        Spec.from_dict({
            'name': 'precipitation',
            'dims': ['LSOA'],
            'coords': {'LSOA': [1, 2, 3]},
            'dtype': 'float',
            'unit': 'ml'
        })
    )
    model.add_input(
        Spec.from_dict({
            'name': 'reservoir_level',
            'dims': ['LSOA'],
            'coords': {'LSOA': [1, 2, 3]},
            'dtype': 'float',
            'unit': 'ml'
        })
    )
    model.add_input(
        Spec.from_dict({
            'name': 'rGVA',
            'dims': ['LSOA'],
            'coords': {'LSOA': [1, 2, 3]},
            'dtype': 'float',
            'unit': 'million GBP'
        })
    )
    model.add_output(
        Spec.from_dict({
            'name': 'water',
            'dims': ['LSOA'],
            'coords': {'LSOA': [1, 2, 3]},
            'dtype': 'float',
            'unit': 'Ml'
        })
    )
    model.add_output(
        Spec.from_dict({
            'name': 'reservoir_level',
            'dims': ['LSOA'],
            'coords': {'LSOA': [1, 2, 3]},
            'dtype': 'float',
            'unit': 'ml'
        })
    )
    return model


@fixture(scope='function')
def economic_model():
    """SectorModel requiring precipitation and cost, providing water
    """
    model = EmptySectorModel('economic_model')
    model.add_output(
        Spec.from_dict({
            'name': 'gva',
            'dims': ['LSOA'],
            'coords': {'LSOA': [1, 2, 3]},
            'dtype': 'float',
            'unit': 'million GBP'
        })
    )
    return model


@fixture
def energy_model():
    class EnergyModel(SectorModel):
        """
        electricity_demand_input -> fluffiness
        """

        def simulate(self, data_handle):
            """Mimics the running of a sector model
            """
            fluff = data_handle['electricity_demand_input']
            data_handle['fluffiness'] = fluff * 0.819
            return data_handle

    energy_model = EnergyModel('energy_model')
    energy_model.add_input(
        Spec(
            name='electricity_demand_input',
            dims=['LSOA'],
            coords={'LSOA': ['E090001', 'E090002']},
            dtype='float',
        )
    )
    energy_model.add_output(
        Spec(
            name='fluffiness',
            dims=['LSOA'],
            coords={'LSOA': ['E090001', 'E090002']},
            dtype='float',
        )
    )

    return energy_model


@fixture(scope='function')
def sos_model(sector_model, scenario_model, economic_model):
    """SosModel with one scenario and one sector model
    """
    model = SosModel('test_sos_model')
    model.add_model(scenario_model)
    model.add_model(economic_model)
    model.add_model(sector_model)
    model.add_dependency(scenario_model, 'precipitation', sector_model, 'precipitation')
    model.add_dependency(economic_model, 'gva', sector_model, 'rGVA')
    return model


@fixture(scope='function')
def scenario_only_sos_model_dict():
    """Config for a SosModel with one scenario
    """
    return {
        'name': 'test_sos_model',
        'description': 'Readable description of the sos model',
        'scenarios': [
            {
                'name': 'climate',
                'scenario': 'UKCP09 High emissions',
                'outputs': [
                    {
                        'name': 'precipitation',
                        'dims': ['LSOA'],
                        'coords': {'LSOA': [1, 2, 3]},
                        'dtype': 'float',
                        'unit': 'ml'
                    },
                    {
                        'name': 'reservoir_level',
                        'dims': ['LSOA'],
                        'coords': {'LSOA': [1, 2, 3]},
                        'dtype': 'float',
                        'unit': 'ml'
                    }
                ]
            }
        ],
        'sector_models': [],
        'model_dependencies': [],
        'scenario_dependencies': []
    }


@fixture(scope='function')
def sos_model_dict(scenario_only_sos_model_dict):
    """Config for a SosModel with one scenario and one sector model
    """
    config = scenario_only_sos_model_dict
    config['sector_models'] = [
        {
            'name': 'economic_model',
            'inputs': [],
            'parameters': [],
            'outputs': [
                {
                    'name': 'gva',
                    'dims': ['LSOA'],
                    'coords': {'LSOA': [1, 2, 3]},
                    'dtype': 'float',
                    'unit': 'million GBP'
                }
            ]
        },
        {
            'name': 'water_supply',
            'inputs': [
                {
                    'name': 'precipitation',
                    'dims': ['LSOA'],
                    'coords': {'LSOA': [1, 2, 3]},
                    'dtype': 'float',
                    'unit': 'ml'
                },
                {
                    'name': 'rGVA',
                    'dims': ['LSOA'],
                    'coords': {'LSOA': [1, 2, 3]},
                    'dtype': 'float',
                    'unit': 'million GBP'
                },
                {
                    'name': 'reservoir_level',
                    'dims': ['LSOA'],
                    'coords': {'LSOA': [1, 2, 3]},
                    'dtype': 'float',
                    'unit': 'ml'
                }
            ],
            'parameters': [],
            'outputs': [
                {
                    'name': 'water',
                    'dims': ['LSOA'],
                    'coords': {'LSOA': [1, 2, 3]},
                    'dtype': 'float',
                    'unit': 'Ml'
                },
                {
                    'name': 'reservoir_level',
                    'dims': ['LSOA'],
                    'coords': {'LSOA': [1, 2, 3]},
                    'dtype': 'float',
                    'unit': 'ml'
                }
            ]
        }
    ]
    config['scenario_dependencies'] = [
        {
            'source': 'climate',
            'source_output': 'precipitation',
            'sink_input': 'precipitation',
            'sink': 'water_supply',
            'timestep': 'CURRENT'
        },
        {
            'source': 'climate',
            'source_output': 'reservoir_level',
            'sink_input': 'reservoir_level',
            'sink': 'water_supply',
            'timestep': 'CURRENT'
        }
    ]
    config['model_dependencies'] = [
        {
            'source': 'economic_model',
            'source_output': 'gva',
            'sink_input': 'rGVA',
            'sink': 'water_supply',
            'timestep': 'CURRENT'
        },
        {
            'source': 'water_supply',
            'source_output': 'reservoir_level',
            'sink_input': 'reservoir_level',
            'sink': 'water_supply',
            'timestep': 'PREVIOUS'
        }
    ]
    return config


class TestSosModel():
    """Construct from config or compose from objects
    """
    def test_construct(self, sos_model_dict, scenario_model, sector_model, economic_model):
        """Constructing from config of the form::

            {
                'name': 'sos_model_name',
                'description': 'friendly description of the sos model',
                'dependencies': [
                    {
                        'source': str (Model.name),
                        'source_output': str (Metadata.name),
                        'sink': str (Model.name),
                        'sink_output': str (Metadata.name)
                    }
                ]
            }

        With list of child SectorModel/ScenarioModel instances passed in alongside.
        """
        sos_model = SosModel.from_dict(
            sos_model_dict, [scenario_model, sector_model, economic_model])

        assert isinstance(sos_model, SosModel)
        assert list(sos_model.scenario_models) == [scenario_model]
        assert isinstance(sos_model.get_model('climate'), ScenarioModel)
        assert sos_model.sector_models == [sector_model, economic_model] or \
            sos_model.sector_models == [economic_model, sector_model]
        assert isinstance(sos_model.get_model('economic_model'), SectorModel)
        assert isinstance(sos_model.get_model('water_supply'), SectorModel)

    def test_optional_description(self, sos_model_dict):
        """Default to empty description
        """
        del sos_model_dict['description']
        sos_model = SosModel.from_dict(sos_model_dict)
        assert sos_model.description == ''

    def test_dependencies_fields(self, sos_model_dict, scenario_model, sector_model,
                                 economic_model):
        """Compose dependencies from scenario- and model- fields
        """
        sos_model_dict['scenario_dependencies'] = [
            {
                'source': 'climate',
                'source_output': 'precipitation',
                'sink_input': 'precipitation',
                'sink': 'water_supply',
                'timestep': 'CURRENT'
            },
            {
                'source': 'climate',
                'source_output': 'reservoir_level',
                'sink_input': 'reservoir_level',
                'sink': 'water_supply',
                'timestep': 'CURRENT'
            }
        ]
        sos_model_dict['model_dependencies'] = [
            {
                'source': 'economic_model',
                'source_output': 'gva',
                'sink_input': 'rGVA',
                'sink': 'water_supply',
                'timestep': 'CURRENT'
            },
            {
                'source': 'water_supply',
                'source_output': 'reservoir_level',
                'sink_input': 'reservoir_level',
                'sink': 'water_supply',
                'timestep': 'PREVIOUS'
            }
        ]
        sos_model = SosModel.from_dict(
            sos_model_dict, [scenario_model, sector_model, economic_model])
        actual = sos_model.as_dict()
        TestCase().assertCountEqual(
            actual['scenario_dependencies'], sos_model_dict['scenario_dependencies'])
        TestCase().assertCountEqual(
            actual['model_dependencies'], sos_model_dict['model_dependencies'])

    def test_compose(self, sos_model):
        with raises(AssertionError) as ex:
            sos_model.add_model(SosModel('test'))
        msg = "Only Models can be added to a SosModel (and SosModels cannot be nested)"
        assert msg in str(ex)

    def test_as_dict(self, sos_model):
        """as_dict correctly returns configuration as a dictionary, with child models as_dict
        similarly
        """
        actual = sos_model.as_dict()
        del actual['scenario_dependencies']
        del actual['model_dependencies']
        expected = {
            'name': 'test_sos_model',
            'description': '',
            'scenarios': ['climate'],
            'sector_models': ['economic_model', 'water_supply']
        }
        assert actual == expected

    def test_add_dependency(self, empty_sector_model):
        """Add models, connect via dependency
        """
        spec = Spec(
            name='hourly_value',
            dims=['hours'],
            coords={'hours': range(24)},
            dtype='int'
        )
        sink_model = copy(empty_sector_model)
        sink_model.add_input(spec)

        source_model = copy(empty_sector_model)
        source_model.add_output(spec)

        sos_model = SosModel('test')
        sos_model.add_model(source_model)
        sos_model.add_model(sink_model)

        sos_model.add_dependency(source_model, 'hourly_value', sink_model, 'hourly_value')

    def test_before_model_run_fails(self, sos_model):
        """Before model run should raise
        """
        data_handle = Mock()
        with raises(AttributeError):
            sos_model.before_model_run(data_handle)

    def test_simulate_fails(self, sos_model):
        """Simulate should raise
        """
        data_handle = Mock()
        with raises(AttributeError):
            sos_model.simulate(data_handle)


class TestSosModelProperties():
    """SosModel has inputs, outputs, parameters

    Convergence settings (should perhaps move to runner)
    """

    def test_model_inputs(self, sos_model):
        spec = sos_model.get_model('water_supply').inputs['precipitation']
        assert isinstance(spec, Spec)

    def test_model_outputs(self, sos_model):
        spec = sos_model.get_model('water_supply').outputs['water']
        assert isinstance(spec, Spec)


class TestSosModelDependencies(object):
    """SosModel can represent data flow as defined by model dependencies
    """
    def test_simple_dependency(self, sos_model):
        """Dependencies
        """
        scenario = sos_model.get_model('climate')
        model = sos_model.get_model('water_supply')
        economic_model = sos_model.get_model('economic_model')

        actual = list(sos_model.dependencies)
        expected = [
            Dependency(
                scenario,
                scenario.outputs['precipitation'],
                model,
                model.inputs['precipitation']
            ),
            Dependency(
                economic_model,
                economic_model.outputs['gva'],
                model,
                model.inputs['rGVA']
            )
        ]
        assert actual == expected or actual == list(reversed(expected))

        actual = list(sos_model.scenario_dependencies)
        expected = [
            Dependency(
                scenario,
                scenario.outputs['precipitation'],
                model,
                model.inputs['precipitation']
            )
        ]
        assert actual == expected

        actual = list(sos_model.model_dependencies)
        expected = [
            Dependency(
                economic_model,
                economic_model.outputs['gva'],
                model,
                model.inputs['rGVA']
            )
        ]
        assert actual == expected

    def test_dependency_timestep(self, sos_model, scenario_model, sector_model):
        # add self-dependency on previous timestep output
        sos_model.add_dependency(
            sector_model, 'reservoir_level', sector_model, 'reservoir_level',
            timestep=RelativeTimestep.PREVIOUS)
        # add dependency on scenario (to satisfy initial timestep input requirement)
        sos_model.add_dependency(
            scenario_model, 'reservoir_level',
            sector_model, 'reservoir_level'
        )

    def test_dependency_duplicate(self, sos_model, scenario_model, sector_model):
        with raises(ValueError) as ex:
            sos_model.add_dependency(
                scenario_model, 'precipitation',
                sector_model, 'precipitation')
        assert "Could not add dependency: input 'precipitation' already provided" in str(ex)

    def test_dependency_not_present(self, sos_model, scenario_model, energy_model):
        """Should fail with missing input/output
        """
        with raises(ValueError) as ex:
            sos_model.add_dependency(
                scenario_model, 'not_present', energy_model, 'electricity_demand_input')
        msg = "Output 'not_present' is not defined in '{}'".format(scenario_model.name)
        assert msg in str(ex)

        with raises(ValueError) as ex:
            sos_model.add_dependency(
                scenario_model, 'precipitation', energy_model, 'incorrect_name')
        msg = "Input 'incorrect_name' is not defined in '{}'".format(energy_model.name)
        assert msg in str(ex)

    def test_data_not_present(self, sos_model_dict, sector_model):
        """Raise a NotImplementedError if an input is defined but no dependency links
        it to a data source
        """
        sos_model_dict['scenario_dependencies'] = []
        sos_model_dict['model_dependencies'] = []
        with raises(NotImplementedError):
            SosModel.from_dict(sos_model_dict, [sector_model])

    def test_undefined_unit_conversion(self, sos_model_dict, sector_model, scenario_model,
                                       economic_model):
        """Error on invalid dependency
        """
        sector_model.inputs['precipitation'] = Spec(
            name='precipitation',
            dims=['LSOA'],
            coords={'LSOA': [1, 2, 3]},
            dtype='float',
            unit='incompatible'
        )

        with raises(ValueError) as ex:
            SosModel.from_dict(sos_model_dict, [sector_model, scenario_model, economic_model])
        assert "ml!=incompatible" in str(ex)

    def test_invalid_unit_conversion(self, sos_model_dict, sector_model, scenario_model,
                                     economic_model):
        """Error on invalid dependency
        """
        scenario_model.outputs['precipitation'] = Spec(
            name='precipitation',
            dims=['LSOA'],
            coords={'LSOA': [1, 2, 3]},
            dtype='float',
            unit='meter'
        )

        with raises(ValueError) as ex:
            SosModel.from_dict(sos_model_dict, [sector_model, scenario_model, economic_model])
        assert "meter!=ml" in str(ex.value)
