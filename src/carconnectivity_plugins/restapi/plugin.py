"""Module implements the plugin to provide a REST API for CarConnectivity."""
from __future__ import annotations
from typing import TYPE_CHECKING

import logging
import threading

from werkzeug.serving import _TSSLContextArg

from carconnectivity.errors import ConfigurationError
from carconnectivity.util import config_remove_credentials
from carconnectivity_plugins.base.plugin import BasePlugin
from carconnectivity_plugins.restapi.api.app import RestAPI
try:
    from carconnectivity_plugins.restapi._version import __version__
except ImportError:
    __version__ = 'unknown'

if TYPE_CHECKING:
    from typing import Dict, Optional
    from carconnectivity.carconnectivity import CarConnectivity

LOG: logging.Logger = logging.getLogger("carconnectivity.plugins.restapi")


class Plugin(BasePlugin):
    """
    Plugin class providing a REST API for CarConnectivity.

    The REST API allows external clients to:
      - GET  data from the CarConnectivity object tree
      - PUT  writable attributes to change values
      - POST commands with their arguments

    Args:
        plugin_id (str): Unique identifier for this plugin instance.
        car_connectivity (CarConnectivity): The CarConnectivity instance.
        config (Dict): Configuration dictionary for the plugin.
    """

    # pylint: disable-next=too-many-branches,too-many-statements
    def __init__(
        self,
        plugin_id: str,
        car_connectivity: CarConnectivity,
        config: Dict,
        *args,
        initialization: Optional[Dict] = None,
        **kwargs,
    ) -> None:
        BasePlugin.__init__(
            self,
            plugin_id=plugin_id,
            car_connectivity=car_connectivity,
            config=config,
            log=LOG,
            *args,
            initialization=initialization,
            **kwargs,
        )

        self._rest_thread: Optional[threading.Thread] = None

        werkzeug_logger: logging.Logger = logging.getLogger('werkzeug')
        if 'log_level' in self.active_config and self.active_config['log_level'] is not None:
            werkzeug_logger.setLevel(self.active_config['log_level'])
        werkzeug_logger.addHandler(self.log_storage)

        # Host
        if 'host' not in config or not config['host']:
            self.active_config['host'] = '0.0.0.0'  # nosec
        else:
            self.active_config['host'] = config['host']

        # Port
        if 'port' in config and config['port'] is not None:
            self.active_config['port'] = config['port']
            if not self.active_config['port'] or self.active_config['port'] < 1 or self.active_config['port'] > 65535:
                raise ConfigurationError('Invalid port specified in config ("port" out of range, must be 1-65535)')
        else:
            self.active_config['port'] = 40000

        # Users / Basic Authentication
        users: Dict[str, str] = {}
        if 'username' in config and config['username'] is not None \
                and 'password' in config and config['password'] is not None:
            users[config['username']] = config['password']

        if 'users' in config and config['users'] is not None:
            for user in config['users']:
                if 'username' in user and 'password' in user:
                    users[user['username']] = user['password']
        self.active_config['passwords'] = users

        # HTTPS / SSL
        ssl_context: Optional[_TSSLContextArg] = None
        if 'https' in config and config['https']:
            self.active_config['https'] = True
            if 'ssl_certificate_file' in config and 'ssl_certificate_key_file' in config:
                self.active_config['ssl_certificate_file'] = config['ssl_certificate_file']
                self.active_config['ssl_certificate_key_file'] = config['ssl_certificate_key_file']
                ssl_context = (config['ssl_certificate_file'], config['ssl_certificate_key_file'])
            else:
                ssl_context = 'adhoc'
        else:
            self.active_config['https'] = False

        self.restapi = RestAPI(
            car_connectivity=car_connectivity,
            host=self.active_config['host'],
            port=self.active_config['port'],
            users=users,
            ssl_context=ssl_context,
        )

        LOG.info("Loading REST API plugin with config %s", config_remove_credentials(config))

    def startup(self) -> None:
        LOG.info("Starting REST API plugin")
        self._rest_thread = threading.Thread(target=self.restapi.server.serve_forever)
        self._rest_thread.name = 'carconnectivity.plugins.restapi-server'
        self._rest_thread.daemon = True
        self._rest_thread.start()
        self.healthy._set_value(value=True)  # pylint: disable=protected-access
        LOG.debug("Starting REST API plugin done")

    def shutdown(self) -> None:
        """Shut down the REST API server and clean up resources."""
        if self._rest_thread is not None and self._rest_thread.is_alive():
            self.restapi.server.shutdown()
        return super().shutdown()

    def get_version(self) -> str:
        return __version__

    def get_type(self) -> str:
        return "carconnectivity-plugin-restapi"

    def get_name(self) -> str:
        return "REST API Plugin"
