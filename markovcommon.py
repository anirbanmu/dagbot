from utilities.progressbar import ProgressBar
from math import floor

# Markov dictionary has form key(tuple(words[chain_length])) -> [(word_choice1, count), (word_choice2, count)]

def add_to_markov_dictionary(markov_dict, chain_length, line):
    words = line.split()

    for i in xrange(chain_length, len(words)):
        key = tuple(words[i - chain_length : i])
        entry = markov_dict.get(key)

        if not entry:
            markov_dict[key] = [(words[i], 1)]
        else:
            word_index = next((j for j,v in enumerate(entry) if v[0] == words[i]), None)
            if word_index:
                entry[word_index] = (words[i], entry[word_index][1] + 1)
            else:
                entry.append((words[i], 1))

def markov_dictionary_from_file(brain_file, chain_length):
    markov_dict = {}
    with open(brain_file, 'r') as f:
        lines = f.readlines()
        progress_bar = ProgressBar(len(lines), int(floor(0.01 * len(lines))))
        for i,line in enumerate(lines):
            add_to_markov_dictionary(markov_dict, chain_length, line.strip().decode('utf-8'))
            progress_bar.update(i + 1)
    return markov_dict