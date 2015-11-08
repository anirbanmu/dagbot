from utilities.common import ProgressBar, time_function
from utilities.dbdict import DatabaseDictionary

START_CODE = u'␂␀␃'
STOP_CODE = u'␃␀␂'

# Markov dictionary has form key(tuple(words[chain_length])) -> {word_choice1: count, word_choice2: count}

def add_to_markov_dictionary(markov_dict, chain_length, line):
    words = line.split() + [STOP_CODE]

    for i in xrange(chain_length, len(words)):
        key = tuple(words[i - chain_length : i])
        choices = markov_dict.get(key)

        if not choices:
            choices = {words[i]: 1}
        else:
            count = choices.get(words[i])
            choices[words[i]] = count + 1 if count else 1

        markov_dict[key] = choices

@time_function
def line_count(file):
    c = 0
    with open(file, 'r') as f:
        c = sum(1 for l in f)
    return c

@time_function
def markov_dictionary_from_file(temp_db_file, brain_file, chain_length):
    print 'Creating markov chains from %s' % brain_file
    temp_dict = {}
    with open(brain_file, 'r') as f:
        progress_bar = ProgressBar(line_count(brain_file))
        for line in f:
            add_to_markov_dictionary(temp_dict, chain_length, line.strip().decode('utf-8'))
            progress_bar.update()

    print 'Populating database dictionary with markov chains'
    db_dict = DatabaseDictionary(temp_db_file)
    db_dict.begin()
    db_dict.replace(temp_dict)
    db_dict.commit()
    db_dict.close()