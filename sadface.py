__author__ = "Benjamin Keith (ben@benlk.com)"

import sys, os, random, re, time, string, json, jsonschema
from twisted.words.protocols import irc
from twisted.internet import protocol
from twisted.internet import reactor
from time import localtime, strftime
from commands.calendarcountdown import CalendarCountdown
from markovbrain import MarkovBrain
from utilities.calendar import Calendar
from utilities.common import time_function
from utilities.json import json_encode, default_setting_jsonschema_validator

#
# Setting some settings
#
def read_config(schema_file_path, config_file_path):
    with open(schema_file_path, 'r') as schema_file:
        with open(config_file_path, 'r') as config_file:
            schema = json.load(schema_file)
            config = json.load(config_file)
            jsonschema.Draft4Validator.check_schema(schema)
            validator = default_setting_jsonschema_validator(jsonschema.Draft4Validator)
            validator(schema).validate(config) # Throws on error
            return json_encode(config, 'utf-8')

try:
    config = read_config(os.path.join(os.path.dirname(__file__), 'config_schema.json'), sys.argv[1])
except jsonschema.ValidationError as e:
    print 'Error validating config file (%s).' % sys.argv[1]
    print e
    sys.exit()

if not os.path.exists(config['brain']['brain_file']):
    sys.exit('Error: Hoi! I need me some brains! Whaddya think I am, the Tin Man?')

listen_only_channels = []
if 'unresponsive_channels' in config['irc']:
    listen_only_channels = ['#' + c.lower() for c in config['irc']['unresponsive_channels']]

# Calendar from http://www.f1fanatic.co.uk/contact/f1-fanatic-calendar/
formula1_calendar = Calendar('http://www.google.com/calendar/ical/hendnaic1pa2r3oj8b87m08afg%40group.calendar.google.com/public/basic.ics')

dynamic_commands = [CalendarCountdown(formula1_calendar,
                                      ['@next', '@countdown'],
                                      ['r', 'q', 'fp1', 'fp2', 'fp3'],
                                      {'': '', 'r': 'grand prix', 'q': 'grand prix qualifying', 'fp1': 'first practice', 'fp2': 'second practice', 'fp3': 'third practice'}),
                                      # Calendar from http://icalshare.com/calendars/7111
                    CalendarCountdown('http://www.google.com/calendar/ical/hq7d8mnvjfodf60rno2rbr6leg%40group.calendar.google.com/public/basic.ics',
                                      ['@nextwec', '@countdownwec'],
                                      ['r', 'q'],
                                      {'': '', 'r': 'race', 'q': 'qualifying'}),
                    CalendarCountdown('http://www.google.com/calendar/ical/smcvrb4c50unt7gs59tli4kq9o%40group.calendar.google.com/public/basic.ics',
                                      ['@nextgp2', '@countdowngp2'],
                                      ['r', 'q'],
                                      {'': '', 'r': 'race', 'q': 'qualifying'}),
                    CalendarCountdown('http://www.google.com/calendar/ical/dc71ef6p5csp8i8gu4vai0h5mg%40group.calendar.google.com/public/basic.ics',
                                      ['@nextgp3', '@countdowngp3'],
                                      ['r', 'q'],
                                      {'': '', 'r': 'race', 'q': 'qualifying'})]

if 'dynamic_aliases' in config['commands']:
    for command,aliases in config['commands']['dynamic_aliases'].iteritems():
        for dynamic_command in dynamic_commands:
            if command in dynamic_command.keywords:
                dynamic_command.keywords = dynamic_command.keywords + [a for a in aliases if a not in dynamic_command.keywords]

markov = MarkovBrain(config['brain']['brain_file'], config['brain']['chain_length'], config['brain']['max_words'])

#
# Begin actual code
#
def ignore(user):
    ignore_users = config['irc'].get('ignore_users')
    return ignore_users and user in ignore_users

def pick_modifier(modifiers, str):
    for modifier in modifiers:
        if str.startswith(modifier):
            return modifier
    return ''

class sadfaceBot(irc.IRCClient):
    realname = config['irc']['realname']
    username = config['irc']['username']
    userinfo = config['irc']['user_info']
    versionName = config['irc']['version_info']
    erroneousNickFallback = config['irc']['nickname'][1]
    password = config['irc']['password'] if 'password' in config['irc'] else None

    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)

    def joinChannel(self, channel):
        self.join(channel)

    def signedOn(self):
        if self.password:
            self.msg('nickserv', 'identify ' + self.password)

        for chan in self.factory.channels:
            self.joinChannel(chan)

        for chan in self.factory.listen_only_channels:
            self.joinChannel(chan)

    def joined(self, channel):
        print "Joined %s as %s." % (channel,self.nickname)

    def listen_only(self, channel):
        return channel.lower() in self.factory.listen_only_channels

    def receiver(self, user_nick, channel):
        return user_nick if channel.lower() == self.factory.nickname.lower() else channel

    def send(self, user_nick, channel, msg):
        self.msg(self.receiver(user_nick, channel), msg)

    def handle_dynamic(self, user_nick, channel, msg, keyword, modifiers, response, check_only):
        prefix = user_nick + ': '
        if msg.startswith(keyword):
            if not check_only:
                self.send(user_nick, channel, prefix + response(pick_modifier(modifiers, msg[len(keyword):])))
            return True
        return False

    def handle_command(self, user_nick, channel, msg, check_only = False):
        prefix = user_nick + ': '
        # Check if this is a simple static command
        for command,responses in self.factory.static_commands.iteritems():
            if msg.startswith(command):
                if not check_only:
                    self.send(user_nick, channel, prefix + random.choice(responses))
                return True

        for command_index,keyword_index in self.factory.dynamic_command_keyword_order:
            command = self.factory.dynamic_commands[command_index]
            if self.handle_dynamic(user_nick, channel, msg, command.keywords[keyword_index], command.modifiers, command.response, check_only):
                return True

        return False

    def privmsg(self, user, channel, msg):
# TODO
# make the privmsg class run:
#    check for user
#    check for reply
#        check for self.
        channel = channel.lower()
        user_nick = user.split('!', 1)[0]
        # Prints the message to stdout
        print channel + " <" + user_nick + "> " + msg
        if not user:
            print "NON-USER:" + msg
            return

        # Ignores the message if the person is in the ignore list
        if ignore(user_nick):
            print "\t" + "Ignored message from <" + user_nick + "> at: " + strftime("%a, %d %b %Y %H:%M:%S %Z", localtime()) # Time method from http://stackoverflow.com/a/415527
            return

        reply = config['brain']['reply_mode']

        if reply == 0 or self.listen_only(channel):
            print msg
            if not self.handle_command(user_nick, channel, msg.lower(), True):
                self.factory.markov.add_to_brain(re.compile(self.nickname + "[:,]* ?", re.I).sub('', msg))
            return

        if self.handle_command(user_nick, channel, msg.lower()):
            return

        if self.factory.quiet_hours_calendar.in_event():
            print "No response during quiet hours. Message: " + msg
            self.factory.markov.add_to_brain(re.compile(self.nickname + "[:,]* ?", re.I).sub('', msg))
            return

        # Replies to messages containing the bot's name
        if reply == 1:
            if self.nickname in msg:
                time.sleep(0.2) #to prevent flooding
                msg = re.compile(self.nickname + "[:,]* ?", re.I).sub('', msg)
                prefix = "%s: " % (user_nick, )
            else:
                prefix = ''

            self.factory.markov.add_to_brain(msg)
            print "\t" + msg #prints to stdout what sadface added to brain
            if prefix or (channel == self.nickname or random.random() <= self.factory.channels[channel]):
                sentence = self.factory.markov.generate_sentence(msg)
                if sentence:
                    self.msg(self.receiver(user_nick, channel), prefix + sentence)
                    print ">" + "\t" + sentence #prints to stdout what sadface said
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

            self.factory.markov.add_to_brain(msg)
            print "\t" + msg #prints to stdout what sadface added to brain
            if prefix or (channel == self.nickname or random.random() <= self.factory.channels[channel]):
                sentence = self.factory.markov.generate_sentence(msg)
                if sentence:
                    self.msg(self.receiver(user_nick, channel), prefix + sentence)
                    print ">" + "\t" + sentence #prints to stdout what sadface said
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

class sadfaceBotFactory(protocol.ClientFactory):
    protocol = sadfaceBot

    def __init__(self, markov, channels, listen_only_channels, static_commands, dynamic_commands, quiet_hours_calendar):
        self.markov = markov
        self.channels = channels
        self.listen_only_channels = listen_only_channels
        self.nickname = config['irc']['nickname'][0]
        self.static_commands = static_commands
        self.dynamic_commands = dynamic_commands
        self.quiet_hours_calendar = quiet_hours_calendar

        # Holds the order of matching for keywords from longest in length to shortest. This prevents collisions of substring keywords.
        # Each array element is (index into dynamic_command, index into that specific command's keywords)
        self.dynamic_command_keyword_order = []
        for command_index, command_object in enumerate(self.dynamic_commands):
            for keyword_index, keyword in enumerate(command_object.keywords):
                self.dynamic_command_keyword_order.append((command_index, keyword_index))
        self.dynamic_command_keyword_order.sort(key=lambda x: len(self.dynamic_commands[x[0]].keywords[x[1]]), reverse=True)

    def clientConnectionLost(self, connector, reason):
        print "Lost connection (%s), reconnecting." % (reason,)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "Could not connect: %s" % (reason,)
        quit()
#
#    We begin!
#

if __name__ == "__main__":
    config_file = sys.argv[1]
    if config_file == False:
        print "Please specify a valid config file in the arguments."
        print "Example:"
        print "python sadface.py default.ini"

    irc_config = config['irc']
    reactor.connectTCP(irc_config['host'], irc_config['port'], sadfaceBotFactory(markov, irc_config['responsive_channels'] , listen_only_channels, config['commands']['static_commands'], dynamic_commands, formula1_calendar))
    reactor.run()

    markov.close()