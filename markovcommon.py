from collections import namedtuple
from utilities.common import ProgressBar, time_function
from utilities.dbdict import DatabaseDictionary
from random import random
import string

START_CODE = u'␂␀␃'
STOP_CODE = u'␃␀␂'

# Markov dictionary has form key(tuple(words[chain_length])) -> {word_choice1: count, word_choice2: count}

MARKOV_VALUE_PROPS = [('dict', 'BLOB'), ('chain_length', 'INTEGER'), ('start_count', 'INTEGER')]
MarkovDictionaryValue = namedtuple("MarkovDictValue", ','.join(v[0] for v in MARKOV_VALUE_PROPS))

def pick_weighted_random(choices):
    r = random() * sum(choices.itervalues())
    for c,p in choices.iteritems():
        r -= p
        if r <= 0:
            return c
    assert False

def add_to_markov_dictionary(markov_dict, chain_length, line):
    words = line.split() + [STOP_CODE]

    for i in xrange(chain_length, len(words)):
        key = tuple(words[i - chain_length : i])
        value = markov_dict.get(key)

        if not value:
            value = MarkovDictionaryValue({words[i]: 1}, chain_length, 1 if i == chain_length else 0)
        else:
            count = value.dict.get(words[i])
            value.dict[words[i]] = count + 1 if count else 1
            value = MarkovDictionaryValue(value.dict, chain_length, value.start_count + 1 if i == chain_length else value.start_count)

        markov_dict[key] = value

@time_function
def count_lines(file):
    c = 0
    with open(file, 'r') as f:
        c = sum(1 for l in f)
    return c

@time_function
def markov_dictionary_from_file(temp_db_file, brain_file, chain_length):
    print 'Creating markov chains from %s' % brain_file

    line_count = count_lines(brain_file)

    temp_dict = {}
    for c in xrange(1, chain_length + 1):
        print 'Creating markov chains of length %i' % c
        with open(brain_file, 'r') as f:
            progress_bar = ProgressBar(line_count)
            for line in f:
                add_to_markov_dictionary(temp_dict, c, line.strip().decode('utf-8'))
                progress_bar.update()

    print 'Populating database dictionary with markov chains'
    db_dict = DatabaseDictionary(temp_db_file, MARKOV_VALUE_PROPS)
    db_dict.begin()
    db_dict.replace(temp_dict)
    db_dict.commit()
    db_dict.close()

@time_function
def generate_sentence(markov_dict, seed_msg, chain_length, max_words):
    msg = seed_msg.strip().decode('utf-8')
    if len(msg) > 0 and msg[-1] in string.punctuation:
        # drop punctuation
        msg = msg[:len(msg) - 1]

    message = msg.split()[:chain_length]

    if len(message) == 0:
        # Get a random seed from one word key
        r = markov_dict.get_random_filtered_key(['chain_length = 1', 'start_count > 1'])
        if not r:
            return ''
        message.append(r[0])

    length = len(message)
    while length < max_words:
        word_choices = markov_dict.get(tuple(message[-chain_length : length]))
        if not word_choices:
            break
        choice = pick_weighted_random(word_choices.dict)
        if choice == STOP_CODE:
            break
        message.append(choice)
        length += 1

    return ' '.join(message).encode('utf-8')