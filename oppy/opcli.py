"""
    Define the CLI object.
"""
import base64
import cmd
import getpass
import json
import logging
import os
import pickle
import subprocess

import cryptography.fernet as fernet
import keyring
import pygments
import pygments.formatters as pyg_format
import pygments.lexers as pyg_lexer

import oppy.opdb as opdb


logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s %(filename)s:%(lineno)d - %(message)s'
logging.basicConfig(format=FORMAT)


class LoginError(Exception):
    pass


class OnePasswordCLI(cmd.Cmd):
    """ Define the command line interface to interact with OnePassword. """
    prompt = '(op ➜) '
    items = opdb.OpResponse()

    def __init__(self, config, profile, *args, **kwargs):
        super(OnePasswordCLI, self).__init__(*args, **kwargs)
        self.domain = config.get(profile, 'domain')
        self.do_setvault(config.get(profile, 'vault'))
        self.debug = config.getboolean(profile, 'debug')
        self.temp_file = config.get(profile, 'temp_file')
        logger.setLevel(logging.DEBUG if self.debug else logging.INFO)

    @property
    def conf(self):
        return {
            'vault': self.vault,
            'domain': self.domain,
            'debug': self.debug
        }

    @property
    def db(self):
        return opdb.OpDatabase(self.items)

    @property
    def op_session(self):
        return keyring.get_password('OnePasswordCLI',
                                    'OP_SESSION_{}'.format(self.domain))

    @property
    def tmp_file_name(self):
        """ Returns the complete path of the temporary file
        used to cache the list results.
        """
        if self.vault:
            return '{}-{}'.format(self.temp_file, self.vault)
        return self.temp_file

    def _get_env(self):
        """ Returns a copy of the current environment updated
        with the OnePassword session.
        """
        environ = os.environ.copy()
        environ.update({
            'OP_SESSION_%s' % self.domain: self.op_session
        })
        return environ

    def _set_pass_to_keyring(self, password=None):
        """ Set the OnePassword master key in the system keyring."""
        password = getpass.getpass(
            '1password master for {}:'.format(self.domain))
        return password

    def _get_encryption_key(self, size=32):
        """ Compute the encryption key from OnePassword master key. """
        password = bytes(self.op_session, 'utf-8')
        # b'\xce' char make 1 character len
        password = password[:size] + b'\xce' * (size - len(password))
        return base64.encodebytes(password)

    def _login(self):
        """ Do the OnePassword login and store the session. """
        print('Waiting for authentication checks...', end='', flush=True)
        process = subprocess.Popen(args=['op', 'signin', '--output=raw',
                                   self.domain],
                                   encoding='utf-8',
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

        # set the password to the keyring
        password = self._set_pass_to_keyring()

        # extract the stdout and stderr from process
        out, err = process.communicate(password)

        # if error, log it and retry
        if err:
            logger.error(err)
            self._login()
            return

        # store the session
        keyring.set_password('OnePasswordCLI',
                             'OP_SESSION_{}'.format(self.domain), out.strip())
        print('')
        logger.debug(self.op_session)
        print('Login successful')

    def _save_to_tmp(self):
        """ Save the items list in the temporary file. """
        try:
            with open(self.tmp_file_name, 'wb+') as tmp:
                # encrypt data
                f = fernet.Fernet(self._get_encryption_key())
                tmp.write(f.encrypt(pickle.dumps(self.items)))
        except (ValueError, TypeError, IOError) as exc:
            logger.debug(exc)

    def _read_from_tmp(self):
        """ Get the items from the temporary files. """
        try:
            with open(self.tmp_file_name, 'rb') as tmp:
                # decrypt data
                f = fernet.Fernet(self._get_encryption_key())
                self.items = pickle.loads(f.decrypt(tmp.read()))
        except (ValueError, TypeError, IOError, EOFError) as exc:
            logger.debug(exc)
            try:
                os.remove(self.tmp_file_name)
            except OSError as exc:
                logger.debug(exc)
            self.items = opdb.OpResponse()

    def _get_items(self, refresh=False):
        """ Get items either from file cache or from server.

        :type refresh: boolean
        :param refresh: if True, get the items from the server and update
        the file cache.
        :rtype: opdb.OpResponse()
        """
        self._read_from_tmp()
        if refresh or not list(self.items):
            cmd = ['op', 'list', 'items']
            if self.vault:
                cmd += ['--vault=%s' % self.vault]
            process = subprocess.Popen(args=cmd,
                                       env=self._get_env(),
                                       encoding='utf-8',
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            out, err = process.communicate()
            if out:
                self.items = opdb.OpResponse(
                    json.loads(out))
                self._save_to_tmp()
            else:
                self.items = opdb.OpResponse()
                self._save_to_tmp()
        return self.items

    def _get_item(self, uuid):
        """ Get one item from its UUID.

        :type uuid: str
        :param uuid: the item unique identifier
        :returns:  dict -- the dict of the item
        """
        cmd = ['op', 'get', 'item']
        if self.vault:
            cmd += ['--vault=%s' % self.vault]
        cmd += [uuid]
        process = subprocess.Popen(args=cmd,
                                   env=self._get_env(),
                                   encoding='utf-8',
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        out, err = process.communicate()
        if out:
            raw_item = json.loads(out)
            item = {'uuid': raw_item['uuid']}
            if 'title' in raw_item.get('overview', {}):
                item['title'] = raw_item['overview']['title']
            if 'url' in raw_item.get('overview', {}):
                item['url'] = raw_item['overview']['url']
            username_fields = [field for field in raw_item.get('details', {})
                                                          .get('fields')
                               if field.get('designation') == 'username']
            if username_fields:
                item['username'] = username_fields[0]['value']
            password_fields = [field for field in raw_item.get('details', {})
                                                          .get('fields')
                               if field.get('designation') == 'password']
            if password_fields:
                item['password'] = password_fields[0]['value']
            return item
        if err:
            logger.error(err)

    def _ask_choice(self, choices):
        """ Ask user to select one of the elements of the list.
        :type choices: list of dict
        :param choices: list of elements in which user will pick one
        :returns: one of the choices
        """
        for idx, choice in enumerate(choices):
            print('{}: {}'.format(idx, choice))
        user_choice = input('Enter one of the choices above: ')
        try:
            return int(user_choice)
        except ValueError:
            if user_choice in ('q', 'quit', 'exit'):
                return None
            return self._ask_choice(choices)

    def preloop(self):
        """ At the start of the CLI, print a nice welcoming message
        and log the user in.
        """
        print('Welcome to the One Password python CLI!')
        self._login()

    def precmd(self, line):
        """ Before each command, check if the user is logged in. """
        if 'login' not in line and not self.op_session:
            self._login()
        return line

    def query(self, tql, refresh=False):
        """ Query the items.

        :type tql: str
        :param tql: the TQL representing the query.
        :type refresh: boolean
        :param refresh: if True, refresh the items before execute the query.
        :returns: the filtered items
        """
        self._get_items(refresh=refresh)
        return list(self.db.raw_query(tql))

    def print_json(self, data):
        """ Format the json before outputing it. """
        if data:
            data = json.dumps(data, indent=4, ensure_ascii=False)
            print(pygments.highlight(data, pyg_lexer.JsonLexer(),
                                     pyg_format.Terminal256Formatter()))

    def do_session(self, args):
        """ Output the current user session. """
        print(self.op_session)

    def do_version(self, args):
        """ Output the op program version. """
        subprocess.run(args=['op', '--version'])

    def do_update(self, args):
        """ Check for op updates. """
        subprocess.run(args=['op', 'update'])

    def do_login(self, args):
        """ Log the user in. """
        self._login()

    def do_refresh(self, args):
        """ Refresh the items. """
        self._get_items(refresh=True)

    def do_list(self, args):
        """ Output the items as JSON. """
        self.print_json(list(self._get_items()))

    def do_get(self, arg):
        """ Get a specific item using its uuid, title or domain. """
        self.print_json(self._get_item(arg))

    def do_search(self, tql):
        """ Find items matching the tql given as argument. """
        if not tql:
            return print('A TQL is required')
        try:
            items = self.query(tql)
        except opparser.ParsingError as exc:
            logger.error(exc)
            return
        # if there is no item, return
        if len(items) == 0:
            logger.error('No item found')
            return
        # if there is only one item, display it,
        # else, ask for user to make a choice
        if len(items) == 1:
            item = items[0]
        else:
            # compute the choices display
            choices = [
                '{} :: {}'.format(item['overview']['title'],
                                  item['overview'].get('url', '-'))
                for item in items
            ]
            # ask user
            user_choice = self._ask_choice(choices)
            # if choice is None, user want to exit
            if user_choice is None:
                return
            # use the choice to get item from list
            item = items[user_choice]
        # output the item
        self.print_json(self._get_item(item['uuid']))

    def do_setvault(self, args):
        """ Change the current vault. """
        if args in ['null', 'None', 'None', '']:
            self.vault = None
        else:
            self.vault = args

    def do_setdebug(self, debug):
        """ Change the debug config. """
        if debug.lower() in ['yes', 'y', 'true', 'y', '1']:
            self.debug = True
        elif debug.lower() in ['no', 'n', 'false', 'f', '0']:
            self.debug = False
        else:
            # do nothing if debug is not a recognize value
            pass

    def do_getconf(self, args):
        """ Get the current conf. """
        self.print_json(self.conf)

    def do_EOF(self, args):
        return self.do_bye(args)

    def do_bye(self, args):
        print('Bye!')
        return True
