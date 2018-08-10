# -*- coding: utf-8 -*-
from __future__ import print_function

import redis
import itertools
from multiprocessing import Process
from utilities.common import ProgressBar, time_function

KEY_SEPARATOR = ':'
DAGBOT_KEY_MARKER = 'dagbot'
MARKOV_KEY_MARKER = 'markov'
CHOICES_KEY_MARKER = 'choices'
CHOICES_TOTAL_KEY_MARKER = 'choices_total'
ORIGINAL_VALUE_KEY_MARKER = 'original_value'

BASE_KEY_PREFIX = KEY_SEPARATOR.join([DAGBOT_KEY_MARKER, MARKOV_KEY_MARKER])
CHOICES_KEY_PREFIX = KEY_SEPARATOR.join([BASE_KEY_PREFIX, CHOICES_KEY_MARKER])
CHOICES_TOTAL_KEY_PREFIX = KEY_SEPARATOR.join([BASE_KEY_PREFIX, CHOICES_TOTAL_KEY_MARKER])
ORIGINAL_VALUE_KEY_PREFIX = KEY_SEPARATOR.join([BASE_KEY_PREFIX, ORIGINAL_VALUE_KEY_MARKER])
START_WORDS_KEY = KEY_SEPARATOR.join([BASE_KEY_PREFIX, 'start_words'])

STOP_CODE = u'␃␀␂'

REDIS = redis.StrictRedis(decode_responses=True)

def chain_key_parts(chain_tuple):
    # return list(chain_tuple) + [str(len(chain_tuple))]
    return list(chain_tuple)

def base_chain_key(chain_tuple):
    return ' '.join(chain_key_parts(chain_tuple))
    # return KEY_SEPARATOR.join(chain_key_parts(chain_tuple))

def choices_key(chain_key):
    return KEY_SEPARATOR.join([CHOICES_KEY_PREFIX, chain_key])

def choices_total_key(chain_key):
    return KEY_SEPARATOR.join([CHOICES_TOTAL_KEY_PREFIX, chain_key])

def original_value_key(chain_key):
    return KEY_SEPARATOR.join([ORIGINAL_VALUE_KEY_PREFIX, chain_key])

def add_to_markov_dictionary(chain_length, line, redis_connection = None):
    words = line.split() + [STOP_CODE]

    for i in xrange(chain_length, len(words)):
        chain = tuple(words[i - chain_length : i])
        chain_key = base_chain_key(chain)

        pipe = redis_connection if redis_connection != None else REDIS.pipeline()

        # Original value of this chain (needed if looking up a start chain to use)
        # pipe.set(original_value_key(chain_key), ' '.join(chain))

        # Sorted set of choices (score is number of times seen after this chain)
        chain_choices_key = choices_key(chain_key)
        pipe.zincrby(chain_choices_key, words[i])

        # Total score of items in chain_choices_key
        pipe.incr(choices_total_key(chain_key))

        # List of start chain_keys
        if i == chain_length:
            pipe.sadd(START_WORDS_KEY, chain_key)

        if pipe != redis_connection:
            pipe.execute()

@time_function
def count_lines(file):
    c = 0
    with open(file, 'r') as f:
        c = sum(1 for l in f)
    return c

@time_function
def markov_dictionary_from_file(brain_file, chain_length):
    print('Creating markov chains from %s' % brain_file)

    line_count = count_lines(brain_file)

    for c in xrange(1, chain_length + 1):
        print('Creating markov chains of length %i' % c)

        pipe = REDIS.pipeline()
        with open(brain_file, 'r') as f:
            progress_bar = ProgressBar(line_count)
            for i, line in enumerate(f):
                add_to_markov_dictionary(c, line.strip().decode('utf-8').lower(), pipe)
                progress_bar.update()
                if i % 256 == 0:
                    pipe.execute()
                    pipe = REDIS.pipeline()

        pipe.execute()

def populate_markov_data(brain_file, chain_length, start_line, stop_line):
    print('Creating markov chains from %s [%i - %i]' % (brain_file, start_line, stop_line))

    pipe = REDIS.pipeline()
    for c in xrange(1, chain_length + 1):
        with open(brain_file, 'r') as f:
            for i, line in enumerate(itertools.islice(f, start_line, stop_line)):
                add_to_markov_dictionary(c, line.strip().decode('utf-8').lower(), pipe)
                if i % 256 == 0:
                    pipe.execute()
                    pipe = REDIS.pipeline()

    pipe.execute()

@time_function
def markov_dictionary_from_file_with_workers(brain_file, chain_length, worker_count = 4):
    print('Creating markov chains from %s' % brain_file)

    line_count = count_lines(brain_file)
    lines_per_worker = line_count / worker_count
    start_stop_indices = [(lines_per_worker * i, line_count if i + 1 == worker_count else lines_per_worker * (i + 1)) for i in range(worker_count)]

    workers = [Process(target = populate_markov_data, args = (brain_file, chain_length) + start_stop_indices[i]) for i in range(worker_count)]
    for w in workers:
        w.start()

    for w in workers:
        w.join()
