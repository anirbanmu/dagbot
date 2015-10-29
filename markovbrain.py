import string, random

def total_entries(values):
    entries = 0
    for v in values:
        entries += len(v)
    return entries

class MarkovBrain():
    def __init__(self, brain_file, chain_length, max_words):
        self.brain_file = brain_file
        self.chain_length = chain_length
        self.max_words = max_words
        self.flat_brain = []
        self.markov = {}

        self.load_brain()

    def load_brain(self):
        with open(self.brain_file, 'r') as f:
            for line in f:
                self.add_to_brain(line.strip())
        print 'Brain loaded with %i lines.' % (len(self.flat_brain))
        print 'Markov dictionary has %i keys & %i total list entries.' % (len(self.markov.keys()), total_entries(self.markov.values()))

    def add_to_brain(self, msg):
        if len(msg) == 0:
            return

        self.flat_brain.append(msg)
        self.add_to_markov_brain(len(self.flat_brain) - 1)

    def add_to_markov_brain(self, line_index):
        words = self.flat_brain[line_index].split()

        # We store the line_index into flat_brain & the word index in that line inside the dictionary
        for i in xrange(self.chain_length, len(words)):
            key = hash(tuple(words[i - self.chain_length : i]))
            entry = self.markov.get(key)
            if entry:
                entry.append((line_index, i))
            else:
                self.markov[key] = [(line_index, i)]

    def generate_sentence(self, seed_msg):
        if len(seed_msg) > 0 and seed_msg[-1] in string.punctuation:
            # drop punctuation
            seed_msg = seed_msg[:len(seed_msg) - 1]

        message = seed_msg.split()[:self.chain_length]
        if len(message) < self.chain_length:
            for i in xrange(self.chain_length - len(message)):
                message.append(self.retrieve_word(random.choice(self.markov[random.choice(self.markov.keys())])))

        for i in xrange(self.chain_length, self.max_words):
            word_choices = self.markov.get(hash(tuple(message[i - self.chain_length : i])))
            if word_choices:
                message.append(self.retrieve_word(random.choice(word_choices)))

        return ' '.join(message)

    def retrieve_word(self, indexes):
        return self.flat_brain[indexes[0]].split()[indexes[1]]

    def dump_brain(self):
        with open(self.brain_file, 'w') as f:
            for line in self.flat_brain:
                f.write(line + '\n')
        print '%i lines brain dumped.' % (len(self.flat_brain))