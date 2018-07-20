import React, { Component } from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'

import { fetchScenarios } from 'actions/actions.js'
import { saveScenario } from 'actions/actions.js'
import { createScenario } from 'actions/actions.js'
import { deleteScenario } from 'actions/actions.js'
import { fetchScenarioSet } from 'actions/actions.js'
import { saveScenarioSet } from 'actions/actions.js'
import { fetchSosModelRuns } from 'actions/actions.js'
import { fetchSosModels } from 'actions/actions.js'

import ScenarioSetConfigForm from 'components/ConfigForm/ScenarioSetConfigForm.js'

class ScenarioSetConfig extends Component {
    constructor(props) {
        super(props)
        this.init = true

        this.saveScenarioSet = this.saveScenarioSet.bind(this)
        this.saveScenario = this.saveScenario.bind(this)
        this.createScenario = this.createScenario.bind(this)
        this.deleteScenario = this.deleteScenario.bind(this)

        this.returnToPreviousPage = this.returnToPreviousPage.bind(this)

        this.config_name = this.props.match.params.name
    }

    componentDidMount() {
        const { dispatch } = this.props

        dispatch(fetchScenarioSet(this.config_name))
        dispatch(fetchScenarios())
        dispatch(fetchSosModels())
        dispatch(fetchSosModelRuns())
    }

    componentDidUpdate() {
        const { dispatch } = this.props

        if (this.config_name != this.props.match.params.name) {
            this.config_name = this.props.match.params.name
            dispatch(fetchScenarioSet(this.config_name))
        }
    }

    saveScenarioSet(ScenarioSet) {
        const { dispatch } = this.props
        dispatch(saveScenarioSet(ScenarioSet))
        this.returnToPreviousPage()
    }

    saveScenario(Scenario) {
        const { dispatch } = this.props
        dispatch(saveScenario(Scenario))
    }

    createScenario(scenario) {
        const { dispatch } = this.props
        dispatch(createScenario(
            {
                name: scenario['name'],
                description: scenario['description'],
                facets: scenario['facets'],
                scenario_set: this.props.scenario_set['name']
            }
        ))
    }

    deleteScenario(scenario) {
        const { dispatch } = this.props
        dispatch(deleteScenario(scenario))
    }

    returnToPreviousPage() {
        this.props.history.push('/configure/scenario-set')
    }

    renderLoading() {
        return (
            <div className="alert alert-primary">
                Loading...
            </div>
        )
    }

    renderError() {
        return (
            <div className="alert alert-danger">
                Error
            </div>
        )
    }

    renderScenarioSetConfig(sos_model_runs, sos_models, scenario_set, scenarios) {
        return (
            <div key={'scenarioset_' + scenario_set.name}>
                <ScenarioSetConfigForm
                    sosModelRuns={sos_model_runs}
                    sosModels={sos_models}
                    scenarioSet={scenario_set}
                    scenarios={scenarios}
                    saveScenarioSet={this.saveScenarioSet}
                    createScenario={this.createScenario}
                    deleteScenario={this.deleteScenario}
                    saveScenario={this.saveScenario}
                    cancelScenarioSet={this.returnToPreviousPage}/>
            </div>
        )
    }

    render () {
        const {sos_model_runs, sos_models, scenarios, scenario_set, isFetching} = this.props

        if (isFetching && this.init) {
            return this.renderLoading()
        } else {
            this.init = false
            return this.renderScenarioSetConfig(sos_model_runs, sos_models, scenario_set, scenarios)
        }
    }
}

ScenarioSetConfig.propTypes = {
    sos_model_runs: PropTypes.array.isRequired,
    sos_models: PropTypes.array.isRequired,
    scenario_set: PropTypes.object.isRequired,
    scenarios: PropTypes.array.isRequired,
    isFetching: PropTypes.bool.isRequired,
    dispatch: PropTypes.func.isRequired,
    match: PropTypes.object.isRequired,
    history: PropTypes.object.isRequired
}

function mapStateToProps(state) {

    return {
        sos_model_runs: state.sos_model_runs.items,
        sos_models: state.sos_models.items,
        scenario_set: state.scenario_set.item,
        scenarios: state.scenarios.items,
        isFetching: (
            state.sos_model_runs.isFetching ||
            state.sos_models.isFetching ||
            state.scenario_set.isFetching ||
            state.scenarios.isFetching
        )
    }
}

export default connect(mapStateToProps)(ScenarioSetConfig)