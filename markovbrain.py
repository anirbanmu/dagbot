from __future__ import print_function

import time
from builtins import object

from markov.markov_core_sqlite import MarkovCoreSqlite
from utilities.common import time_function


# Get total number of entries for a dictionary which has the value type list
def total_entries(d):
    entries = 0
    for k in d.keys():
        entries += len(d[k])
    return entries


class MarkovBrain(object):
    new_brain_lines_limit = 1024

    def __init__(self, brain_file, brain_db, chain_length, max_words, censored_words=None):
        if censored_words is None:
            censored_words = []

        self.brain_file = brain_file
        self.max_words = max_words
        self.censored_words = censored_words

        self.markov = MarkovCoreSqlite(brain_db, chain_length)
        self.markov.sync_with_file(brain_file)

        # New lines seen since brain was loaded. Will be added to brain file when size reaches new_brain_lines_limit
        self.new_brain_lines = []

    def __add_new_brain_line(self, msg):
        self.new_brain_lines.append(msg + '\n')
        if len(self.new_brain_lines) >= self.new_brain_lines_limit:
            self.__dump_new_brain_lines()

    def __dump_new_brain_lines(self):
        with open(self.brain_file, 'a') as f:
            for line in self.new_brain_lines:
                f.write(line)
        print('%i new brain lines dumped.' % (len(self.new_brain_lines)))
        self.new_brain_lines = []

    @time_function
    def add_to_brain(self, original_msg):
        msg = original_msg.replace('\x00', '').strip()

        # Don't bother with empty lines.
        if len(msg) == 0:
            return

        self.__add_new_brain_line(msg)
        self.markov.add_to_markov_dictionary(msg)

    def generate_sentence(self, seed_msg):
        sentence = self.markov.generate_sentence(seed_msg, self.max_words)

        end_time = time.time() + 4
        while any(w in sentence for w in self.censored_words):
            if time.time() > end_time:
                return ''
            sentence = self.markov.generate_sentence('', self.max_words)
        return sentence

    def close(self):
        self.__dump_new_brain_lines()
        self.markov.close()
