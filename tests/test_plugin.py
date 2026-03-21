"""Tests for the CarConnectivity REST API plugin."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from carconnectivity_plugins.restapi.api.app import RestAPI, _check_auth


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_car_connectivity():
    """Return a minimal CarConnectivity mock."""
    cc = MagicMock()
    cc.plugins = MagicMock()
    cc.plugins.children = []
    cc.active_config = {}
    cc.config = {'carConnectivity': {}}
    return cc


def _make_rest_api(users=None, car_connectivity=None):
    """Create a RestAPI instance bound to localhost:0 (OS-assigned port)."""
    if car_connectivity is None:
        car_connectivity = _make_car_connectivity()
    if users is None:
        users = {'admin': 'secret'}
    # Use port 0 so the OS picks an available port
    api = RestAPI(car_connectivity=car_connectivity, host='127.0.0.1', port=0, users=users)
    return api


# ---------------------------------------------------------------------------
# _check_auth
# ---------------------------------------------------------------------------

class TestCheckAuth:
    def test_valid_credentials(self):
        assert _check_auth({'user': 'pass'}, 'user', 'pass') is True

    def test_wrong_password(self):
        assert _check_auth({'user': 'pass'}, 'user', 'wrong') is False

    def test_unknown_user(self):
        assert _check_auth({'user': 'pass'}, 'other', 'pass') is False

    def test_empty_users(self):
        assert _check_auth({}, 'user', 'pass') is False


# ---------------------------------------------------------------------------
# Flask test client helpers
# ---------------------------------------------------------------------------

def _auth_headers(username='admin', password='secret'):
    import base64
    token = base64.b64encode(f'{username}:{password}'.encode()).decode()
    return {'Authorization': f'Basic {token}'}


# ---------------------------------------------------------------------------
# Healthcheck (no auth required)
# ---------------------------------------------------------------------------

class TestHealthcheck:
    def test_healthcheck_no_auth(self):
        api = _make_rest_api()
        client = api.app.test_client()
        resp = client.get('/healthcheck')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Authentication enforcement
# ---------------------------------------------------------------------------

class TestAuthentication:
    def test_get_without_auth_returns_401(self):
        cc = _make_car_connectivity()
        cc.get_by_path = MagicMock(return_value=False)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.get('/')
        assert resp.status_code == 401

    def test_get_wrong_password_returns_401(self):
        cc = _make_car_connectivity()
        cc.get_by_path = MagicMock(return_value=False)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.get('/', headers=_auth_headers(password='wrong'))
        assert resp.status_code == 401

    def test_get_correct_auth_passes(self):
        from carconnectivity.objects import GenericObject
        cc = _make_car_connectivity()
        root = MagicMock(spec=GenericObject)
        root.enabled = True
        root.as_dict = MagicMock(return_value={})
        cc.get_by_path = MagicMock(return_value=root)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.get('/', headers=_auth_headers())
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET endpoint
# ---------------------------------------------------------------------------

class TestGetEndpoint:
    def test_get_unknown_path_returns_404(self):
        cc = _make_car_connectivity()
        cc.get_by_path = MagicMock(return_value=False)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.get('/unknown/path', headers=_auth_headers())
        assert resp.status_code == 404

    def test_get_disabled_element_returns_404(self):
        from carconnectivity.objects import GenericObject
        cc = _make_car_connectivity()
        element = MagicMock(spec=GenericObject)
        element.enabled = False
        cc.get_by_path = MagicMock(return_value=element)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.get('/some/path', headers=_auth_headers())
        assert resp.status_code == 404

    def test_get_object_returns_json(self):
        from carconnectivity.objects import GenericObject
        cc = _make_car_connectivity()
        element = MagicMock(spec=GenericObject)
        element.enabled = True
        element.as_dict = MagicMock(return_value={'key': 'value'})
        cc.get_by_path = MagicMock(return_value=element)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.get('/some/object', headers=_auth_headers())
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data == {'key': 'value'}

    def test_get_attribute_returns_json(self):
        from carconnectivity.attributes import GenericAttribute
        cc = _make_car_connectivity()
        element = MagicMock(spec=GenericAttribute)
        element.enabled = True
        element.as_dict = MagicMock(return_value={'val': 42})
        cc.get_by_path = MagicMock(return_value=element)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.get('/some/attr', headers=_auth_headers())
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data == {'val': 42}


# ---------------------------------------------------------------------------
# PUT endpoint
# ---------------------------------------------------------------------------

class TestPutEndpoint:
    def test_put_unknown_path_returns_404(self):
        cc = _make_car_connectivity()
        cc.get_by_path = MagicMock(return_value=False)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.put('/unknown', headers=_auth_headers(),
                          data=json.dumps({'value': 1}),
                          content_type='application/json')
        assert resp.status_code == 404

    def test_put_non_attribute_returns_400(self):
        from carconnectivity.objects import GenericObject
        cc = _make_car_connectivity()
        element = MagicMock(spec=GenericObject)
        element.enabled = True
        cc.get_by_path = MagicMock(return_value=element)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.put('/some/object', headers=_auth_headers(),
                          data=json.dumps({'value': 1}),
                          content_type='application/json')
        assert resp.status_code == 400

    def test_put_readonly_attribute_returns_403(self):
        from carconnectivity.attributes import GenericAttribute
        cc = _make_car_connectivity()
        element = MagicMock(spec=GenericAttribute)
        element.enabled = True
        element.is_changeable = False
        cc.get_by_path = MagicMock(return_value=element)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.put('/some/attr', headers=_auth_headers(),
                          data=json.dumps({'value': 1}),
                          content_type='application/json')
        assert resp.status_code == 403

    def test_put_missing_value_field_returns_400(self):
        from carconnectivity.attributes import GenericAttribute
        cc = _make_car_connectivity()
        element = MagicMock(spec=GenericAttribute)
        element.enabled = True
        element.is_changeable = True
        cc.get_by_path = MagicMock(return_value=element)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.put('/some/attr', headers=_auth_headers(),
                          data=json.dumps({'wrong_key': 1}),
                          content_type='application/json')
        assert resp.status_code == 400

    def test_put_valid_attribute_returns_200(self):
        from carconnectivity.attributes import GenericAttribute
        cc = _make_car_connectivity()
        element = MagicMock(spec=GenericAttribute)
        element.enabled = True
        element.is_changeable = True
        element.set_value = MagicMock()
        cc.get_by_path = MagicMock(return_value=element)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.put('/some/attr', headers=_auth_headers(),
                          data=json.dumps({'value': 80}),
                          content_type='application/json')
        assert resp.status_code == 200
        element.set_value.assert_called_once_with(80)

    def test_put_setter_error_returns_400(self):
        from carconnectivity.attributes import GenericAttribute
        from carconnectivity.errors import SetterError
        cc = _make_car_connectivity()
        element = MagicMock(spec=GenericAttribute)
        element.enabled = True
        element.is_changeable = True
        element.set_value = MagicMock(side_effect=SetterError('bad value'))
        cc.get_by_path = MagicMock(return_value=element)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.put('/some/attr', headers=_auth_headers(),
                          data=json.dumps({'value': -999}),
                          content_type='application/json')
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST endpoint
# ---------------------------------------------------------------------------

class TestPostEndpoint:
    def test_post_unknown_path_returns_404(self):
        cc = _make_car_connectivity()
        cc.get_by_path = MagicMock(return_value=False)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.post('/unknown', headers=_auth_headers(),
                           data=json.dumps({'value': 'start'}),
                           content_type='application/json')
        assert resp.status_code == 404

    def test_post_non_command_returns_400(self):
        from carconnectivity.objects import GenericObject
        cc = _make_car_connectivity()
        element = MagicMock(spec=GenericObject)
        element.enabled = True
        cc.get_by_path = MagicMock(return_value=element)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.post('/some/object', headers=_auth_headers(),
                           data=json.dumps({'value': 'start'}),
                           content_type='application/json')
        assert resp.status_code == 400

    def test_post_command_returns_200(self):
        from carconnectivity.commands import GenericCommand
        cc = _make_car_connectivity()
        element = MagicMock(spec=GenericCommand)
        element.enabled = True
        element.set_value = MagicMock()
        cc.get_by_path = MagicMock(return_value=element)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.post('/some/command', headers=_auth_headers(),
                           data=json.dumps({'value': 'start'}),
                           content_type='application/json')
        assert resp.status_code == 200
        element.set_value.assert_called_once_with('start')

    def test_post_missing_value_field_returns_400(self):
        from carconnectivity.commands import GenericCommand
        cc = _make_car_connectivity()
        element = MagicMock(spec=GenericCommand)
        element.enabled = True
        cc.get_by_path = MagicMock(return_value=element)
        api = _make_rest_api(car_connectivity=cc)
        client = api.app.test_client()
        resp = client.post('/some/command', headers=_auth_headers(),
                           data=json.dumps({'wrong': 'x'}),
                           content_type='application/json')
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Plugin class
# ---------------------------------------------------------------------------

class TestPlugin:
    def test_plugin_init_defaults(self):
        from carconnectivity_plugins.restapi.plugin import Plugin
        cc = _make_car_connectivity()
        with patch('carconnectivity_plugins.restapi.plugin.RestAPI') as MockRestAPI:
            MockRestAPI.return_value = MagicMock()
            MockRestAPI.return_value.server = MagicMock()
            plugin = Plugin(plugin_id='restapi', car_connectivity=cc, config={})
            assert plugin.active_config['port'] == 40000
            assert plugin.active_config['host'] == '0.0.0.0'
            assert plugin.active_config['https'] is False

    def test_plugin_custom_port(self):
        from carconnectivity_plugins.restapi.plugin import Plugin
        cc = _make_car_connectivity()
        with patch('carconnectivity_plugins.restapi.plugin.RestAPI') as MockRestAPI:
            MockRestAPI.return_value = MagicMock()
            MockRestAPI.return_value.server = MagicMock()
            plugin = Plugin(plugin_id='restapi', car_connectivity=cc, config={'port': 8080})
            assert plugin.active_config['port'] == 8080

    def test_plugin_invalid_port_raises(self):
        from carconnectivity_plugins.restapi.plugin import Plugin
        from carconnectivity.errors import ConfigurationError
        cc = _make_car_connectivity()
        with patch('carconnectivity_plugins.restapi.plugin.RestAPI'):
            with pytest.raises(ConfigurationError):
                Plugin(plugin_id='restapi', car_connectivity=cc, config={'port': 99999})

    def test_plugin_users_config(self):
        from carconnectivity_plugins.restapi.plugin import Plugin
        cc = _make_car_connectivity()
        config = {
            'username': 'admin',
            'password': 'secret',
        }
        with patch('carconnectivity_plugins.restapi.plugin.RestAPI') as MockRestAPI:
            MockRestAPI.return_value = MagicMock()
            MockRestAPI.return_value.server = MagicMock()
            plugin = Plugin(plugin_id='restapi', car_connectivity=cc, config=config)
            assert plugin.active_config['passwords'] == {'admin': 'secret'}

    def test_plugin_multiple_users_config(self):
        from carconnectivity_plugins.restapi.plugin import Plugin
        cc = _make_car_connectivity()
        config = {
            'users': [
                {'username': 'u1', 'password': 'p1'},
                {'username': 'u2', 'password': 'p2'},
            ]
        }
        with patch('carconnectivity_plugins.restapi.plugin.RestAPI') as MockRestAPI:
            MockRestAPI.return_value = MagicMock()
            MockRestAPI.return_value.server = MagicMock()
            plugin = Plugin(plugin_id='restapi', car_connectivity=cc, config=config)
            assert plugin.active_config['passwords'] == {'u1': 'p1', 'u2': 'p2'}

    def test_plugin_get_type(self):
        from carconnectivity_plugins.restapi.plugin import Plugin
        cc = _make_car_connectivity()
        with patch('carconnectivity_plugins.restapi.plugin.RestAPI') as MockRestAPI:
            MockRestAPI.return_value = MagicMock()
            MockRestAPI.return_value.server = MagicMock()
            plugin = Plugin(plugin_id='restapi', car_connectivity=cc, config={})
            assert plugin.get_type() == 'carconnectivity-plugin-restapi'

    def test_plugin_get_name(self):
        from carconnectivity_plugins.restapi.plugin import Plugin
        cc = _make_car_connectivity()
        with patch('carconnectivity_plugins.restapi.plugin.RestAPI') as MockRestAPI:
            MockRestAPI.return_value = MagicMock()
            MockRestAPI.return_value.server = MagicMock()
            plugin = Plugin(plugin_id='restapi', car_connectivity=cc, config={})
            assert plugin.get_name() == 'REST API Plugin'
