"""The decision module handles the three planning levels

Currently, only pre-specified planning is implemented.

The choices made in the three planning levels influence the set of interventions
and assets available within a model run.

The interventions available in a model run are stored in a dict keyed by name.

"""
__author__ = "Will Usher, Tom Russell"
__copyright__ = "Will Usher, Tom Russell"
__license__ = "mit"

import itertools
import os
from abc import ABCMeta, abstractmethod
from logging import getLogger
from types import MappingProxyType
from typing import Dict, List, Tuple

from smif.data_layer.data_handle import ResultsHandle
from smif.data_layer.model_loader import ModelLoader
from smif.data_layer.store import Store
from smif.exception import SmifDataNotFoundError, SmifTimestepResolutionError


class DecisionManager(object):
    """A DecisionManager is initialised with one or more model run strategies
    that refer to DecisionModules such as pre-specified planning,
    a rule-based models or multi-objective optimisation.
    These implementations influence the combination and ordering of decision
    iterations and model timesteps that need to be performed by the model runner.

    The DecisionManager presents a simple decision loop interface to the model runner,
    in the form of a generator which allows the model runner to iterate over the
    collection of independent simulations required at each step.

    The DecisionManager collates the output of the decision algorithms and
    writes the post-decision state through a ResultsHandle. This allows Models
    to access a given decision state (identified uniquely by timestep and
    decision iteration id).

    The :py:meth:`get_decisions` method passes a ResultsHandle down to a
    DecisionModule, allowing the DecisionModule to access model results from
    previous timesteps and decision iterations when making decisions

    Arguments
    ---------
    store: smif.data_layer.store.Store
    """

    def __init__(self, store: Store,
                 timesteps: List[int],
                 modelrun_name: str,
                 sos_model):

        self.logger = getLogger(__name__)

        self._store = store
        self._modelrun_name = modelrun_name
        self._sos_model = sos_model
        self._timesteps = timesteps
        self._decision_module = None

        self._register = {}  # type: Dict
        for sector_model in sos_model.sector_models:
            self._register.update(self._store.read_interventions(sector_model.name))
        self.planned_interventions = set()  # type: set

        strategies = self._store.read_strategies(modelrun_name)
        self.logger.info("%s strategies found", len(strategies))
        self.pre_spec_planning = self._set_up_pre_spec_planning(modelrun_name, strategies)
        self._set_up_decision_modules(modelrun_name, strategies)

    def _set_up_pre_spec_planning(self, modelrun_name, strategies):

        pre_spec_planning = None

        # Read in the historical interventions (initial conditions) directly
        initial_conditions = self._store.read_all_initial_conditions(modelrun_name)

        # Read in strategies
        planned_interventions = []
        planned_interventions.extend(initial_conditions)

        for index, strategy in enumerate(strategies):
            # Extract pre-specified planning interventions
            if strategy['type'] == 'pre-specified-planning':

                msg = "Adding %s planned interventions to pre-specified-planning %s"
                self.logger.info(msg, len(strategy['interventions']), index)

                planned_interventions.extend(strategy['interventions'])

        # Create a Pre-Specified planning decision module with all
        # the planned interventions
        if planned_interventions:
            pre_spec_planning = PreSpecified(self._timesteps,
                                             self._register,
                                             planned_interventions)
            self.planned_interventions = set([x['name'] for x in planned_interventions])

        return pre_spec_planning

    def _set_up_decision_modules(self, modelrun_name, strategies):

        strategy_types = [x['type'] for x in strategies
                          if x['type'] != 'pre-specified-planning']
        if len(set(strategy_types)) > 1:
            msg = "Cannot use more the 2 type of strategy simultaneously"
            raise NotImplementedError(msg)

        for strategy in strategies:

            if strategy['type'] != 'pre-specified-planning':

                loader = ModelLoader()

                # absolute path to be crystal clear for ModelLoader when loading python class
                strategy['path'] = os.path.normpath(
                    os.path.join(self._store.model_base_folder, strategy['path']))
                strategy['timesteps'] = self._timesteps
                # Pass a reference to the register of interventions
                strategy['register'] = MappingProxyType(self.available_interventions)

                strategy['name'] = strategy['classname'] + '_' + strategy['type']

                self.logger.debug("Trying to load strategy: %s", strategy['name'])
                decision_module = loader.load(strategy)
                self._decision_module = decision_module  # type: DecisionModule

    @property
    def available_interventions(self) -> Dict[str, Dict]:
        """Returns a register of available interventions, i.e. those not planned
        """
        edited_register = {name: self._register[name]
                           for name in self._register.keys() -
                           self.planned_interventions}
        return edited_register

    def update_planned_interventions(self, decisions: List[Tuple]):
        """Adds a list of decisions to the set of planned interventions
        """
        self.planned_interventions.update([x[1] for x in decisions])

    def get_intervention(self, value):
        try:
            return self._register[value]
        except KeyError:
            msg = ""
            raise SmifDataNotFoundError(msg.format(value))

    def decision_loop(self):
        """Generate bundles of simulation steps to run

        Each call to this method returns a dict:

            {
                'decision_iterations': list of decision iterations (int),
                'timesteps': list of timesteps (int),
                'decision_links': (optional) dict of {
                    decision iteration in current bundle: decision iteration of previous bundle
                }
            }

        A bundle is composed differently according to the implementation of the
        contained DecisionModule.  For example:

        With only pre-specified planning, there is a single step in the loop,
        with a single decision iteration with timesteps covering the entire model horizon.

        With a rule based approach, there might be many steps in the loop, each with a single
        decision iteration and single timestep, moving on once some threshold is satisfied.

        With a genetic algorithm, there might be a configurable number of steps in the loop,
        each with multiple decision iterations (one for each member of the algorithm's
        population) and timesteps covering the entire model horizon.

        Implicitly, if the bundle returned in an iteration contains multiple decision
        iterations, they can be performed in parallel. If each decision iteration contains
        multiple timesteps, they can also be parallelised, so long as there are no temporal
        dependencies.

        Decision links are only required if the bundle timesteps do not start from the first
        timestep of the model horizon.
    """
        self.logger.debug("Calling decision loop")
        if self._decision_module:
            while True:
                bundle = next(self._decision_module)
                if bundle is None:
                    break
                self.logger.debug("Bundle returned: %s", bundle)
                self._get_and_save_bundle_decisions(bundle)
                yield bundle
        else:
            bundle = {
                'decision_iterations': [0],
                'timesteps': [x for x in self._timesteps]
            }
            self._get_and_save_bundle_decisions(bundle)
            yield bundle

    def _get_and_save_bundle_decisions(self, bundle):
        """Iterate over bundle and write decisions

        Arguments
        ---------
        bundle : dict

        Returns
        -------
        bundle : dict
            One definitive bundle across the decision modules

        """
        for iteration, timestep in itertools.product(
                bundle['decision_iterations'],
                bundle['timesteps']):
            self.get_and_save_decisions(iteration, timestep)

    def get_and_save_decisions(self, iteration, timestep):
        """Retrieves decisions for given timestep and decision iteration from each decision
        module and writes them to the store as state.

        Calls each contained DecisionModule for the given timestep and decision iteration in
        the `data_handle`, retrieving a list of decision dicts (keyed by intervention name and
        build year).

        These decisions are then written to a state file using the data store.

        Arguments
        ---------
        timestep : int
        iteration : int

        Notes
        -----
        State contains all intervention names which are present in the system at
        the given ``timestep`` for the current ``iteration``. This must include
        planned interventions from a previous timestep that are still within
        their lifetime, and interventions picked by a decision module in the
        previous timesteps.

        After loading all historical interventions, and screening them to remove
        interventions from the previous timestep that have reached the end
        of their lifetime, new decisions are added to the list of current
        interventions.

        Finally, the new state file is written to disk.
        """
        results_handle = ResultsHandle(
            store=self._store,
            modelrun_name=self._modelrun_name,
            sos_model=self._sos_model,
            current_timestep=timestep,
            timesteps=self._timesteps,
            decision_iteration=iteration
        )

        # Decision module overrides pre-specified planning for obtaining state
        # from previous iteration
        pre_decision_state = set()
        if self._decision_module:
            previous_state = self._get_previous_state(self._decision_module, results_handle)
            pre_decision_state.update(previous_state)
        elif self.pre_spec_planning:
            previous_state = self._get_previous_state(self.pre_spec_planning, results_handle)
            pre_decision_state.update(previous_state)

        msg = "Pre-decision state at timestep %s and iteration %s:\n%s"
        self.logger.debug(msg,
                          timestep, iteration, pre_decision_state)

        new_decisions = set()
        if self._decision_module:
            decisions = self._get_decisions(self._decision_module,
                                            results_handle)
            new_decisions.update(decisions)
        if self.pre_spec_planning:
            decisions = self._get_decisions(self.pre_spec_planning,
                                            results_handle)
            new_decisions.update(decisions)

        self.logger.debug("New decisions at timestep %s and iteration %s:\n%s",
                          timestep, iteration, new_decisions)

        self.update_planned_interventions(new_decisions)
        # Post decision state is the union of the pre decision state set
        # and new decision set
        post_decision_state = self._untuplize_state(pre_decision_state | new_decisions)

        self.logger.debug("Post-decision state at timestep %s and iteration %s:\n%s",
                          timestep, iteration, post_decision_state)

        self.logger.debug(
            "Writing state for timestep %s and interation %s", timestep, iteration)

        if not post_decision_state:
            post_decision_state = [{'name': '', 'build_year': ''}]
        self._store.write_state(post_decision_state, self._modelrun_name, timestep, iteration)

    def _get_decisions(self,
                       decision_module: 'DecisionModule',
                       results_handle: ResultsHandle) -> List[Tuple[int, str]]:
        decisions = decision_module.get_decision(results_handle)
        return self._tuplize_state(decisions)

    def _get_previous_state(self,
                            decision_module: 'DecisionModule',
                            results_handle: ResultsHandle) -> List[Tuple[int, str]]:
        state_dict = decision_module.get_previous_state(results_handle)
        return self._tuplize_state(state_dict)

    @staticmethod
    def _tuplize_state(state: List[Dict]) -> List[Tuple[int, str]]:
        return [(x['build_year'], x['name']) for x in state]

    @staticmethod
    def _untuplize_state(state: List[Tuple[int, str]]) -> List[Dict]:
        return [{'build_year': x[0], 'name': x[1]} for x in state]


class DecisionModule(metaclass=ABCMeta):
    """Abstract class which provides the interface to user defined decision modules.

    These mechanisms could include a Rule-based Approach or Multi-objective Optimisation.

    This class provides two main methods, ``__next__`` which is normally
    called implicitly as a call to the class as an iterator, and ``get_decision()``
    which takes as arguments a smif.data_layer.data_handle.ResultsHandle object.

    Arguments
    ---------
    timesteps : list
        A list of planning timesteps
    register : dict
        Reference to a dict of iterventions
    """

    """Current iteration of the decision module
    """
    def __init__(self, timesteps: List[int], register: MappingProxyType):
        self.timesteps = timesteps
        self._register = register
        self.logger = getLogger(__name__)
        self._decisions = set()  # type: set

    def __next__(self) -> List[Dict]:
        return self._get_next_decision_iteration()

    @property
    def first_timestep(self):
        return min(self.timesteps)

    @property
    def last_timestep(self):
        return max(self.timesteps)

    @abstractmethod
    def get_previous_state(self, results_handle: ResultsHandle) -> List[Dict]:
        raise NotImplementedError

    @property
    def interventions(self) -> Dict[str, Dict]:
        """Return the collection of available interventions

        Available interventions are the subset of interventions that have not
        been implemented in a prior iteration or timestep

        Returns
        -------
        list
        """
        edited_register = {name: self._register[name] for name in self._register.keys()
                           - self.decisions}
        return edited_register

    @property
    def decisions(self) -> set:
        """The set of historical decisions

        Returns
        -------
        set

        Raises
        ------
        ValueError
            If a duplicate decision is added to the set of historical decisions
        """
        return self._decisions

    @decisions.setter
    def decisions(self, value: str):
        if value in self._decisions:
            msg = "Decision {} already exists in decision history"
            raise ValueError(msg.format(value))
        else:
            self._decisions.add(value)

    def update_decisions(self, decisions: List[Dict]):
        """Adds a list of decisions to the set of planned interventions
        """
        for decision in decisions:
            self.decisions = decision['name']
        self.logger.debug("Internal record of state updated to: %s", self.decisions)

    def get_intervention(self, name):
        """Return an intervention dict

        Returns
        -------
        dict
        """
        try:
            return self._register[name]
        except KeyError:
            msg = "Intervention '{}' is not found in the list of available interventions"
            raise SmifDataNotFoundError(msg.format(name))

    @abstractmethod
    def _get_next_decision_iteration(self) -> List[Dict]:
        """Implement to return the next decision iteration

        Within a list of decision-iteration/timestep pairs, the assumption is
        that all decision iterations can be run in parallel
        (otherwise only one will be returned) and within a decision interation,
        all timesteps may be run in parallel as long as there are no
        inter-timestep state dependencies

        Returns
        -------
        dict
            Yields a dictionary keyed by ``decision iterations`` whose values
            contain a list of iteration integers, ``timesteps`` whose values
            contain a list of timesteps run in each decision iteration and the
            optional ``decision_links`` which link the decision interation of the
            current bundle to that of the previous bundle::

            {
                'decision_iterations': list of decision iterations (int),
                'timesteps': list of timesteps (int),
                'decision_links': (optional) dict of {
                    decision iteration in current bundle: decision iteration of previous bundle
                }
            }
        """
        raise NotImplementedError

    @abstractmethod
    def get_decision(self, results_handle: ResultsHandle) -> List[Dict]:
        """Return decisions for a given timestep and decision iteration

        Parameters
        ----------
        results_handle : smif.data_layer.data_handle.ResultsHandle

        Returns
        -------
        list of dict

        Examples
        --------
        >>> register = {'intervention_a': {'capital_cost': {'value': 1234}}}
        >>> dm = DecisionModule([2010, 2015], register)
        >>> dm.get_decision(results_handle)
        [{'name': 'intervention_a', 'build_year': 2010}])
        """
        raise NotImplementedError


class PreSpecified(DecisionModule):
    """Pre-specified planning

    Parameters
    ----------
    timesteps : list
        A list of the timesteps included in the model horizon
    register : dict
        A dict of intervention dictionaries keyed by unique intervention name
    planned_interventions : list
        A list of dicts ``{'name': 'intervention_name', 'build_year': 2010}``
        representing historical or planned interventions
    """
    def __init__(self, timesteps, register, planned_interventions):
        super().__init__(timesteps, register)
        self._planned = planned_interventions

    def _get_next_decision_iteration(self):
        return {
            'decision_iterations': [0],
            'timesteps': [x for x in self.timesteps]
        }

    def get_previous_state(self,
                           results_handle: ResultsHandle,
                           iteration: int = None) -> List[Dict]:
        try:
            prev_timestep = results_handle.previous_timestep
            if iteration:
                prev_iteration = iteration
            else:
                prev_iteration = results_handle.decision_iteration
            return results_handle.get_state(prev_timestep, prev_iteration)
        except SmifTimestepResolutionError:
            return []

    def get_decision(self, results_handle) -> List[Dict]:
        """Return a dict of historical or planned interventions in current timestep

        Use lifetime attribute of named intervention to calculate if it is still
        present in the current state of the system

        Arguments
        ---------
        results_handle : smif.data_layer.data_handle.ResultsHandle
            A reference to a smif results handle

        Returns
        -------
        list of dict

        Examples
        --------
        >>> dm = PreSpecified([2010, 2015], register,
        [{'name': 'intervention_a', 'build_year': 2010}])
        >>> dm.get_decision(results_handle)
        [{'name': intervention_a', 'build_year': 2010}]
        """
        decisions = []
        timestep = results_handle.current_timestep

        for intervention in self._planned:
            build_year = int(intervention['build_year'])

            data = self._register[intervention['name']]
            lifetime = data['technical_lifetime']['value']

            if self.buildable(build_year, timestep) and \
               self.within_lifetime(build_year, timestep, lifetime):
                decisions.append(intervention)
        return decisions

    def buildable(self, build_year, timestep):
        """Interventions are deemed available if build_year is less than next timestep

        For example, if `a` is built in 2011 and timesteps are
        [2005, 2010, 2015, 2020] then buildable returns True for timesteps
        2010, 2015 and 2020 and False for 2005.
        """
        if not isinstance(build_year, (int, float)):
            msg = "Build Year should be an integer but is a {}"
            raise TypeError(msg.format(type(build_year)))
        if timestep not in self.timesteps:
            raise ValueError("Timestep not in model timesteps")
        index = self.timesteps.index(timestep)
        if index == len(self.timesteps) - 1:
            next_year = timestep + 1
        else:
            next_year = self.timesteps[index + 1]

        if int(build_year) < next_year:
            return True
        else:
            return False

    def within_lifetime(self, build_year, timestep, lifetime):
        """Interventions are deemed active if build_year + lifetime >= timestep

        Arguments
        ---------
        build_year : int
        timestep : int
        lifetime : int
        """
        if not isinstance(build_year, (int, float)):
            msg = "Build Year should be an integer but is a {}"
            raise TypeError(msg.format(type(build_year)))

        try:
            build_year = int(build_year)
        except ValueError:
            raise ValueError(
                "A build year must be a valid integer. Received {}.".format(build_year))

        try:
            lifetime = int(lifetime)
        except ValueError:
            lifetime = float("inf")
        if lifetime < 0:
            msg = "The value of lifetime cannot be negative"
            raise ValueError(msg)
        if timestep <= build_year + lifetime:
            return True
        else:
            return False


class RuleBased(DecisionModule):
    """Rule-base decision modules
    """

    def __init__(self, timesteps, register):
        super().__init__(timesteps, register)
        self.satisfied = False
        self.current_timestep = self.first_timestep
        self.current_iteration = 0
        # keep internal account of max iteration reached per timestep
        self._max_iteration_by_timestep = {self.first_timestep: 0}
        self.logger = getLogger(__name__)

    def get_previous_state(self, results_handle: ResultsHandle) -> List[Dict]:
        if self.current_timestep > self.first_timestep:
            prev_timestep = self.previous_timestep
            prev_iteration = self.get_previous_year_iteration()
            return results_handle.get_state(prev_timestep, prev_iteration)
        else:
            return []

    @property
    def next_timestep(self):
        index_current_timestep = self.timesteps.index(self.current_timestep)
        try:
            return self.timesteps[index_current_timestep + 1]
        except IndexError:
            return None

    @property
    def previous_timestep(self):
        index_current_timestep = self.timesteps.index(self.current_timestep)
        if index_current_timestep > 0:
            return self.timesteps[index_current_timestep - 1]
        else:
            return None

    def _get_next_decision_iteration(self):
        if self.satisfied and (self.current_timestep == self.last_timestep):
            return None
        elif self.satisfied and (self.current_timestep < self.last_timestep):
            self._max_iteration_by_timestep[self.current_timestep] = \
                self.current_iteration
            self.satisfied = False
            self.current_timestep = self.next_timestep
            self.current_iteration += 1
            return self._make_bundle()
        else:
            self.current_iteration += 1
            return self._make_bundle()

    def get_previous_year_iteration(self):
        iteration = self._max_iteration_by_timestep[self.previous_timestep]
        return iteration

    def _make_bundle(self):
        bundle = {'decision_iterations': [self.current_iteration],
                  'timesteps': [self.current_timestep]}

        if self.current_timestep > self.first_timestep:
            bundle['decision_links'] = {
                self.current_iteration: self._max_iteration_by_timestep[
                    self.previous_timestep]
            }
        return bundle

    def get_decision(self, results_handle) -> List[Dict]:
        return []
