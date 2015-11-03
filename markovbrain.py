import string
from random import choice, random

# Get total number of entries for a dictionary which has the value type list
def total_entries(d):
    entries = 0
    for k in d.keys():
        entries += len(d[k])
    return entries

def pick_weighted_random(choices):
    r = random() * sum([c[1] for c in choices])
    for c,p in choices:
        r -= p
        if r <= 0:
            return c
    assert False

class MarkovBrain():
    new_brain_lines_limit = 1024

    def __init__(self, brain_file, chain_length, max_words):
        self.brain_file = brain_file
        self.chain_length = chain_length
        self.max_words = max_words

        self.word_dict = {} # Holds all words seen. hash(word) -> word
        self.markov = {} # Holds markov chain data. tuple(word * chain_length) -> list of hash(word)
        self.new_brain_lines = [] # New lines seen since brain was loaded. Will be added to brain file when size reaches new_brain_lines_limit

        self.load_brain()

    def load_brain(self):
        with open(self.brain_file, 'r') as f:
            for line in f:
                self.__add_to_markov_brain(line.strip().decode('utf-8'))
        print 'Brain loaded.'
        print 'Markov dictionary has %i keys & %i total list entries.' % (len(self.markov.keys()), total_entries(self.markov))
        print 'Word dictionary has %i words.' % (len(self.word_dict.keys()))

    def __add_to_markov_brain(self, msg):
        words = msg.split()

        # We store the line_index into flat_brain & the word index in that line inside the dictionary
        for i in xrange(self.chain_length, len(words)):
            key = hash(tuple(words[i - self.chain_length : i]))
            entry = self.markov.get(key)
            word_hash = hash(words[i])
            if not entry:
                self.markov[key] = [(word_hash, 1)]
            else:
                word_hash_index = next((i for i,v in enumerate(entry) if v[0] == word_hash), None)
                if word_hash_index:
                    entry[word_hash_index] = (word_hash, entry[word_hash_index][1] + 1)
                else:
                    entry.append((word_hash, 1))

            if not self.word_dict.get(word_hash):
                self.word_dict[word_hash] = words[i]

    def __add_new_brain_line(self, msg):
        self.new_brain_lines.append(msg + '\n')
        if len(self.new_brain_lines) >= self.new_brain_lines_limit:
            self.dump_new_brain_lines()

    def dump_new_brain_lines(self):
        with open(self.brain_file, 'a') as f:
            for line in self.new_brain_lines:
                f.write(line.encode('utf-8'))
        print '%i new brain lines dumped.' % (len(self.new_brain_lines))
        self.new_brain_lines = []

    def add_to_brain(self, original_msg):
        msg = original_msg.replace('\x00', '').strip().decode('ascii')

        # Don't bother with empty lines.
        if len(msg) == 0:
            return

        self.__add_new_brain_line(msg)
        self.__add_to_markov_brain(msg)

    def generate_sentence(self, seed_msg):
        msg = seed_msg.strip().decode('ascii')
        if len(msg) > 0 and msg[-1] in string.punctuation:
            # drop punctuation
            msg = msg[:len(msg) - 1]

        message = msg.split()[:self.chain_length]

        if len(message) < self.chain_length:
            for i in xrange(self.chain_length - len(message)):
                message.append(self.word_dict[pick_weighted_random(self.markov[choice(self.markov.keys())])])

        for i in xrange(self.chain_length, self.max_words):
            word_choices = self.markov.get(hash(tuple(message[i - self.chain_length : i])))
            if not word_choices:
                break
            message.append(self.word_dict[pick_weighted_random(word_choices)])

        return ' '.join(message).encode('ascii')