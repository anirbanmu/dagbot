# -*- coding: utf-8 -*-
from __future__ import print_function

import redis

class MarkovCoreRedis():
    def __init__(self, brain_db, chain_length):
        self.brain_db = brain_db
        self.chain_length = chain_length
        self.redis = redis.StrictRedis(decode_responses=True)

    def sync_with_file(self, brain_file):
        pass

    def add_to_markov_dictionary(self, line):
        pass

    def generate_sentence(self, seed_msg, max_words):
        pass

    def close(self):
        pass