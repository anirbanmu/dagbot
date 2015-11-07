import sqlite3, pickle
from base64 import b64encode, b64decode

def to_db(data):
    return b64encode(pickle.dumps(data, pickle.HIGHEST_PROTOCOL))

def from_db(data):
    return pickle.loads(b64decode(data))

class DatabaseDictionary(object):
    def __init__(self, file_name):
        self.connection = sqlite3.connect(file_name, isolation_level=None)
        self.cursor = self.connection.cursor()

        self.cursor.execute('PRAGMA journal_mode=WAL')
        self.cursor.execute('PRAGMA synchronous=OFF')

        self.cursor.execute(('CREATE TABLE IF NOT EXISTS dictionary ('
                             'id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,'
                             'key BLOB UNIQUE NOT NULL,'
                             'value BLOB)'))

    def get_random_key(self):
        self.cursor.execute('SELECT key FROM dictionary ORDER BY RANDOM() LIMIT 1')
        key = self.cursor.fetchone()
        return from_db(key[0]) if key else None

    def __setitem__(self, key, value):
        self.cursor.execute('INSERT OR REPLACE INTO dictionary VALUES(null, ?, ?)', (to_db(key), to_db(value)))

    def __getitem__(self, key):
        value = self.get(key)
        if value == None:
            raise KeyError
        return value

    def __delitem__(self, key):
        self.__getitem__(key) # Will ensure key exists
        self.cursor.execute('DELETE FROM dictionary WHERE key = ?', (to_db(key),))

    def update(self, other):
        self.cursor.executemany('INSERT OR REPLACE INTO dictionary VALUES(null, ?, ?)', ((to_db(k), to_db(v)) for k,v in other.iteritems()))

    def replace(self, other):
        self.cursor.execute('DELETE FROM dictionary')
        self.cursor.executemany('INSERT INTO dictionary VALUES(null, ?, ?)', ((to_db(k), to_db(v)) for k,v in other.iteritems()))

    def get(self, key):
        self.cursor.execute('SELECT value FROM dictionary WHERE key = ?', (to_db(key),))
        value = self.cursor.fetchone()
        return from_db(value[0]) if value else None

    def keys(self):
        self.cursor.execute('SELECT key FROM dictionary')
        values = self.cursor.fetchall()
        return [from_db(v[0]) for v in values]

    def key_count(self):
        self.cursor.execute('SELECT COUNT(*) FROM dictionary')
        return self.cursor.fetchone()[0]

    def begin(self):
        self.cursor.execute('BEGIN')

    def commit(self):
        self.connection.commit()
        self.cursor.execute('PRAGMA shrink_memory')

    def close(self):
        self.connection.commit()
        self.connection.close()