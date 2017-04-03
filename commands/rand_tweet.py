import tweepy
from collections import deque
from random import choice
from datetime import datetime, timedelta
from commands.commandhandler import CommandHandler

class RandTweetHandler(CommandHandler):
    def __init__(self, config):
        auth = tweepy.OAuthHandler(config['api_key'], config['api_secret'])
        auth.set_access_token(config['access_token'], config['access_token_secret'])

        self.api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
        self.screen_name = self.api.me().screen_name
        self.tweets = []
        self.__update_tweets()

    def __update_tweets(self):
        tweet_count = len(self.tweets)
        most_recent_id = self.tweets[tweet_count - 1][0] if tweet_count > 0 else None

        # Grab all tweets if we have not seen any tweets yet. On further calls, only grab what we haven't seen.
        cursor = tweepy.Cursor(self.api.user_timeline) if most_recent_id is None else tweepy.Cursor(self.api.user_timeline, since_id=most_recent_id)

        # Always keeps tweets in oldest to newest in left to right order
        temp_deque = deque()
        for status in cursor.items():
            temp_deque.appendleft((status.id, status.text)) # Store ID so twitter URL can be constructed later.
        self.tweets.extend(temp_deque)

    def get_help(self, _0, _1):
        return ['Display a random previously tweeted message']

    def get_response(self, _0, msg, _1):
        self.__update_tweets()
        if len(self.tweets) > 0:
            status = choice(self.tweets)
            return ("%s ( https://twitter.com/%s/status/%i )" % (status[1], self.screen_name, status[0])).encode('utf-8')
        return "No previous tweets found.".encode('utf-8')

command_handler_properties = (RandTweetHandler, ['randtweet'], False)
