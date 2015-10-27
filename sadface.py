__author__ = "Benjamin Keith (ben@benlk.com)"

import sys, os, random, re, time, ConfigParser, string
from twisted.words.protocols import irc
from twisted.internet import protocol
from twisted.internet import reactor
from collections import defaultdict
from time import localtime, strftime
from commands.f1countdown import FormulaOneCountdown

#
# Setting some settings
#

config_file = sys.argv[1]

requiredconfig = [('Connection', 'host'), ('Connection', 'port'), ('Bot', 'nickname'), ('Bot', 'erroneousNickFallback'), ('Bot', 'realname'), ('Bot', 'username'), ('Bot', 'userinfo'), ('Brain', 'reply'), ('Brain', 'brain_file'), ('Brain', 'ignore_file'), ('Brain', 'STOP_WORD'), ('Brain', 'chain_length'), ('Brain', 'max_words')];
config = ConfigParser.ConfigParser()
config.read(config_file)
for setting in requiredconfig:
    if not config.has_option(setting[0], setting[1]):
        sys.exit('Error: Option "' + setting[1] + '" in section "' + setting[0] + '" is required! Take a look at your config.ini')

requiredsections = ['Channels']
for section in requiredsections:
    if not config.has_section(section) or len(config.items(section)) == 0:
        sys.exit('Error: Section "' + section + '" is required & must be non empty! Take a look at your config.ini')

host = config.get('Connection', 'host')
port = int(config.get('Connection', 'port'))
password = config.get('Connection', 'password')

nickname = config.get('Bot', 'nickname')
erroneousNickFallback = config.get('Bot', 'erroneousNickFallback')
realname = config.get('Bot', 'realname')
username = config.get('Bot', 'username')
userinfo = config.get('Bot', 'userinfo')
versionName = "sadface bot rev. 10"

reply = config.get('Brain', 'reply')
markov = defaultdict(list)
brain_file = config.get('Brain', 'brain_file')
STOP_WORD = config.get('Brain', 'STOP_WORD')
# punctuation = ['\n', '.', '?', '!', ',', '\r']
# Chain_length is the length of the message that sadface compares
chain_length = int(config.get('Brain', 'chain_length'))
max_words = int(config.get('Brain', 'max_words'))

ignore_nicks = []
if config.has_option('Brain', 'ignore_file'):
    with open(config.get('Brain', 'ignore_file'), 'r') as f:
        for line in f:
            ignore_nicks.append(line.strip())

#
# Begin actual code
#

def add_to_brain(msg, chain_length, write_to_file=False):
    if write_to_file:
        with open(brain_file, 'a') as f:
            f.write(msg + '\n')
    buf = [STOP_WORD] * chain_length
    for word in msg.split():
        markov[tuple(buf)].append(word)
        del buf[0]
        buf.append(word)
    markov[tuple(buf)].append(STOP_WORD)

# TODO
# Find the brain state, keep it saved on disk instead of in RAM.

def generate_sentence(msg, chain_length, max_words=1000): #max_words is defined elsewhere
    if len(msg) > 0 and msg[-1][-1] in string.punctuation:
#        msg[-1] = msg[-1][:-1]
#        msg.replace([-1], '')
# converts string to list, drops the end character, converts back to string
        msg = list(msg)
        msg[-1] = msg[-1][:-1]
        msg[0] = msg[0].upper()
        msg = "".join(msg)
#    buf = msg.split()[-chain_length:]
    buf = msg.split()[:chain_length]

# If message is longer than chain_length, shorten the message.
    if len(msg.split()) > chain_length:
        message = buf[:]
    else:
        message = []
        for i in xrange(chain_length):
            message.append(random.choice(markov[random.choice(markov.keys())]))
    for i in xrange(max_words):
        try:
            next_word = random.choice(markov[tuple(buf)])
        except IndexError:
            continue
        if next_word == STOP_WORD:
            break
        message.append(next_word)
        del buf[0] # What happpens if this is moved down a line?
        buf.append(next_word)
    return ' '.join(message)

def ignore(user):
    if user in ignore_nicks:
        return True
    return False

def pick_modifier(modifiers, str):
    for modifier in modifiers:
        if str.startswith(modifier):
            return modifier
    return ''

class sadfaceBot(irc.IRCClient):
    realname = realname
    username = username
    userinfo = userinfo
    versionName = versionName
    erroneousNickFallback = erroneousNickFallback
    password = password

    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)

    def joinChannel(self, channel):
        self.join(channel)

    def signedOn(self):
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

    def handle_dynamic(self, user_nick, channel, msg, command_object, check_only):
        prefix = user_nick + ': '
        for keyword in command_object.keywords:
            if msg.startswith(keyword):
                if not check_only:
                    self.send(user_nick, channel, prefix + command_object.response(pick_modifier(command_object.modifiers, msg[len(keyword):])))
                return True
        return False

    def handle_command(self, user_nick, channel, msg, check_only = False):
        prefix = user_nick + ': '
        # Check if this is a simple static command
        for command,response in self.factory.static_commands:
            if msg.startswith(command):
                if not check_only:
                    self.send(user_nick, channel, prefix + response)
                return True

        for command_object in self.factory.dynamic_commands:
            if self.handle_dynamic(user_nick, channel, msg, command_object, check_only):
                return True

        return False

    def privmsg(self, user, channel, msg):
# TODO
# make the privmsg class run:
#    check for user
#    check for reply
#        check for self.

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

        if reply == '0' or self.listen_only(channel):
            print msg
            if not self.handle_command(user_nick, channel, msg.lower(), True):
                add_to_brain(msg, self.factory.chain_length, write_to_file=True)
            return

        if self.handle_command(user_nick, channel, msg.lower()):
            return

        # Replies to messages containing the bot's name
        if reply == '1':
            if self.nickname in msg:
                time.sleep(0.2) #to prevent flooding
                msg = re.compile(self.nickname + "[:,]* ?", re.I).sub('', msg)
                prefix = "%s: " % (user_nick, )
            elif msg.lower().translate(string.maketrans("",""), string.punctuation).startswith(("hello", "hi", "sup", "howdy", "hola", "salutation", "yo", "greeting", "what up")):
                time.sleep(0.2) #to prevent flooding
                msg = re.compile(self.nickname + "[:,]* ?", re.I).sub('', msg) + " to you"
                prefix = "%s: " % (user_nick, )
            else:
                prefix = ''

            add_to_brain(msg, self.factory.chain_length, write_to_file=True)
            print "\t" + msg #prints to stdout what sadface added to brain
            if prefix or (channel == self.nickname or random.random() <= self.factory.channels[channel]):
                sentence = generate_sentence(msg, self.factory.chain_length, self.factory.max_words)
                if sentence:
                    self.msg(self.receiver(user_nick, channel), prefix + sentence)
                    print ">" + "\t" + sentence #prints to stdout what sadface said
            return

        # Replies to messages starting with the bot's name.
        if reply == '2':
            if msg.startswith(self.nickname): #matches nickname, mecause of Noxz
                time.sleep(0.2) #to prevent flooding
                msg = re.compile(self.nickname + "[:,]* ?", re.I).sub('', msg)
                prefix = "%s: " % (user_nick, )
            else:
                msg = re.compile(self.nickname + "[:,]* ?", re.I).sub('', msg)
                prefix = ''

            add_to_brain(msg, self.factory.chain_length, write_to_file=True)
            print "\t" + msg #prints to stdout what sadface added to brain
            if prefix or (channel == self.nickname or random.random() <= self.factory.channels[channel]):
                sentence = generate_sentence(msg, self.factory.chain_length, self.factory.max_words)
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

    def __init__(self, channels, listen_only_channels, nickname, chain_length, max_words, static_commands, dynamic_commands):
        self.channels = channels
        self.listen_only_channels = listen_only_channels
        self.nickname = nickname
        self.chain_length = chain_length
        self.max_words = max_words
        self.static_commands = static_commands
        self.dynamic_commands = dynamic_commands

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
        print "python sadface_configgable.py default.ini"
    if os.path.exists(brain_file):
        with open(brain_file, 'r') as f:
            for line in f:
                add_to_brain(line, chain_length)
            print 'Brain reloaded'
    else:
        print "Hoi! I need me some brains! Whaddya think I am, the Tin Man?"

    channels = {}
    for chan,chattiness in config.items("Channels"):
        channels['#' + chan.lower()] = float(chattiness)

    listen_only_channels = []
    if config.has_option('Bot', 'listenOnlyChannels'):
        for chan in config.get('Bot', 'listenOnlyChannels').split(','):
            listen_only_channels.append('#' + chan.strip().lower())

    static_commands = []
    if config.has_option('Brain', 'static_commands_file'):
        with open(config.get('Brain', 'static_commands_file'), 'r') as f:
            for line in f:
                split = line.split(':', 1);
                static_commands.append((split[0].strip().lower(), split[1].strip()))

    dynamic_commands = [FormulaOneCountdown()]

    reactor.connectTCP(host, port, sadfaceBotFactory(channels, listen_only_channels, nickname, chain_length, max_words, static_commands, dynamic_commands))
    reactor.run()