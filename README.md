# CarConnectivity Plugin for a REST API

[![GitHub sourcecode](https://img.shields.io/badge/Source-GitHub-green)](https://github.com/tillsteinbach/CarConnectivity-plugin-restapi/)
[![GitHub](https://img.shields.io/github/license/tillsteinbach/CarConnectivity-plugin-restapi)](https://github.com/tillsteinbach/CarConnectivity-plugin-restapi/blob/master/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/tillsteinbach/CarConnectivity-plugin-restapi)](https://github.com/tillsteinbach/CarConnectivity-plugin-restapi/issues)

## CarConnectivity will become the successor of [WeConnect-python](https://github.com/tillsteinbach/WeConnect-python) in 2025 with similar functionality but support for other brands beyond Volkswagen!

[CarConnectivity](https://github.com/tillsteinbach/CarConnectivity) is a python API to connect to various car services. This plugin provides a REST API that allows other clients to interact with CarConnectivity's object tree.

## Supported operations
- **GET** data from CarConnectivity's object tree
- **PUT** writable attributes (change values)
- **POST** commands with their arguments

## Installation
```bash
pip install carconnectivity-plugin-restapi
```

## Configuration
Add the plugin to your `carconnectivity.json` configuration file:

```json
{
    "carConnectivity": {
        "connectors": [...],
        "plugins": [
            {
                "type": "restapi",
                "config": {
                    "host": "0.0.0.0",
                    "port": 40000,
                    "username": "admin",
                    "password": "secretpassword"
                }
            }
        ]
    }
}
```

### Multiple users
```json
{
    "carConnectivity": {
        "plugins": [
            {
                "type": "restapi",
                "config": {
                    "port": 40000,
                    "users": [
                        {"username": "user1", "password": "pass1"},
                        {"username": "user2", "password": "pass2"}
                    ]
                }
            }
        ]
    }
}
```

### HTTPS
```json
{
    "carConnectivity": {
        "plugins": [
            {
                "type": "restapi",
                "config": {
                    "port": 40000,
                    "https": true,
                    "ssl_certificate_file": "/path/to/cert.pem",
                    "ssl_certificate_key_file": "/path/to/key.pem",
                    "username": "admin",
                    "password": "secret"
                }
            }
        ]
    }
}
```

## API Usage

All endpoints require HTTP Basic Authentication.

### GET — retrieve data
```
GET http://localhost:40000/<path>
```
Returns the object or attribute at `<path>` in the CarConnectivity object tree as JSON.
An empty path (`/`) returns the entire tree.

Example:
```bash
curl -u admin:secret http://localhost:40000/garage/WVWZZZAUZLW123456/charging/connector/connection_state
```

### PUT — set a writable attribute
```
PUT http://localhost:40000/<path>
Content-Type: application/json

{"value": <new_value>}
```

Example:
```bash
curl -u admin:secret -X PUT -H "Content-Type: application/json" \
     -d '{"value": 80}' \
     http://localhost:40000/garage/WVWZZZAUZLW123456/charging/settings/target_level
```

### POST — execute a command
```
POST http://localhost:40000/<path>
Content-Type: application/json

{"value": <command_arguments>}
```

Example:
```bash
curl -u admin:secret -X POST -H "Content-Type: application/json" \
     -d '{"value": "start"}' \
     http://localhost:40000/garage/WVWZZZAUZLW123456/climatization/commands/start-stop
```

## Configuration parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `host` | Host/IP to listen on | `0.0.0.0` |
| `port` | Port to listen on | `40000` |
| `username` | Single user username | — |
| `password` | Single user password | — |
| `users` | List of `{username, password}` objects | — |
| `https` | Enable HTTPS | `false` |
| `ssl_certificate_file` | Path to SSL certificate file | — |
| `ssl_certificate_key_file` | Path to SSL private key file | — |
| `log_level` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `ERROR` |