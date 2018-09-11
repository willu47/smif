from copy import copy

import numpy as np
from pytest import fixture, mark, param, raises
from smif.data_layer import (DatabaseInterface, DataExistsError,
                             DatafileInterface, MemoryInterface)
from smif.metadata import Spec


@fixture(
    params=[
        'memory',
        'file',
        param('database', marks=mark.skip)]
    )
def init_handler(request, setup_empty_folder_structure):
    if request.param == 'memory':
        handler = MemoryInterface()
    elif request.param == 'file':
        base_folder = setup_empty_folder_structure
        handler = DatafileInterface(base_folder, 'local_csv')
    elif request.param == 'database':
        handler = DatabaseInterface()
        raise NotImplementedError

    return handler


@fixture
def handler(init_handler, model_run, get_sos_model, get_sector_model, strategies,
            unit_definitions, dimension, source_spec, sink_spec, coefficients, scenario,
            narrative):
    handler = init_handler
    handler.write_model_run(model_run)
    handler.write_sos_model(get_sos_model)
    handler.write_sector_model(get_sector_model)
    handler.write_strategies('test_modelrun', strategies)
    # could write state
    handler.write_unit_definitions(unit_definitions)
    handler.write_dimension(dimension)
    handler.write_coefficients(source_spec, sink_spec, coefficients)
    handler.write_scenario(scenario)
    handler.write_narrative(narrative)

    return handler


@fixture
def model_run():
    return {
        'name': 'test_modelrun',
        'timesteps': [2010, 2015, 2010]
    }


@fixture
def strategies():
    return [
        {
            'strategy': 'pre-specified-planning',
            'model_name': 'test_model',
            'interventions': [
                {'name': 'a', 'build_year': 2020},
                {'name': 'b', 'build_year': 2025},
            ]
        }
    ]


@fixture
def unit_definitions():
    return ['kg = kilograms']


@fixture
def dimension():
    return {'name': 'category', 'elements': [1, 2, 3]}


@fixture
def source_spec():
    return Spec(name='a', dtype='float', unit='ml')


@fixture
def sink_spec():
    return Spec(name='b', dtype='float', unit='ml')


@fixture
def coefficients():
    return np.array([[1]])


@fixture
def scenario():
    return {
        'name': 'mortality',
        'description': 'The annual mortality rate in UK population',
        'provides': [
            {
                'name': 'mortality',
                'dtype': 'float',
            }
        ],
        'variants': [
            {
                'name': 'low',
                'description': 'Mortality (Low)',
                'data': {
                    'mortality': 'mortality_low.csv',
                },
            }
        ]
    }


@fixture
def narrative():
    return {
        'name': 'technology',
        'description': 'Describes the evolution of technology',
        'provides': [
            {
                'name': 'smart_meter_savings',
                'dtype': 'float',
            }
        ],
        'variants': [
            {
                'name': 'high_tech_dsm',
                'description': 'High takeup of smart technology on the demand side',
                'data': {
                    'smart_meter_savings': 'high_tech_dsm.csv',
                },
            }
        ]
    }


@fixture
def state():
    return [
        {
            'name': 'test_intervention',
            'build_year': 1900
        }
    ]


class TestModelRuns:
    """Read, write, update model runs
    """
    def test_read_model_runs(self, handler, model_run):
        actual = handler.read_model_runs()
        expected = [model_run]
        assert actual == expected

    def test_read_model_run(self, handler, model_run):
        assert handler.read_model_run('test_modelrun') == model_run

    def test_write_model_run(self, handler, model_run):
        new_model_run = {
            'name': 'new_model_run_name',
            'description': 'Model run 2'
        }
        handler.write_model_run(new_model_run)
        actual = handler.read_model_runs()
        expected = [model_run, new_model_run]
        assert (actual == expected) or (list(reversed(actual)) == expected)

    def test_update_model_run(self, handler):
        updated_model_run = {
            'name': 'test_modelrun',
            'description': 'Model run'
        }
        handler.update_model_run('test_modelrun', updated_model_run)
        assert handler.read_model_runs() == [updated_model_run]

    def test_delete_model_run(self, handler):
        handler.delete_model_run('test_modelrun')
        assert handler.read_model_runs() == []


class TestSosModel:
    """Read, write, update, delete SosModel config
    """
    def test_read_sos_models(self, handler, get_sos_model):
        handler = handler
        actual = handler.read_sos_models()
        expected = [get_sos_model]
        assert actual == expected

    def test_read_sos_model(self, handler, get_sos_model):
        assert handler.read_sos_model('energy') == get_sos_model

    def test_write_sos_model(self, handler, get_sos_model):
        new_sos_model = copy(get_sos_model)
        new_sos_model['name'] = 'another_sos_model'
        handler.write_sos_model(new_sos_model)
        actual = handler.read_sos_models()
        expected = [get_sos_model, new_sos_model]
        assert (actual == expected) or (list(reversed(actual)) == expected)

    def test_write_existing_sos_model(self, handler):
        handler = handler
        with raises(DataExistsError):
            handler.write_sos_model({'name': 'energy'})

    def test_update_sos_model(self, handler, get_sos_model):
        updated_sos_model = copy(get_sos_model)
        updated_sos_model['sector_models'] = ['energy_demand']
        handler.update_sos_model('energy', updated_sos_model)
        assert handler.read_sos_models() == [updated_sos_model]

    def test_delete_sos_model(self, handler):
        handler.delete_sos_model('energy')
        assert handler.read_sos_models() == []


class TestSectorModel():
    """Read/write/update/delete SectorModel config
    """
    def test_read_sector_models(self, handler, get_sector_model):
        actual = handler.read_sector_models()
        expected = [get_sector_model]
        assert actual == expected

    def test_read_sector_model(self, handler, get_sector_model):
        actual = handler.read_sector_model(get_sector_model['name'])
        expected = get_sector_model
        assert actual == expected

    def test_write_sector_model(self, handler, get_sector_model):
        new_sector_model = copy(get_sector_model)
        new_sector_model['name'] = 'another_energy_sector_model'
        handler.write_sector_model(new_sector_model)
        actual = handler.read_sector_models()
        expected = [get_sector_model, new_sector_model]
        assert (actual == expected) or (list(reversed(actual)) == expected)

    def test_update_sector_model(self, handler, get_sector_model):
        name = get_sector_model['name']
        expected = copy(get_sector_model)
        expected['inputs'] = ['energy_use']
        handler.update_sector_model(name, expected)
        actual = handler.read_sector_model(name)
        assert actual == expected

    def test_delete_sector_model(self, handler, get_sector_model):
        handler.delete_sector_model(get_sector_model['name'])
        expected = []
        actual = handler.read_sector_models()
        assert actual == expected


class TestStrategies():
    """Read strategies data
    """
    def test_read_strategies(self, handler, strategies):
        expected = strategies
        actual = handler.read_strategies('test_modelrun')
        assert actual == expected


class TestState():
    """Read and write state
    """
    def test_read_write_state(self, handler, state):
        expected = state
        modelrun_name = 'test_modelrun'
        timestep = 2020
        decision_iteration = None

        handler.write_state(expected, modelrun_name, timestep, decision_iteration)
        actual = handler.read_state(modelrun_name, timestep, decision_iteration)
        assert actual == expected


class TestUnits():
    """Read units definitions
    """
    def test_read_units(self, handler, unit_definitions):
        expected = unit_definitions
        actual = handler.read_unit_definitions()
        assert actual == expected


class TestDimensions():
    """Read/write/update/delete dimensions
    """
    def test_read_dimensions(self, handler, dimension):
        assert handler.read_dimensions() == [dimension]

    def test_read_dimension(self, handler, dimension):
        assert handler.read_dimension('category') == dimension

    def test_write_dimension(self, handler, dimension):
        another_dimension = {'name': '3rd', 'elements': ['a', 'b']}
        handler.write_dimension(another_dimension)
        assert handler.read_dimensions() == [dimension, another_dimension]

    def test_update_dimension(self, handler, dimension):
        another_dimension = {'name': 'category', 'elements': [4, 5, 6]}
        handler.update_dimension('category', another_dimension)
        assert handler.read_dimensions() == [another_dimension]

    def test_delete_dimension(self, handler):
        handler.delete_dimension('category')
        assert handler.read_dimensions() == []


class TestCoefficients():
    """Read/write conversion coefficients
    """
    def test_read_coefficients(self, source_spec, sink_spec, handler, coefficients):
        actual = handler.read_coefficients(source_spec, sink_spec)
        expected = np.array([[1]])
        np.testing.assert_equal(actual, expected)

    def test_write_coefficients(self, source_spec, sink_spec, handler, coefficients):
        expected = np.array([[2]])
        handler.write_coefficients(source_spec, sink_spec, expected)
        actual = handler.read_coefficients(source_spec, sink_spec)
        np.testing.assert_equal(actual, expected)


class TestScenarios():
    """Read and write scenario data
    """
    def test_read_scenarios(self, scenario, handler):
        assert handler.read_scenarios() == [scenario]

    def test_read_scenario(self, scenario, handler):
        assert handler.read_scenario('mortality') == scenario

    def test_write_scenario(self, scenario, handler):
        another_scenario = {
            'name': 'fertility',
            'description': 'Projected annual fertility rates',
            'variants': []
        }
        handler.write_scenario(another_scenario)
        assert handler.read_scenarios() == [scenario, another_scenario]

    def test_update_scenario(self, scenario, handler):
        another_scenario = {
            'name': 'mortality',
            'description': 'Projected annual mortality rates',
            'variants': []
        }
        handler.update_scenario('mortality', another_scenario)
        assert handler.read_scenarios() == [another_scenario]

    def test_delete_scenario(self, handler):
        handler.delete_scenario('mortality')
        assert handler.read_scenarios() == []

    def test_read_scenario_variants(self, handler, scenario):
        actual = handler.read_scenario_variants('mortality')
        expected = scenario['variants']
        assert actual == expected

    def test_read_scenario_variant(self, handler, scenario):
        actual = handler.read_scenario_variant('mortality', 'low')
        expected = scenario['variants'][0]
        assert actual == expected

    def test_write_scenario_variant(self, handler, scenario):
        new_variant = {
            'name': 'high',
            'description': 'Mortality (High)',
            'data': {
                'mortality': 'mortality_high.csv'
            }
        }
        handler.write_scenario_variant('mortality', new_variant)
        actual = handler.read_scenario_variants('mortality')
        expected = [new_variant] + scenario['variants']
        assert (actual == expected) or (actual == list(reversed(expected)))

    def test_update_scenario_variant(self, handler, scenario):
        new_variant = {
            'name': 'low',
            'description': 'Mortality (Low)',
            'data': {
                'mortality': 'mortality_low.csv'
            }
        }
        handler.update_scenario_variant('mortality', 'low', new_variant)
        actual = handler.read_scenario_variants('mortality')
        expected = [new_variant]
        assert actual == expected

    def test_delete_scenario_variant(self, handler, scenario):
        handler.delete_scenario_variant('mortality', 'low')
        assert handler.read_scenario_variants('mortality') == []

    def test_read_scenario_variant_data(self, get_remapped_scenario_data):
        """Read from in-memory data
        """
        data, spec = get_remapped_scenario_data
        handler = MemoryInterface()
        handler._scenario_data[('test_scenario', 'variant', 'parameter', 2010)] = data
        assert handler.read_scenario_variant_data(
            'test_scenario', 'variant', 'parameter', 2010) == data

    def test_write_scenario_variant_data(self, get_remapped_scenario_data):
        """Write to in-memory data
        """
        data, spec = get_remapped_scenario_data
        handler = MemoryInterface()
        handler.write_scenario_variant_data(
            data, 'test_scenario', 'variant', 'parameter', 2010)
        assert handler._scenario_data[('test_scenario', 'variant', 'parameter', 2010)] == data


class TestNarratives():
    """Read and write narrative data
    """
    def test_read_narratives(self, narrative, handler):
        assert handler.read_narratives() == [narrative]

    def test_read_narrative(self, narrative, handler):
        assert handler.read_narrative('technology') == narrative

    def test_write_narrative(self, narrative, handler):
        another_narrative = {
            'name': 'policy',
            'description': 'Parameters decribing policy effects on demand',
            'variants': []
        }
        handler.write_narrative(another_narrative)
        assert handler.read_narratives() == [narrative, another_narrative]

    def test_update_narrative(self, narrative, handler):
        another_narrative = {
            'name': 'technology',
            'description': 'Technology development, adoption and diffusion',
            'variants': []
        }
        handler.update_narrative('technology', another_narrative)
        assert handler.read_narratives() == [another_narrative]

    def test_delete_narrative(self, handler):
        handler.delete_narrative('technology')
        assert handler.read_narratives() == []

    def test_read_narrative_variants(self, handler, narrative):
        actual = handler.read_narrative_variants('technology')
        expected = narrative['variants']
        assert actual == expected

    def test_read_narrative_variant(self, handler, narrative):
        actual = handler.read_narrative_variant('technology', 'high_tech_dsm')
        expected = narrative['variants'][0]
        assert actual == expected

    def test_write_narrative_variant(self, handler, narrative):
        new_variant = {
            'name': 'precautionary',
            'description': 'Slower take-up of smart demand-response technologies',
            'data': {
                'technology': 'precautionary.csv'
            }
        }
        handler.write_narrative_variant('technology', new_variant)
        actual = handler.read_narrative_variants('technology')
        expected = [new_variant] + narrative['variants']
        assert (actual == expected) or (actual == list(reversed(expected)))

    def test_update_narrative_variant(self, handler, narrative):
        new_variant = {
            'name': 'high_tech_dsm',
            'description': 'High takeup of smart technology on the demand side (v2)',
            'data': {
                'technology': 'high_tech_dsm_v2.csv'
            }
        }
        handler.update_narrative_variant('technology', 'high_tech_dsm', new_variant)
        actual = handler.read_narrative_variants('technology')
        expected = [new_variant]
        assert actual == expected

    def test_delete_narrative_variant(self, handler, narrative):
        handler.delete_narrative_variant('technology', 'high_tech_dsm')
        assert handler.read_narrative_variants('technology') == []

    def test_read_narrative_variant_data(self, get_remapped_scenario_data):
        """Read from in-memory data
        """
        data, spec = get_remapped_scenario_data
        handler = MemoryInterface()
        handler._narrative_data[('technology', 'high_tech_dsm', 'param', 2010)] = data
        assert handler.read_narrative_variant_data(
            'technology', 'high_tech_dsm', 'param', 2010) == data

    def test_write_narrative_variant_data(self, get_remapped_scenario_data):
        """Write to in-memory data
        """
        data, spec = get_remapped_scenario_data
        handler = MemoryInterface()
        handler.write_narrative_variant_data(
            data, 'technology', 'high_tech_dsm', 'param', 2010)
        assert handler._narrative_data[('technology', 'high_tech_dsm', 'param', 2010)] == data


class TestResults():
    """Read/write results and prepare warm start
    """
    def test_read_write_results(self, handler):
        results_in = np.array(1)
        modelrun_name = 'test_modelrun'
        model_name = 'energy'
        timestep = 2010
        output_spec = Spec(name='energy_use', dtype='float')

        handler.write_results(results_in, modelrun_name, model_name, output_spec, timestep)
        results_out = handler.read_results(modelrun_name, model_name, output_spec, timestep)
        assert results_in == results_out

    def test_warm_start(self, handler):
        """Warm start should return None if no results are available
        """
        start = handler.prepare_warm_start('test_modelrun')
        assert start is None
