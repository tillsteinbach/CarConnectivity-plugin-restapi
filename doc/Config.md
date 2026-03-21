
# CarConnectivity Plugin for REST API Config Options
The configuration for CarConnectivity is a .json file.
## General format
The general format is a `carConnectivity` section, followed by a list of connectors and plugins.
In the `carConnectivity` section you can set the global `log_level`.
Each connector or plugin needs a `type` attribute and a `config` section.
The `type` and config options specific to your connector or plugin can be found on their respective project page.
```json
{
    "carConnectivity": {
        "log_level": "error", // set the global log level, you can set individual log levels in the connectors and plugins
        "connectors": [
            {
                "type": "skoda", // Definition for a MySkoda account
                "config": {
                    "interval": 600, // Interval in which the server is checked in seconds
                    "username": "test@test.de", // Username of your MySkoda Account
                    "password": "testpassword123" // Password of your MySkoda Account
                }
            },
            {
                "type": "volkswagen", // Definition for a Volkswagen account
                "config": {
                    "interval": 300, // Interval in which the server is checked in seconds
                    "username": "test@test.de", // Username of your Volkswagen Account
                    "password": "testpassword123" // Username of your Volkswagen Account
                }
            }
        ],
        "plugins": [
            {
                "type": "restapi", // Minimal definition for the REST API plugin
                "config": {
                }
            }
        ]
    }
}
```
### REST API Plugin Options
These are the valid options for the REST API plugin
```json
{
    "carConnectivity": {
        "connectors": [],
        "plugins": [
            {
                "type": "restapi", // Definition for the REST API plugin
                "disabled": false, // You can disable plugins without removing them from the config completely
                "config": {
                    "log_level": "error", // The log level for the plugin. Otherwise uses the global log level
                    "host": "localhost", // The host to listen on, default is 0.0.0.0 meaning all interfaces
                    "port": 40000, // Port to listen on, default is 40000
                    "username": "admin", // Admin username for Basic Authentication
                    "password": "secret", // Admin password for Basic Authentication
                    "users": [{ // Additional users
                        "username": "testuser",
                        "password": "testpassword"
                    }],
                    "https": true, //Enable https, default is false. if no cert/key is provided a self signed certificate is generated
                    "ssl_certificate_file": "/home/user/certs/cert.local.cert.pem", // Path to certificate (only with "https": true)
                    "ssl_certificate_key_file": "/home/user/certs/cert.local.key.pem" // Path to certificate key file (only with "https": true)
                }
            }
        ]
    }
}
```

### Connector Options
Valid Options for connectors can be found here:
* [CarConnectivity-connector-skoda Config Options](https://github.com/tillsteinbach/CarConnectivity-connector-skoda/tree/main/doc/Config.md)
* [CarConnectivity-connector-volkswagen Config Options](https://github.com/tillsteinbach/CarConnectivity-connector-volkswagen/tree/main/doc/Config.md)
* [CarConnectivity-connector-tronity Config Options](https://github.com/tillsteinbach/CarConnectivity-connector-tronity/tree/main/doc/Config.md)
