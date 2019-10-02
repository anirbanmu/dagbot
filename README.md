# dagbot

An IRC Markov Chain chatbot with a simple pluggable command system using Python 3.6. Legacy Python 2 version remains on it's own [branch](https://github.com/anirbanmu/dagbot/tree/legacy-python-2-unmaintained) but is and will be unmaintained.

## Intro

Markov bots work on based on the simple idea of markov chains. They usually require a substantially large corpus (flat text file with known good phrases / sentences). One could call this the "brain" of dagbot. Without a large corpus, markov bots will usually generate gibberish phrases that look nothing like what a human would say.

## Details

Commands have a very simple interface which tell the bot what keywords are triggers & what class should handle said keywords.

All configuration data for the bot is defined & validated via [jsonschema](http://json-schema.org/). The `config_schema.json` file defines the main configuration data that dagbot uses (irc channels, response rate etc). It also serves as documentation of configuration format & what each setting means.

Configuration data for each command is also configurable but by default goes in `commands/config` directory. Command config is totally separate from main bot configuration and is fully customizable. At runtime, all commands are pulled in automatically from the `commands` directory.

Logic for markov responses is fairly simple. First the [pattern](https://github.com/clips/pattern) library is used to try to find interesting words in a phrase like the subject. If none can be found, we fall back to just picking the first n (markov chain length) words of the phrase that was sent to the bot.

The brain file is just a flat text file of sentences that have been seen before (said by a human). Dagbot records all messages said in the IRC channels it joins (unless a channel is configured not to be recorded). This means the brain file you use will be modified when the bot is running. At runtime, the text file is parsed into actual markov chains which are stored in a [sqlite3](https://www.sqlite.org/) backed dictionary. The database was used to save memory since using python's built in dictionary consumes massive amounts of memory.

Dagbot depends on the following libraries:

- [twisted](https://pypi.python.org/pypi/Twisted)
- [ics](https://pypi.python.org/pypi/ics)
- [pattern](https://pypi.python.org/pypi/Pattern)
- [urllib3](https://pypi.python.org/pypi/urllib3)
- [msgpack-python](https://pypi.python.org/pypi/msgpack-python)
- [jsonschema](https://pypi.python.org/pypi/jsonschema)
- [tweepy](https://pypi.python.org/pypi/tweepy)

Running the following should install all the dependencies:

    pip install -r requirements.txt

More info on pip is [here](https://pypi.python.org/pypi/pip) if something breaks.

After you've tweaked the configuration file to your liking, you can start the bot with:

    python sadface.py /path/to/config.json

There is no issue with using [pypy](http://pypy.org/) with dagbot instead of CPython. In fact I fully recommend using pypy!

Dagbot is obviously originally derived from sadface but has at this point diverged & grown substantially from the original code.

You can find dagbot chatting away on a number of channels on [snoonet](https://snoonet.org/) if you're interested in seeing how well it performs. The `#f1` channel is quite familiar with dagbot especially due to the countdown command.

## Credits

- Ben Keith
    - Original author of the markov portion of sadface!

- Eric Florenzano
	- sadface derives heavily from his MomBot Markov bot code
	- http://eflorenzano.com/blog/2008/11/16/writing-markov-chain-irc-bot-twisted-and-python/
	- http://wayback.archive.org/web/20130106092748/http://eflorenzano.com/blog/2008/11/16/writing-markov-chain-irc-bot-twisted-and-python/

- hhokanson
	- sadface's configuration methods derive from her AnonBot IRC anonymizer bot
	- https://bitbucket.org/hhokanson/anonbot/src
