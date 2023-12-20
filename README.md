# plejd-mqtt-ha
A simple mqtt gateway to connect your plejd devices to an MQTT broker and Home Assistant

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Description](#description)
- [Getting started](#getting-started)
  - [Setting Up and Running the Program Locally](#setting-up-and-running-the-program-locally)
    - [Prerequisites](#prerequisites)
    - [Installing Python Dependencies](#installing-python-dependencies)
    - [Activating the Virtual Environment](#activating-the-virtual-environment)
    - [Running the program](#running-the-program)
  - [Setting Up and Running as a Docker Container](#setting-up-and-running-as-a-docker-container)
    - [Building the Docker Image](#building-the-docker-image)
    - [Running the Docker Container](#running-the-docker-container)
    - [Running with Docker Compose](#running-with-docker-compose)
- [Configuration](#configuration)
  - [General](#general)
  - [API](#api)
  - [MQTT](#mqtt)
  - [BLE](#ble)
  - [Example](#example)
- [Acknowledgements](#acknowledgements)
- [License](#license)
- [Contributing](#contributing)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Description
This project connects bluetooth devices in a plejd mesh to an MQTT broker. Devices are discovered automatically by Home Assistant.

The project currently supports:
- `Plejd Light`
- `Plejd Device Trigger`
- `Plejd Switch (untested)`

Not supported currently:
- `Plejd Sensor`
- `Plejd Scenes`

## Getting started

This section provides step-by-step instructions on how to set up and run the program on your local machine.

The project is intended to run as a docker container, but can also be run locally.

### Setting Up and Running the Program Locally

This section provides step-by-step instructions on how to set up and run the program on your local machine.

#### Prerequisites

Ensure that you have the following dependencies installed on your system:

- `python`: The programming language used for this project.
- `poetry`: A tool for dependency management in Python.
- `bluetooth`: A library to work with Bluetooth.
- `bluez`: Official Linux Bluetooth protocol stack.

Refer to the Dockerfile in the project root for specific versions of these dependencies.

#### Installing Python Dependencies

After installing the prerequisites, you can install the Python dependencies for the project. Run the following command in your terminal:

```bash
poetry install
```
#### Activating the Virtual Environment
Next, spawn a new virtual shell using the following command:
Start the program using:

```bash
poetry shell
```

This command activates the virtual environment, isolating your project dependencies from other Python projects.
#### Running the program

Finally, you can start the program using the following command:

`python -m plejd_mqtt_ha`

This command runs the plejd_mqtt_ha module as a script, starting the program.

### Setting Up and Running as a Docker Container

This section provides instructions on how to build and run the program as a Docker container. Docker must be installed on your host machine to follow these steps.

#### Building the Docker Image

First, build a Docker image for the program. This creates a reusable image that contains the program and all its dependencies. Run the following command in your terminal:

```bash
docker build . -t plejd
```
This command builds a Docker image from the Dockerfile in the current directory, and tags the image with the name `plejd`

#### Running the Docker Container

After building the image, you can create and start a Docker container from it. For the settings and cache files to persist, it's necessary to mount a configuration directory. At present, the container must operate in privileged mode and with host network capabilities. Before initiating the container, you must halt the Bluetooth service:

```bash
service bluetooth stop
```

Once the service is halted, execute the following command in your terminal:

```bash
docker run -v ./data/:/data/ --rm --net=host --privileged -it plejd
```

This command starts a new Docker container from the plejd image. The program inside the container will start running immediately.

#### Running with Docker Compose

As an alternative to the `docker run` command, you can use Docker Compose to manage your application.

To start the application with Docker Compose, run:

```bash
docker-compose up
```

This command will start a new Docker container from the plejd image, just like the docker run command. The program inside the container will start running immediately.

## Configuration

Configuration of the application. See example configuration [here](#example).

### General

| Parameter                                | Description                                                                                                                 | Default        |
|------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|----------------|
| `health_check` (Optional)                | Enable health check                                                                                                         | True           |
| `health_check_interval` (Optional)       | Interval in seconds between health check writes                                                                             | 60.0           |
| `health_check_dir` (Optional)            | Directory to store health check files                                                                                       | "~/.plejd/"    |
| `health_check_bt_file` (Optional)        | File name for Bluetooth health check                                                                                        | "bluetooth"    |
| `health_check_mqtt_file` (Optional)      | File name for MQTT health check                                                                                             | "mqtt"         |
| `health_check_heartbeat_file` (Optional) | File name for heartbeat file                                                                                                | "heartbeat"    |
| `time_update_interval` (Optional)        | Interval in seconds between updating Plejd time                                                                             | 3600.0         |
| `time_update_threshold` (Optional)       | Time difference in seconds between Plejd time and local time before updating Plejd time                                     | 10.0           |
| `time_use_sys_time` (Optional)           | Whether or not to use system time instead of NTP time                                                                       | True           |
| `timezone` (Optional)                    | Timezone to use for time updates, if not set system timezone will be used. Should be in the form of e.g. "Europe/Stockholm" | None           |
| `ntp_server` (Optional)                  | NTP server to use for time updates, if not set system time will be used                                                     | "pool.ntp.org" |

### API

| Parameter                 | Description                   | Default                    |
|---------------------------|-------------------------------|----------------------------|
| `user`                    | Plejd user name (email)       |                            |
| `password`                | Password of the Plejd user    |                            |
| `site` (Optional)         | Name of the Plejd site to use | First in the accounts list |
| `timeout` (Optional)      | Timeout to reach Plejd API    | 10.0                       |
| `cache_policy` (Optional) | Cache policy to use           | "FIRST_CACHE"              |

### MQTT

| Parameter                     | Description                                                               | Default         |
|-------------------------------|---------------------------------------------------------------------------|-----------------|
| `host` (Optional)             | MQTT broker host                                                          | "localhost"     |
| `port` (Optional)             | MQTT broker port                                                          | 1883            |
| `username` (Optional)         | MQTT broker username                                                      | None            |
| `password` (Optional)         | MQTT broker password                                                      | None            |
| `client_name` (Optional)      | MQTT client name                                                          | None            |
| `use_tls` (Optional)          | Whether or not to use TLS                                                 | False           |
| `tls_key` (Optional)          | TLS key file                                                              | None            |
| `tls_certfile` (Optional)     | TLS certificate file                                                      | None            |
| `tls_ca_cert` (Optional)      | TLS CA certificate file                                                   | None            |
| `discovery_prefix` (Optional) | The root of the topic tree where HA is listening for messages             | "homeassistant" |
| `state_prefix` (Optional)     | The root of the topic tree ha-mqtt-discovery publishes its state messages | "hmd"           |

### BLE

| Parameter                 | Description                                        | Default |
|---------------------------|----------------------------------------------------|---------|
| `adapter` (Optional)      | If a specific Bluetooth adapter is to be used.     | None    |
| `scan_time` (Optional)    | Time to scan for Plejd Bluetooth devices           | 10.0    |
| `retries` (Optional)      | Number of times to try and reconnect to Plejd mesh | 10      |
| `time_retries` (Optional) | Time between retries                               | 10.0    |
| `preferred_device` (Optional) | If a specific Plejd device is to be used as mesh ingress point.             |
|                               | Not recommended to use this setting. **NOT USED YET!**                      | None    |

### Example

Here is an example configuration with some common settings:

```yaml
api:
  user: "your-email@example.com"
  password: "your-password"

mqtt:
  host: "mqtt.example.com"
  port: 1883
  user: "mqtt-user"
  password: "mqtt-password"

ble:
  scan_time: 20.0
```

## Acknowledgements

This project is inspired by the following repositories:

- [ha-plejd](https://github.com/klali/ha-plejd)
- [hassio-plejd](https://github.com/icanos/hassio-plejd)

It also utilizes the [ha-mqtt-discoverable](https://github.com/unixorn/ha-mqtt-discoverable) library
for creating MQTT devices automatically discovered by Home Assistant.

A special thanks to the authors and contributors of these projects for their work and inspiration.

## License

This project is open source and available under the [Apache License Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for details on how to contribute to this project.
