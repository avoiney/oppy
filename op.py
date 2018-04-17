#! /usr/bin/env python3
import argparse
import configparser
import logging
import os

import opcli

parser = argparse.ArgumentParser(description='1password CLI')
parser.add_argument('profile', type=str,
                    help='the 1password profile to use')
parser.add_argument('--config', dest='config', type=str,
                    default='~/.config/op.py/conf.ini',
                    help='path to the conf file')
parser.add_argument('--debug', dest='debug', action='store_true',
                    help='toggle the debug mode')
parser.add_argument('--vault', dest='vault', type=str,
                    help='set the vault')
argv = parser.parse_args()

# read config
config = configparser.ConfigParser({
    'debug': False,
    'vault': None,
    'temp_file': os.path.expanduser('~/.config/op.py/tmpfile')
})
config.read(os.path.expanduser(argv.config))

PROFILE = argv.profile
DEBUG = argv.debug or config.getboolean(PROFILE, 'debug')
config.set(argv.profile, 'debug', 'true' if DEBUG else 'false')
if argv.vault:
    config.set(argv.profile, 'vault', argv.vault)

logger = logging.getLogger(__name__)
if DEBUG:
    level = logging.DEBUG
else:
    level = logging.INFO
logging.basicConfig(level=level)


def main():
    try:
        opcli.OnePasswordCLI(config, PROFILE).cmdloop()
    except opcli.LoginError as exc:
        logger.error(exc)
    except KeyboardInterrupt:
        print('Bye!')


if __name__ == '__main__':
    main()
