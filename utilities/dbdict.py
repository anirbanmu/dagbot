import sqlite3, pickle, json

def to_db(data):
    return pickle.dumps(data, pickle.HIGHEST_PROTOCOL).encode('base64')

def from_db(data):
    return pickle.loads(data.decode('base64'))

class DatabaseDictionary(object):
    def __init__(self, file_name):
        self.connection = sqlite3.connect(file_name)
        self.cursor = self.connection.cursor()

        self.cursor.execute(('CREATE TABLE IF NOT EXISTS dictionary ('
                             'id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,'
                             'key TEXT UNIQUE NOT NULL,'
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

    def get(self, key):
        self.cursor.execute('SELECT value FROM dictionary WHERE key = ?', (to_db(key),))
        value = self.cursor.fetchone()
        return from_db(value[0]) if value else None

    def keys(self):
        self.cursor.execute('SELECT key FROM dictionary')
        values = self.cursor.fetchall()
        return [from_db(v[0]) for v in values]

    def key_count(self):
        self.cursor.execute('SELECT COUNT(*) from dictionary')
        return self.cursor.fetchone()[0]

    def commit(self):
        self.cursor.execute('PRAGMA shrink_memory')
        self.cursor.execute('VACUUM')
        self.connection.commit()

    def close(self):
        self.connection.close()