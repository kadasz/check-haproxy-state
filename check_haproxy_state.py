#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import optparse
import configparser
from haproxyadmin import haproxy
from logging.handlers import SysLogHandler
from logging import StreamHandler, Formatter

logger = logging.getLogger("check_haproxy_state")
logger.setLevel(logging.DEBUG)
formatter_syslog = Formatter("%(name)s[%(process)d]: %(levelname)s - %(message)s")
formatter_console = Formatter("[%(levelname)s] - %(message)s")
console_hdl = StreamHandler(sys.stdout)
console_hdl.setFormatter(formatter_console)
console_hdl.setLevel(logging.DEBUG)
syslog_hdl = SysLogHandler(address="/dev/log")
syslog_hdl.setFormatter(formatter_syslog)
syslog_hdl.setLevel(logging.DEBUG)
logger.addHandler(console_hdl)
logger.addHandler(syslog_hdl)

SIGNALS = {
    "UNKNOWN": "-1",
    "OK": "0",
    "WARNING": "1",
    "ERROR": "2",
}

class AttrConfig(dict):
    def __init__(self, *args, **kwargs):
        super(AttrConfig, self).__init__(*args, **kwargs)
        self.__dict__ = self

config_file = '/etc/haproxy-status.ini'
if os.path.isfile(config_file):
    config = configparser.ConfigParser(dict_type=AttrConfig)
    config.read(config_file)
    if 'EXCLUDE' in config._sections:
        exclude_app = config._sections.get('EXCLUDE', None).get('applications', None)
        if not exclude_app:
            exclude_app = ""
        else:
            exclude_app.split(",")
    else:
        exclude_app = ""
else:
    exclude_app = ""

EXCLUDE_APPS = exclude_app if exclude_app else ""

class Error(Exception):
    u'''Base class to customizing status exceptions'''
    pass

class ExceptionUpBackend(Error):
    u'''Exception when the backend status value is UP'''
    pass

class ExceptionDownBackend(Error):
    '''Exception when the backend status value is DOWN'''
    pass

class ExceptionOtherBackend(Error):
    u'''Exception when the backend status value is OTHER'''
    pass

def _getBackends(metric_type='status', socket=None):
    try:
        backend = {}
        for b in socket.backends():
            if 'stats' not in b.name:
                if metric_type == 'status':
                    backend[b.name] = b.status
        return backend
    except Exception as e:
        logger.error('There was a problem while getting or parsing backends data - {}'.format(str(e)))
        return False

def _getFrontends(metric_type='status', socket=None):
    try:
        frontend = {}
        for f in socket.frontends():
            if 'stats' not in f.name:
                if metric_type == 'status':
                    frontend[f.name] = f.status
        return frontend
    except Exception as e:
        logger.error('There was a problem while getting or parsing frontends data - {}'.format(str(e)))
        return False

def main():

    parser = optparse.OptionParser(description="Simply Nagios plugin to check HAProxy backends and frontends state", version="0.0.1", usage="usage: %prog -s /var/run/haproxy/ -t backends")

    parser.add_option(
    "-s", "--sockets_path",
    dest="sockets_path",
    help="Enter path to the HAProxy sockets",
    )
    parser.add_option(
    "-t", "--section_type",
    dest="section_type",
    help="Select backends or frontends!",
    )
    (opts, args) = parser.parse_args()

    try:
        if not opts.sockets_path or not opts.section_type:
            parser.print_help()
            raise SystemExit(int(SIGNALS["ERROR"]))
        elif opts.sockets_path is None:
            parser.error('Please enter the path to HAProxy sockets!')
        elif opts.section_type is None:
            parser.error('Please select backends or frontends!')
        elif opts.section_type not in [ "backends", "frontends" ]:
            parser.error('Bad value! Possible values are backends or frontends!')
        elif opts.section_type:
            pass
    except Exception as e:
        logger.error('There was a problem parsing the arguments passed to the script! - {}'.format(str(e)))
        sys.exit(int(SIGNALS["ERROR"]))

    try:
        h = haproxy.HAProxy(socket_dir=opts.sockets_path)
        pass
    except Exception as e:
        logger.error('Unable to connect to the HAProxy socket! - {}'.format(str(e)))
        sys.exit(int(SIGNALS["ERROR"]))

    if opts.section_type == "backends":
        try:
            backendy = _getBackends(socket=h)
            if backendy:
                pass
            else:
                sys.exit(int(SIGNALS["UNKNOWN"]))
        except Exception as e:
            logger.error('Unable to retrieve backends data! - {}'.format(str(e)))
            sys.exit(int(SIGNALS["ERROR"]))

    if opts.section_type == "frontends":
        try:
            frontendy = _getFrontends(socket=h)
            if frontendy:
                pass
            else:
                sys.exit(int(SIGNALS["UNKNOWN"]))
        except Exception as e:
            logger.error('Unable to retrieve frontends data! - {}'.format(str(e)))
            sys.exit(int(SIGNALS["ERROR"]))

    if opts.section_type == "frontends":
        filtered_frontends = { 
            k: v for k, v in frontendy.items() if k not in exclude_app 
        }
    else:
        filtered_backends = { 
            k: v for k, v in backendy.items() if k not in exclude_app 
        }

    try: 
        other_backend = {}
        down_backend = {}
        up_backend = {}

        if opts.section_type == "frontends":
            for k, v in filtered_frontends.items():
                if v == "DOWN":
                    down_backend[k] = v
                elif v == "OPEN":
                    up_backend[k] = v
                else:
                    other_backend.append(k)
        elif opts.section_type == "backends":
            for k, v in filtered_backends.items():
                if v == "DOWN":
                    down_backend[k] = v
                elif v == "UP":
                    up_backend[k] = v
                else:
                    other_backend[k] = v

        if down_backend and not other_backend:
            raise ExceptionDownBackend
        if other_backend:
            raise ExceptionOtherBackend
        if up_backend:
            raise ExceptionUpBackend

    except ExceptionDownBackend: 
        logger.error('Some {} has DOWN state: {}'.format(opts.section_type, down_backend))
        raise SystemExit(int(SIGNALS["ERROR"]))
    except ExceptionOtherBackend: 
        logger.error('UNKNOW status of {}: - {}'.format(opts.section_type, other_backend))
        raise SystemExit(int(SIGNALS["UNKNOWN"]))
    except ExceptionUpBackend: 
        logger.info('OK: All {} {} are right state'.format(len(up_backend), opts.section_type))
        raise SystemExit(int(SIGNALS["OK"]))
    except Exception as e:
        logger.error('Error processing or parsing output! - {}'.format(str(e)))
        sys.exit(int(SIGNALS["ERROR"]))
    finally:
        if down_backend and other_backend:
            error_backend = {**down_backend, **other_backend}
            logger.error('Some {} has DOWN or UNKNOWN state: {}'.format(opts.section_type, error_backend))
            raise SystemExit(int(SIGNALS["ERROR"]))
        else:
            pass

if __name__ == '__main__':
    main()
