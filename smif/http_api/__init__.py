"""HTTP API endpoint
"""
import dateutil.parser

from flask import Flask, render_template, request, jsonify, current_app
from flask.views import MethodView

from smif.data_layer import (
    DataExistsError,
    DataMismatchError,
    DataNotFoundError
)


def create_app(static_folder='static', template_folder='templates', get_data_interface=None):
    """Create Flask app object
    """
    app = Flask(
        __name__,
        static_url_path='',
        static_folder=static_folder,
        template_folder=template_folder
    )
    # Pass get_data_interface method which must return an instance of a class
    # implementing DataInterface. There may be a better way!
    app.config.get_data_interface = get_data_interface

    register_routes(app)
    register_api_endpoints(app)
    register_error_handlers(app)

    return app


def register_routes(app):
    """Register plain routing
    """
    @app.route("/")
    def home():
        """Render single page
        """
        return render_template('index.html')


def register_api_endpoints(app):
    """Register API calls (using pluggable views)
    """
    register_api(app, SosModelRunAPI, 'sos_model_run_api', '/api/v1/sos_model_runs/',
                 key='sos_model_run_name', key_type='string')


def register_error_handlers(app):
    """Handle expected errors
    """
    @app.errorhandler(DataExistsError)
    def handle_exists(error):
        """Return 400 Bad Request if data to be created already exists
        """
        response = jsonify({"message": str(error)})
        response.status_code = 400
        return response

    @app.errorhandler(DataMismatchError)
    def handle_mismatch(error):
        """Return 400 Bad Request if data and id/name are mismatched
        """
        response = jsonify({"message": str(error)})
        response.status_code = 400
        return response

    @app.errorhandler(DataNotFoundError)
    def handle_not_found(error):
        """Return 404 if data is not found
        """
        response = jsonify({"message": str(error)})
        response.status_code = 404
        return response


class SosModelRunAPI(MethodView):
    """Implement CRUD operations for sos_model_run configuration data
    """
    def get(self, sos_model_run_name):
        """Get sos_model_runs
        all: GET /api/v1/sos_model_runs/
        one: GET /api/vi/sos_model_runs/name
        """
        # return str(current_app.config)
        data_interface = current_app.config.get_data_interface()
        if sos_model_run_name is None:
            data = data_interface.read_sos_model_runs()
            response = jsonify(data)
        else:
            data = data_interface.read_sos_model_run(sos_model_run_name)
            response = jsonify(data)

        return response

    def post(self):
        """Create a sos_model_run:
        POST /api/v1/sos_model_runs
        """
        data_interface = current_app.config.get_data_interface()
        data = request.get_json() or request.form
        data = check_timestamp(data)

        data_interface.write_sos_model_run(data)
        response = jsonify({"message": "success"})
        response.status_code = 201
        return response

    def put(self, sos_model_run_name):
        """Update a sos_model_run:
        PUT /api/v1/sos_model_runs
        """
        data_interface = current_app.config.get_data_interface()
        data = request.get_json() or request.form
        data = check_timestamp(data)
        data_interface.update_sos_model_run(sos_model_run_name, data)
        response = jsonify({})
        return response

    def delete(self, sos_model_run_name):
        """Delete a sos_model_run:
        DELETE /api/v1/sos_model_runs
        """
        data_interface = current_app.config.get_data_interface()
        data_interface.delete_sos_model_run(sos_model_run_name)
        response = jsonify({})
        return response


def register_api(app, view, endpoint, url, key='id', key_type='int'):
    """Register a MethodView as an endpoint with CRUD operations at a URL
    """
    view_func = view.as_view(endpoint)
    app.add_url_rule(url, defaults={key: None},
                     view_func=view_func, methods=['GET'])
    app.add_url_rule(url, view_func=view_func, methods=['POST'])
    app.add_url_rule('%s<%s:%s>' % (url, key_type, key), view_func=view_func,
                     methods=['GET', 'PUT', 'DELETE'])


def check_timestamp(data):
    """Check for timestamp and parse to datetime object
    """
    if 'stamp' in data:
        try:
            data['stamp'] = dateutil.parser.parse(data['stamp'])
        except(ValueError):
            pass
    return data