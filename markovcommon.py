from utilities.common import ProgressBar, time_function
from utilities.dbdict import DatabaseDictionary

# Markov dictionary has form key(tuple(words[chain_length])) -> [(word_choice1, count), (word_choice2, count)]

def add_to_markov_dictionary(markov_dict, chain_length, line):
    words = line.split()

    for i in xrange(chain_length, len(words)):
        key = tuple(words[i - chain_length : i])
        choices = markov_dict.get(key)

        if not choices:
            markov_dict[key] = [(words[i], 1)]
        else:
            word_index = next((j for j,v in enumerate(choices) if v[0] == words[i]), None)
            if word_index:
                choices[word_index] = (words[i], choices[word_index][1] + 1)
            else:
                choices.append((words[i], 1))
            markov_dict[key] = choices

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
        for i,line in enumerate(f):
            add_to_markov_dictionary(temp_dict, chain_length, line.strip().decode('utf-8'))
            progress_bar.update(i + 1)

    print 'Populating database dictionary with markov chains'
    db_dict = DatabaseDictionary(temp_db_file)
    progress_bar = ProgressBar(len(temp_dict.keys()))
    for i,k in enumerate(temp_dict.keys()):
        db_dict[k] = temp_dict[k]
        progress_bar.update(i + 1)
    db_dict.commit()
    db_dict.close()