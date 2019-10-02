from __future__ import print_function
import tweepy

from commands.commandhandler import CommandHandler

class TweetHandler(CommandHandler):
    def __init__(self, config):
        auth = tweepy.OAuthHandler(config['api_key'], config['api_secret'])
        auth.set_access_token(config['access_token'], config['access_token_secret'])

        self.api = tweepy.API(auth)

    def get_help(self, _0, _1):
        return ['Tweet last markov response in this channel']

    def get_response(self, _0, msg, _1):
        length = len(msg)
        if length == 0:
            return 'Bot has not said anything'

        if length > 140:
            return 'Last message too long'

        response = self.api.update_status(status = msg)

        print(response.user.screen_name)
        return ("Tweet @ https://twitter.com/%s/status/%i" % (response.user.screen_name, response.id))

command_handler_properties = (TweetHandler, ['tweet'], False)
