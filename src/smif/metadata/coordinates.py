"""Dimensions are always finite, and data which has a given dimension can be indexed by a
set of coordinates

Dimensions might be indexed over a grid::

>>> x = Coordinates('x', range(0, 100))
>>> y = Coordinates('y', range(0, 100))

A dimension might be a subset of Local Authority Districts in England::

>>> local_authority_districts = Coordinates('LADs', ['E07000128', 'E07000180'])

Or each of the economic sectors from the International Standard Industrial Classification of
All Economic Activities (ISIC), revision 4::

>>> economic_sector = Coordinates('ISICrev4', [
    {'name': 'A', 'short_desc': 'Agriculture, forestry and fishing'},
    {'name': 'B', 'short_desc': 'Mining and quarrying'},
    {'name': 'C', 'short_desc': 'Manufacturing'},
    {'name': 'D', 'short_desc': 'Electricity, gas, steam and air conditioning supply'}
])
"""


class Coordinates(object):
    """Coordinates index a dimension

    A dict of {Coordinates.dim: Coordinates.ids} can be passed to a Spec (or
    xarray.DataArray)
    """
    def __init__(self, name, elements):
        self.name = name
        self._ids = None
        self._elements = None
        self._set_elements(elements)

    def __eq__(self, other):
        return self.name == other.name \
            and self.elements == other.elements

    def __hash__(self):
        return hash(tuple(frozenset(e.items()) for e in self._elements))

    def __repr__(self):
        return "<Coordinates name='{}' elements={}>".format(self.name, self.ids)

    @property
    def elements(self):
        """Elements are a list of dicts with at least an 'id' key

        Coordinate elements should not be changed.
        """
        return self._elements

    @property
    def ids(self):
        """Element ids is a list of coordinate identifiers
        """
        return self._ids

    def _set_elements(self, elements):
        """Set elements with a list of ids (string or numeric) or dicts (including key 'id')
        """
        if not elements:
            raise ValueError("Coordinates.elements must not be empty")

        try:
            len(elements)
        except TypeError:
            raise ValueError("Coordinate.elements must be finite in length")

        if isinstance(elements[0], dict):
            if "name" not in elements[0]:
                raise KeyError("Coordinates.elements must have a name field, or be a " +
                               "simple list of identifiers")

            self._ids = [e['name'] for e in elements]
            self._elements = elements
        else:
            self._ids = elements
            self._elements = [{"name": e} for e in elements]

    @property
    def dim(self):
        """Dim (dimension) is an alias for Coordinates.name
        """
        return self.name

    @dim.setter
    def dim(self, dim):
        """Set name as dim
        """
        self.name = dim
