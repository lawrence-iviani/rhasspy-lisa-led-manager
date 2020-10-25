# Rhasspy Hermes Dialogue Manager

[![Continous Integration](https://github.com/rhasspy/rhasspy-lisa-led-manager/workflows/Tests/badge.svg)](https://github.com/rhasspy/rhasspy-lisa-led-manager/actions)
[![GitHub license](https://img.shields.io/github/license/rhasspy/rhasspy-lisa-led-manager.svg)](https://github.com/rhasspy/rhasspy-lisa-led-manager/blob/master/LICENSE)

Uses `hermes/dialogueManager` functionality from [Hermes protocol](https://docs.snips.ai/reference/hermes) to activate/deactivate available led configurations.

## Installation

```bash
$ git clone https://github.com/lawrence-iviani/rhasspy-lisa-led-manager
$ cd rhasspy-lisa-led-manager
# Only installation in system, hack for virtual environment otherwise
$ sudo python3 setup.py install

# TODO: common message are defined in https://github.com/lawrence-iviani/rhasspy-lisa-odas-hermes/tree/master/lisa
# this need a refactor, better wait for a concept of deployment from one point (e.g. repository lisa with git links)
# for now the workaround is to create a link manually. (adjust if needed the path)
$ ln -s /home/pi/sw/rhasspy-lisa-odas-hermes/lisa
```

## Running

```bash
$ bin/rhasspy-lisa-led-manager <ARGS>
```

## Command-Line Options

```
usage: rhasspy-lisa-led-manager [-h] [--hw-board] [--led-pattern]
                               [--host HOST] [--port PORT] 
                               [--username USERNAME] [--password PASSWORD] [--tls]
                               [--tls-ca-certs TLS_CA_CERTS]
                               [--tls-certfile TLS_CERTFILE]
                               [--tls-keyfile TLS_KEYFILE]
                               [--tls-cert-reqs {CERT_REQUIRED,CERT_OPTIONAL,CERT_NONE}]
                               [--tls-version TLS_VERSION]
                               [--tls-ciphers TLS_CIPHERS] [--site-id SITE_ID]
                               [--debug] [--log-format LOG_FORMAT]

optional arguments:
  -h, --help            show this help message and exit
  --hw-board LISA_PLATFORM
                        One of the available platforms: Respeaker4MicArray | MatrixVoice | DummyBoard (No led)
  --led-pattern LISA_LED_PATTERN
                        One of the available imitation led patterns between GoogleHome | Alexa
  --host HOST           MQTT host (default: localhost)
  --port PORT           MQTT port (default: 1883)
  --username USERNAME   MQTT username
  --password PASSWORD   MQTT password
  --tls                 Enable MQTT TLS
  --tls-ca-certs TLS_CA_CERTS
                        MQTT TLS Certificate Authority certificate files
  --tls-certfile TLS_CERTFILE
                        MQTT TLS certificate file (PEM)
  --tls-keyfile TLS_KEYFILE
                        MQTT TLS key file (PEM)
  --tls-cert-reqs {CERT_REQUIRED,CERT_OPTIONAL,CERT_NONE}
                        MQTT TLS certificate requirements (default:
                        CERT_REQUIRED)
  --tls-version TLS_VERSION
                        MQTT TLS version (default: highest)
  --tls-ciphers TLS_CIPHERS
                        MQTT TLS ciphers to use
  --site-id SITE_ID     Hermes site id(s) to listen for (default: all)
  --debug               Print DEBUG messages to the console
  --log-format LOG_FORMAT
                        Python logger format
```
