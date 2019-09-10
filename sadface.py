from __future__ import print_function

from future import standard_library
standard_library.install_aliases()
from builtins import map
__author__ = "Benjamin Keith (ben@benlk.com)"

import sys, os, platform, random, re, time, string, json, jsonschema, pkgutil, imp, socket
from time import localtime, strftime
from datetime import timedelta
from collections import OrderedDict, namedtuple

from twisted.internet.protocol import Factory
from twisted.internet.endpoints import clientFromString
from twisted.words.protocols.irc import IRCClient
from twisted.application.internet import ClientService
from twisted.internet import reactor

from markovbrain import MarkovBrain
from utilities.calendar import Calendar
from utilities.common import time_function
from utilities.jsonhelpers import validate_load_default_json, validate_default_json

#
# Setting some settings
#
try:
    config = validate_load_default_json(os.path.join(os.path.dirname(__file__), 'config_schema.json'), sys.argv[1], 'utf-8')
except jsonschema.ValidationError as e:
    print('Error validating config file (%s).' % sys.argv[1])
    print(e)
    sys.exit()

# Handle home directory
config['brain']['brain_file'] = config['brain']['brain_file'].replace('~', os.path.expanduser('~'))
config['brain']['brain_db'] = config['brain']['brain_db'].replace('~', os.path.expanduser('~'))

if not os.path.exists(config['brain']['brain_file']):
    sys.exit('Error: Hoi! I need me some brains! Whaddya think I am, the Tin Man?')

def initialize_chan_props(props):
    quiet_hours = props['quiet_hours']
    if not quiet_hours:
        return props

    p = props.copy()
    p['quiet_hours'] = Calendar(quiet_hours) # Create real calendar object for quiet hours
    return p

config['irc']['unrecorded_channels'] = {k.lower(): initialize_chan_props(v) for k,v in config['irc']['unrecorded_channels'].items()}
config['irc']['responsive_channels'] = {k.lower(): initialize_chan_props(v) for k,v in config['irc']['responsive_channels'].items()}
config['irc']['responsive_channels'].update(config['irc']['unrecorded_channels']) # Unrecorded channels are also responsive.
config['irc']['unresponsive_channels'] = {k.lower(): v for k,v in config['irc']['unresponsive_channels'].items()}

config['irc']['channels'] = config['irc']['responsive_channels'].copy()
config['irc']['channels'].update(config['irc']['unresponsive_channels'])

config['irc']['ignore_users'] = list(map(lambda s: s.lower(), config['irc']['ignore_users']))
config['irc']['unrecorded_users'] = list(map(lambda s: s.lower(), config['irc']['unrecorded_users']))
config['commands']['static_commands'] = {k.lower(): v for k,v in config['commands']['static_commands'].items()}
config['commands']['dynamic_aliases'] = {k.lower(): list(map(lambda s: s.lower(), v)) for k,v in config['commands']['dynamic_aliases'].items()}
config['commands']['disabled_commands'] = list(map(lambda s: s.lower(), config['commands']['disabled_commands']))

#
# Begin actual code
#

# For each command in the path given, we find the command_handler and return a sorted dictionary of handlers.
def gather_commands(path, aliases, command_configs, disabled):
    commands = {}

    CommandHandlerProps = namedtuple('CommandHandlerProps', ['handler', 'use_notice'])

    for importer, name, _ in pkgutil.iter_modules([path]):
        f, filename, description = imp.find_module(name, [path])

        if os.path.splitext(os.path.basename(filename))[0].lower() in disabled:
            continue

        try:
            module = imp.load_module(name, f, filename, description)
            if hasattr(module, 'command_handler_properties'):
                json_file_name = name + '.json'
                schema_file_path = os.path.join(os.path.join(path, 'schema'), json_file_name)
                fallback_config_path = os.path.join(os.path.join(path, 'config'), json_file_name)

                if name in command_configs:
                    command_config = validate_default_json(schema_file_path, command_configs[name], 'utf-8')
                else:
                    command_config = validate_load_default_json(schema_file_path, fallback_config_path, 'utf-8')

                command_handler_type, keywords, use_notice = getattr(module, 'command_handler_properties')
                command_handler = command_handler_type(command_config)
                command_handler_props = CommandHandlerProps(command_handler, use_notice)

                for keyword in keywords:
                    aliases = [keyword] + (aliases[keyword] if keyword in aliases else [])
                    for alias in aliases:
                        commands[alias] = command_handler_props
        finally:
            f.close()

    return OrderedDict(sorted(commands.items(), reverse=True, key=lambda t: len(t[0])))

class sadfaceBot(IRCClient):
    versionEnv = platform.platform()

    @property
    def erroneousNickFallback(self):
        return self.irc_cfg['nickname'][1]

    @property
    def realname(self):
        return self.irc_cfg['realname']

    @property
    def username(self):
        return self.irc_cfg['username']

    @property
    def userinfo(self):
        return self.irc_cfg['user_info']

    @property
    def versionName(self):
        return self.irc_cfg['version_info']['name']

    @property
    def versionNum(self):
        return self.irc_cfg['version_info']['number']

    @property
    def sourceURL(self):
        return self.irc_cfg['source']

    @property
    def config(self):
        return self.factory.config

    @property
    def irc_cfg(self):
        return self.config['irc']

    @property
    def cmd_cfg(self):
        return self.config['commands']

    @property
    def brain_cfg(self):
        return self.config['brain']

    def connectionMade(self):
        self.nickname = self.irc_cfg['nickname'][0]
        IRCClient.connectionMade(self)

    def ignore(self, user):
        return user.lower() in self.irc_cfg['ignore_users']

    def unrecorded(self, user):
        return user.lower() in self.irc_cfg['unrecorded_users']

    def signedOn(self):
        irc_cfg = self.irc_cfg
        if irc_cfg['password']:
            self.msg('nickserv', 'identify ' + irc_cfg['password'])

        for c,props in list(irc_cfg['responsive_channels'].items()) + list(irc_cfg['unresponsive_channels'].items()):
            self.join(c, props['password'])

    def kickedFrom(self, channel, kicker, message):
        reactor.callLater(5.0, self.join, channel, self.irc_cfg['channels'][channel.lower()]['password'])

    def joined(self, channel):
        print("Joined %s as %s." % (channel, self.nickname))

    def unresponsive(self, channel):
        return channel.lower() in self.irc_cfg['unresponsive_channels']

    def add_to_brain(self, channel, user_nick, msg, raw_msg):
        if channel not in self.irc_cfg['unrecorded_channels'] and self.nickname not in raw_msg and not self.is_pm(channel) and not self.unrecorded(user_nick):
            self.factory.markov.add_to_brain(msg)
        else:
            print("Message not added to brain.")

    def in_quiet_hours(self, channel, longest_duration):
        if self.is_pm(channel):
            return False

        quiet_hours = self.irc_cfg['channels'][channel]['quiet_hours']
        return quiet_hours and quiet_hours.in_event(longest_duration, '')

    def is_pm(self, channel):
        return channel == self.nickname.lower()

    def receiver(self, user_nick, channel):
        return user_nick if self.is_pm(channel) else channel

    def send(self, user_nick, channel, msg, use_notice = False):
        for m in msg.splitlines():
            if use_notice:
                self.notice(user_nick, m)
                continue
            self.msg(self.receiver(user_nick, channel), m)

    def send_markov_sentence(self, user_nick, channel, prefix, msg):
        self.factory.last_response[self.receiver(user_nick, channel)] = msg
        self.send(user_nick, channel, prefix + msg)

    def last_markov_sentence(self, user_nick, channel):
        receiver = self.receiver(user_nick, channel)
        last = self.factory.last_response.get(receiver)
        return '' if not last else last

    def execute_command(self, user_nick, channel, check_only, trigger):
        if trigger in self.cmd_cfg['deprecated_triggers']:
            self.send(user_nick, channel, '%s is deprecated. Use one of these instead: %s' % (trigger, ' '.join(self.cmd_cfg['triggers'])), True)
            return False
        return not check_only

    def handle_help(self, channel, param_str):
        if param_str != '':
            for keyword,cmd_props in self.factory.dynamic_commands.items():
                if param_str.startswith(keyword):
                    return cmd_props.handler.get_help(param_str[len(keyword):], channel)

        return [', '.join(self.factory.dynamic_commands.keys())]

    def handle_command(self, user_nick, channel, msg, check_only = False):
        prefix = user_nick + ': '

        # Handle help
        help_command_match = self.factory.help_command_regex.match(msg)
        if help_command_match:
            if self.execute_command(user_nick, channel, check_only, help_command_match.group(1)):
                helper_strings = self.handle_help(channel, msg[help_command_match.span(2)[1]:].strip())
                for i, h in enumerate(helper_strings):
                    self.send(user_nick, channel, ('    ' * i) + h, True)
            return True

        # Check if this is a simple static command
        static_command_match = self.factory.static_commands_regex.match(msg)
        if static_command_match:
            if self.execute_command(user_nick, channel, check_only, static_command_match.group(1)):
                self.send(user_nick, channel, prefix + random.choice(self.cmd_cfg['static_commands'][static_command_match.group(3)]))
            return True

        dynamic_command_match = self.factory.dynamic_commands_regex.match(msg)
        if dynamic_command_match:
            if self.execute_command(user_nick, channel, check_only, dynamic_command_match.group(1)):
                cmd_props = self.factory.dynamic_commands[dynamic_command_match.group(3)]
                reply = prefix + cmd_props.handler.get_response(msg[dynamic_command_match.span(2)[1]:], self.last_markov_sentence(user_nick, channel), channel)
                self.send(user_nick, channel, reply, cmd_props.use_notice)
            return True

        return False

    def privmsg(self, user, channel, raw_msg):
        # TODO
        # make the privmsg class run:
        #    check for user
        #    check for reply
        #    check for self.
        channel = channel.lower()
        user_nick = user.split('!', 1)[0].lower()
        msg = raw_msg = raw_msg.lower()

        # Prints the message to stdout
        print(channel + " <" + user_nick + "> " + msg)
        if not user:
            print("NON-USER:" + msg)
            return

        # Ignores the message if the person is in the ignore list
        if self.ignore(user_nick):
            print("\t" + "Ignored message from <" + user_nick + "> at: " + strftime("%a, %d %b %Y %H:%M:%S %Z", localtime())) # Time method from http://stackoverflow.com/a/415527
            return

        reply = self.brain_cfg['reply_mode']

        if reply == 0 or self.unresponsive(channel):
            print(msg)
            if not self.handle_command(user_nick, channel, msg.lower(), True):
                self.add_to_brain(channel, user_nick, re.compile(self.nickname + "[:,]* ?", re.I).sub('', msg), raw_msg)
            return

        if self.handle_command(user_nick, channel, msg.lower()):
            return

        if self.in_quiet_hours(channel, timedelta(hours=6)):
            print("No response during quiet hours. Message: " + msg)
            self.add_to_brain(channel, user_nick, re.compile(self.nickname + "[:,]* ?", re.I).sub('', msg), raw_msg)
            return

        # Replies to messages containing the bot's name
        if reply == 1:
            if self.nickname in msg:
                time.sleep(0.2) #to prevent flooding
                msg = re.compile(self.nickname + "[:,]* ?", re.I).sub('', msg)
                prefix = "%s: " % (user_nick, )
            else:
                prefix = ''

            self.add_to_brain(channel, user_nick, msg, raw_msg)
            print("\t" + msg) #prints to stdout what sadface added to brain
            if prefix or (channel == self.nickname or random.random() <= self.irc_cfg['responsive_channels'][channel]['p']):
                sentence = self.factory.markov.generate_sentence(msg)
                if sentence:
                    self.send_markov_sentence(user_nick, channel, prefix, sentence)
                    print(">" + "\t" + sentence) #prints to stdout what sadface said
            return

        # Replies to messages starting with the bot's name.
        if reply == 2:
            if msg.startswith(self.nickname): #matches nickname, mecause of Noxz
                time.sleep(0.2) #to prevent flooding
                msg = re.compile(self.nickname + "[:,]* ?", re.I).sub('', msg)
                prefix = "%s: " % (user_nick, )
            else:
                msg = re.compile(self.nickname + "[:,]* ?", re.I).sub('', msg)
                prefix = ''

            self.add_to_brain(channel, user_nick, msg, raw_msg)
            print("\t" + msg) #prints to stdout what sadface added to brain
            if prefix or (channel == self.nickname or random.random() <= self.irc_cfg['responsive_channels'][channel]['p']):
                sentence = self.factory.markov.generate_sentence(msg)
                if sentence:
                    self.send_markov_sentence(user_nick, channel, prefix, sentence)
                    print(">" + "\t" + sentence) #prints to stdout what sadface said
            return

#
# Idea for later implementation
# To limit who gets to talk to the bot, the talker's nickname is self.nickname
# if user in allowed_people:
#    Check that user is okayed with nickserv
#    pass
# else:
#    fail
#

class sadfaceBotFactory(Factory):
    protocol = sadfaceBot

    def __init__(self, config, markov, dynamic_commands, dynamic_commands_regex, static_commands_regex, help_command_regex):
        self.markov = markov
        self.config = config
        self.dynamic_commands = dynamic_commands
        self.dynamic_commands_regex = dynamic_commands_regex
        self.static_commands_regex = static_commands_regex
        self.help_command_regex = help_command_regex
        self.last_response = {}

#
#    We begin!
#

if __name__ == "__main__":
    config_file = sys.argv[1]
    if config_file == False:
        print("Please specify a valid config file in the arguments.")
        print("Example:")
        print("python sadface.py default.ini")

    irc_cfg = config['irc']
    cmd_cfg = config['commands']
    commands_dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'commands')
    dynamic_commands = gather_commands(commands_dir_path, cmd_cfg['dynamic_aliases'], cmd_cfg['command_configs'], cmd_cfg['disabled_commands'])

    triggers = '|'.join(re.escape(s) for s in config['commands']['triggers'] + config['commands']['deprecated_triggers'])
    dynamic_commands_regex = re.compile('\s*(' + triggers + ')\s*((' + '|'.join(dynamic_commands.keys()) + ')\s*).*')
    static_commands_regex = re.compile('\s*(' + triggers + ')\s*((' + '|'.join(cmd_cfg['static_commands'].keys()) + ')\s*).*')
    help_command_regex = re.compile('\s*(' + triggers + ')\s*(help\s*).*')

    brain_config = config['brain']
    markov = MarkovBrain(brain_config['brain_file'], brain_config['brain_db'], brain_config['chain_length'], brain_config['max_words'],
                         brain_config['censored_words'])

    client_string = "%s:%s:%u" % ('ssl' if irc_cfg['ssl'] else 'tcp', irc_cfg['host'], irc_cfg['port'])
    endpoint = clientFromString(reactor, client_string)
    bot_client_service = ClientService(endpoint, sadfaceBotFactory(config, markov, dynamic_commands, dynamic_commands_regex, static_commands_regex, help_command_regex))

    bot_client_service.startService()

    reactor.run()

    markov.close()
