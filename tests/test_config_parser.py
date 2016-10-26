"""Test config load and parse
"""
import json
import os

import jsonschema

import smif.parse_config
from pytest import fixture, raises


@fixture(scope="function")
def setup_schema():
    """Returns the json schema for model inputs

    Returns
    =======
    schema : dict
    """
    schema_filename = 'schema.json'
    schema_path = os.path.join(os.path.dirname(__file__),
                               "fixtures",
                               "config",
                               schema_filename)
    with open(schema_path, 'r') as sf:
        schema = json.load(sf)
    return schema


class TestConfigParser:

    def test_load_simple_config(self):
        path = os.path.join(os.path.dirname(__file__),
                            "fixtures",
                            "config",
                            "simple.yaml")
        conf = smif.parse_config.ConfigParser(path)
        assert conf.data["name"] == "test"

    def test_simple_validate_valid(self):
        conf = smif.parse_config.ConfigParser()
        conf.data = {"name": "test"}
        conf.validate({
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                },
                "required": ["name"]
            })

    def test_simple_validate_invalid(self):
        conf = smif.parse_config.ConfigParser()
        conf.data = {"name": "test"}

        msg = "'nonexistent_key' is a required property"
        with raises(jsonschema.exceptions.ValidationError, message=msg):
            conf.validate({
                "type": "object",
                "properties": {
                    "nonexistent_key": {"type": "string"}
                },
                "required": ["nonexistent_key"]
            })


class TestConfigParserWaterSupply:

    def test_water_supply_static(self):

        filename = 'water_supply_static_1.yaml'
        path = os.path.join(os.path.dirname(__file__),
                            "fixtures",
                            "config",
                            filename)
        conf = smif.parse_config.ConfigParser(path)

        actual = conf.data
        expected = {'decision variables': ['water treatment capacity'],
                    'parameters': ['raininess'],
                    'water treatment capacity': {'bounds': [0, 20],
                                                 'index': 0,
                                                 'value': 10
                                                 },
                    'raininess': {'bounds': [0, 5],
                                  'index': 0,
                                  'value': 3
                                  }
                    }
        assert actual == expected

    def test_water_supply_validation(self, setup_schema):

        filename = 'water_supply_static_1.yaml'
        path = os.path.join(os.path.dirname(__file__),
                            "fixtures",
                            "config",
                            filename)
        conf = smif.parse_config.ConfigParser(path)

        schema = setup_schema

        conf.validate(schema)

        actual = conf.data
        expected = {'decision variables': ['water treatment capacity'],
                    'parameters': ['raininess'],
                    'water treatment capacity': {'bounds': [0, 20],
                                                 'index': 0,
                                                 'value': 10
                                                 },
                    'raininess': {'bounds': [0, 5],
                                  'index': 0,
                                  'value': 3
                                  }
                    }
        assert actual == expected

    def test_water_supply_validation_multiple_params(self, setup_schema):

        filename = 'water_supply_static_2.yaml'
        path = os.path.join(os.path.dirname(__file__),
                            "fixtures",
                            "config",
                            filename)
        conf = smif.parse_config.ConfigParser(path)

        schema = setup_schema
        conf.validate(schema)

        actual = conf.data
        expected = {'decision variables': ['water treatment capacity',
                                           'decision lumpiness'],
                    'parameters': ['raininess',
                                   'discount rate',
                                   'arbitrariness'],
                    'water treatment capacity': {'bounds': [0, 20],
                                                 'index': 0,
                                                 'value': 10
                                                 },
                    'raininess': {'bounds': [0, 5],
                                  'index': 0,
                                  'value': 3
                                  }
                    }
        assert actual == expected
