import tempfile, os
from multiprocessing import Process
from markovcommon import markov_dictionary_from_file, add_to_markov_dictionary, generate_sentence, MARKOV_VALUE_PROPS
from utilities.common import time_function
from utilities.dbdict import DatabaseDictionary

# Get total number of entries for a dictionary which has the value type list
def total_entries(d):
    entries = 0
    for k in d.keys():
        entries += len(d[k])
    return entries

def as_process(target, args):
    p = Process(target = target, args = args)
    p.start()
    p.join()
    p.terminate()

class MarkovBrain():
    new_brain_lines_limit = 1024

    def __init__(self, brain_file, brain_db, chain_length, max_words):
        self.brain_file = brain_file
        self.brain_db = brain_db
        self.chain_length = chain_length
        self.max_words = max_words

        self.markov = None # Holds markov chain data. key(tuple(words[chain_length])) -> {word_choice1: count, word_choice2: count}
        self.new_brain_lines = [] # New lines seen since brain was loaded. Will be added to brain file when size reaches new_brain_lines_limit

        self.load_brain()

    def load_brain(self):
        print 'Brain loading...'

        # Generate new db if file doesn't exist
        if not os.path.exists(self.brain_db):
            as_process(markov_dictionary_from_file, (self.brain_db, self.brain_file, self.chain_length)) # Shields main process from intermediate memory used
        self.markov = DatabaseDictionary(self.brain_db, MARKOV_VALUE_PROPS)
        print 'Brain loaded.'
        print 'Markov dictionary has %i keys' % (len(self.markov),)

    def __add_new_brain_line(self, msg):
        self.new_brain_lines.append(msg + '\n')
        if len(self.new_brain_lines) >= self.new_brain_lines_limit:
            self.__dump_new_brain_lines()

    def __dump_new_brain_lines(self):
        with open(self.brain_file, 'a') as f:
            for line in self.new_brain_lines:
                f.write(line.encode('utf-8'))
        print '%i new brain lines dumped.' % (len(self.new_brain_lines))
        self.new_brain_lines = []

    @time_function
    def add_to_brain(self, original_msg):
        msg = original_msg.replace('\x00', '').strip().decode('utf-8')

        # Don't bother with empty lines.
        if len(msg) == 0:
            return

        self.__add_new_brain_line(msg)
        self.markov.begin()
        add_to_markov_dictionary(self.markov, self.chain_length, msg)
        self.markov.commit()

    def generate_sentence(self, seed_msg):
        return generate_sentence(self.markov, seed_msg, self.chain_length, self.max_words)

    def close(self):
        self.__dump_new_brain_lines()
        self.markov.close()