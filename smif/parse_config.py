"""Parse yaml config files, to construct sector models

"""
import jsonschema
import yaml

__author__ = "Tom Russell"
__copyright__ = "Tom Russell"
__license__ = "mit"


class ConfigParser:
    """Parse, hold and validate a yaml config file

    Arguments
    =========
    filepath : str
        Path to the yaml configuration file

    """
    def __init__(self, filepath=None):
        if filepath is not None:
            self._config_filepath = filepath

            with open(filepath, 'r') as fh:
                self.data = yaml.load(fh)
        else:
            self.data = None

    def validate(self, schema):
        """Validates the configuration file against a schema

        Arguments
        =========
        schema : dict
            A dictionary representing the expected structure of the
            configuration file
        """
        if self.data is None:
            raise AttributeError("Config data not loaded")

        jsonschema.validate(self.data, schema)
