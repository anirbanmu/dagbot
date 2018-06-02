# -*- coding: utf-8 -*-
from __future__ import print_function

from multiprocessing import Process

from markovcommon import add_to_markov_dictionary, markov_dictionary_from_file, generate_sentence, MARKOV_VALUE_PROPS, MarkovDictionaryValue
from utilities.dbdict import DatabaseDictionary

def as_process(target, args):
    p = Process(target = target, args = args)
    p.start()
    p.join()
    p.terminate()

class MarkovCoreSqlite():
    def __init__(self, brain_db, chain_length):
        self.brain_db = brain_db
        self.chain_length = chain_length

        # Holds markov chain data. key(tuple(words[chain_length])) -> {word_choice1: count, word_choice2: count}
        self.sqlite_dict = DatabaseDictionary(self.brain_db, MARKOV_VALUE_PROPS, MarkovDictionaryValue)

    def sync_with_file(self, brain_file):
        if len(self.sqlite_dict) > 0:
            return
        self.sqlite_dict.close()
        as_process(markov_dictionary_from_file, (self.brain_db, brain_file, self.chain_length))
        self.sqlite_dict = DatabaseDictionary(self.brain_db, MARKOV_VALUE_PROPS, MarkovDictionaryValue)

    def add_to_markov_dictionary(self, line):
        self.sqlite_dict.begin()
        for c in xrange(1, self.chain_length + 1):
            add_to_markov_dictionary(self.sqlite_dict, c, line)
        self.sqlite_dict.commit()

    def generate_sentence(self, seed_msg, max_words):
        return generate_sentence(self.sqlite_dict, seed_msg, self.chain_length, max_words)

    def close(self):
        self.sqlite_dict.close()