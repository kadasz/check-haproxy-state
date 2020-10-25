# check-haproxy-state

Nagios/NRPE compatible plugin for checking HAProxy frontends and backends state.

## Depedencies
- `haproxyadmin 0.2.1 or later`

## Installation

Just install the dependencies and copy the binary to standard path for nagios plugins.

```
curl -Lso /usr/lib/nagios/plugins/check_haproxy_state.py https://raw.githubusercontent.com/kadasz/check-haproxy-state/main/check_haproxy_state.py
chmod +x /usr/lib/nagios/plugins/check_haproxy_state.py
```

## Usage

```
/usr/lib/nagios/plugins/check_haproxy_state.py  --help
Usage: check_haproxy_state.py -s /var/run/haproxy/ -t backends

Simply Nagios plugin to check HAProxy backends and frontends state

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -s SOCKETS_PATH, --sockets_path=SOCKETS_PATH
                        Enter path to the HAProxy sockets
  -t SECTION_TYPE, --section_type=SECTION_TYPE
                        Select backends or frontends!
```

This check communicate with a HAProxy by local socket file using `haproxyadmin` library. Some backends or frontends checking can be avaoided by creating or coping file from repo `check-haproxy-state.ini` to `/etc/check-haproxy-state.ini`. The backend or frontend names can be entered after the decimal point this file in the applications line. 

## Server configuration

- __simple configuration for check HAProxy state__ 

```
define command {
	command_name	check_haproxy_state
	command_line	/usr/lib/nagios/plugins/check_haproxy_state.py --sockets_path $ARG1$ --section_type $ARG2$
}
```

- __service check configuration__

```
define service {
  host_name srv1.local
  use generic-service
  service_description check_haproxy_backends
  check_command check_haproxy_state!/var/run/haproxy/!backends
}
```
