"""Module implementing the Flask-based REST API for CarConnectivity."""
from __future__ import annotations
from typing import TYPE_CHECKING

import logging
import functools

import flask
from werkzeug.serving import make_server, _TSSLContextArg

from carconnectivity.objects import GenericObject
from carconnectivity.attributes import GenericAttribute
from carconnectivity.commands import GenericCommand
from carconnectivity.errors import SetterError

if TYPE_CHECKING:
    from typing import Dict, Optional
    from carconnectivity.carconnectivity import CarConnectivity
    from werkzeug.serving import BaseWSGIServer

LOG: logging.Logger = logging.getLogger("carconnectivity.plugins.restapi")


class NoHealthcheck(logging.Filter):  # pylint: disable=too-few-public-methods
    """Logging filter that suppresses healthcheck request logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        return 'GET /healthcheck' not in record.getMessage()


def _check_auth(users: Dict[str, str], username: str, password: str) -> bool:
    """Verify username/password against the configured users dictionary."""
    return username in users and users[username] == password


def _require_auth(users: Dict[str, str]):
    """Decorator factory that enforces HTTP Basic Authentication."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            auth = flask.request.authorization
            if not auth or not _check_auth(users, auth.username, auth.password):
                return flask.Response(
                    'Unauthorized',
                    401,
                    {'WWW-Authenticate': 'Basic realm="CarConnectivity REST API"'},
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


class RestAPI:  # pylint: disable=too-few-public-methods
    """
    REST API server for CarConnectivity.

    Exposes CarConnectivity's object tree via a simple HTTP REST interface:
      GET  /<path>  – retrieve an object or attribute as JSON
      PUT  /<path>  – set the value of a writable attribute
      POST /<path>  – execute a command (writable GenericCommand attribute)
    """

    def __init__(
        self,
        car_connectivity: CarConnectivity,
        host: str,
        port: int,
        users: Optional[Dict[str, str]] = None,
        ssl_context: Optional[_TSSLContextArg] = None,
    ) -> None:
        self.car_connectivity: CarConnectivity = car_connectivity
        self.users: Dict[str, str] = users if users is not None else {}

        self.app = flask.Flask('CarConnectivity-RestAPI')

        # Suppress healthcheck noise from werkzeug logs
        logging.getLogger('werkzeug').addFilter(NoHealthcheck())

        require_auth = _require_auth(self.users)

        # ------------------------------------------------------------------
        # Routes
        # ------------------------------------------------------------------

        @self.app.route('/healthcheck', methods=['GET'])
        def healthcheck():  # pylint: disable=unused-variable
            return flask.Response('OK', 200)

        @self.app.route('/', defaults={'path': ''}, methods=['GET'])
        @self.app.route('/<path:path>', methods=['GET'])
        @require_auth
        def get_element(path: str):  # pylint: disable=unused-variable
            element = self.car_connectivity.get_by_path(path)
            if element is False or element is None:
                return flask.Response(
                    flask.json.dumps({'error': f'Path not found: /{path}'}),
                    404,
                    content_type='application/json',
                )
            if not element.enabled:
                return flask.Response(
                    flask.json.dumps({'error': f'Element at /{path} is not enabled'}),
                    404,
                    content_type='application/json',
                )
            result = element.as_json()
            return flask.Response(
                result,
                200,
                content_type='application/json',
            )

        @self.app.route('/', defaults={'path': ''}, methods=['PUT'])
        @self.app.route('/<path:path>', methods=['PUT'])
        @require_auth
        def put_element(path: str):  # pylint: disable=unused-variable
            element = self.car_connectivity.get_by_path(path)
            if element is False or element is None:
                return flask.Response(
                    flask.json.dumps({'error': f'Path not found: /{path}'}),
                    404,
                    content_type='application/json',
                )
            if not isinstance(element, GenericAttribute):
                return flask.Response(
                    flask.json.dumps({'error': f'Element at /{path} is not an attribute and cannot be set'}),
                    400,
                    content_type='application/json',
                )
            if not element.is_changeable:
                return flask.Response(
                    flask.json.dumps({'error': f'Attribute at /{path} is read-only'}),
                    403,
                    content_type='application/json',
                )
            request_data = flask.request.get_json(silent=True)
            if request_data is None or 'value' not in request_data:
                return flask.Response(
                    flask.json.dumps({'error': 'Request body must be JSON with a "value" field'}),
                    400,
                    content_type='application/json',
                )
            try:
                element.set_value(request_data['value'])
            except SetterError as err:
                return flask.Response(
                    flask.json.dumps({'error': str(err)}),
                    400,
                    content_type='application/json',
                )
            except Exception as err:  # pylint: disable=broad-except
                LOG.error('Unexpected error setting value at /%s: %s', path, err)
                return flask.Response(
                    flask.json.dumps({'error': str(err)}),
                    500,
                    content_type='application/json',
                )
            return flask.Response(
                flask.json.dumps({'status': 'ok'}),
                200,
                content_type='application/json',
            )

        @self.app.route('/', defaults={'path': ''}, methods=['POST'])
        @self.app.route('/<path:path>', methods=['POST'])
        @require_auth
        def post_element(path: str):  # pylint: disable=unused-variable
            element = self.car_connectivity.get_by_path(path)
            if element is False or element is None:
                return flask.Response(
                    flask.json.dumps({'error': f'Path not found: /{path}'}),
                    404,
                    content_type='application/json',
                )
            if not isinstance(element, GenericCommand):
                return flask.Response(
                    flask.json.dumps({'error': f'Element at /{path} is not a command'}),
                    400,
                    content_type='application/json',
                )
            request_data = flask.request.get_json(silent=True)
            if request_data is None or 'value' not in request_data:
                return flask.Response(
                    flask.json.dumps({'error': 'Request body must be JSON with a "value" field'}),
                    400,
                    content_type='application/json',
                )
            try:
                element.set_value(request_data['value'])
            except SetterError as err:
                return flask.Response(
                    flask.json.dumps({'error': str(err)}),
                    400,
                    content_type='application/json',
                )
            except Exception as err:  # pylint: disable=broad-except
                LOG.error('Unexpected error executing command at /%s: %s', path, err)
                return flask.Response(
                    flask.json.dumps({'error': str(err)}),
                    500,
                    content_type='application/json',
                )
            return flask.Response(
                flask.json.dumps({'status': 'ok'}),
                200,
                content_type='application/json',
            )

        # Register the GenericObject as a JSON encoder hint so that Flask can
        # serialise values that are not natively JSON-serialisable (e.g. enums,
        # datetime objects).  We handle this by relying on CarConnectivity's own
        # as_dict() which returns plain Python types.
        self.server: BaseWSGIServer = make_server(host, port, self.app, threaded=True, ssl_context=ssl_context)
