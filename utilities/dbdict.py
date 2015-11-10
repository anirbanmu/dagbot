import sqlite3, pickle
from base64 import b64encode, b64decode
from collections import namedtuple

def to_db(data):
    return b64encode(pickle.dumps(data, pickle.HIGHEST_PROTOCOL))

def from_db(data):
    return pickle.loads(b64decode(data))

def convert_tuple(data, properties, tuple_type, convert):
    assert isinstance(data, tuple)
    assert len(data) == len(properties)
    converted = []
    for i,v in enumerate(data):
        converted.append(convert(v) if properties[i].convert else v)
    return tuple_type(*converted)

def tuple_to_db(data, properties, tuple_type):
    return convert_tuple(data, properties, tuple_type, to_db)

def tuple_from_db(data, properties, tuple_type):
    return convert_tuple(data, properties, tuple_type, from_db)

ValueProperties = namedtuple('ValueProperties', 'name, type, convert')

class DatabaseDictionary(object):
    # value_types determines what columns are stored for each key
    def __init__(self, file_name, value_types):
        self.connection = sqlite3.connect(file_name, isolation_level=None)
        self.cursor = self.connection.cursor()

        assert len(value_types) != 0

        self.cursor.execute('PRAGMA journal_mode=WAL')
        self.cursor.execute('PRAGMA synchronous=OFF')

        self.value_props = [ValueProperties(v[0], v[1], 'blob' in v[1].lower()) for v in value_types]

        values_sql = 'VALUES(null, ?' + ',?' * len(self.value_props) + ')'
        self.insert_sql = 'INSERT INTO dictionary ' + values_sql
        self.insert_replace_sql = 'INSERT OR REPLACE INTO dictionary ' + values_sql
        self.select_sql = 'SELECT ' + ','.join(v.name for v in self.value_props) + ' FROM dictionary WHERE key = ?'
        self.row_tuple = namedtuple('RowTuple', ','.join(v.name for v in self.value_props))

        self.cursor.execute('CREATE TABLE IF NOT EXISTS dictionary (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, key BLOB UNIQUE NOT NULL,' + ','.join(v.name + ' ' + v.type for v in self.value_props) + ')')

    def get_random_filtered_key(self, filter_conditions):
        self.cursor.execute('SELECT key FROM dictionary WHERE ' + ' AND '.join(filter_conditions) + ' ORDER BY RANDOM() LIMIT 1')
        key = self.cursor.fetchone()
        return from_db(key[0]) if key else None

    def get_random_key(self):
        self.cursor.execute('SELECT key FROM dictionary ORDER BY RANDOM() LIMIT 1')
        key = self.cursor.fetchone()
        return from_db(key[0]) if key else None

    def __setitem__(self, key, value):
        self.cursor.execute(self.insert_replace_sql, (to_db(key),) + tuple_to_db(value, self.value_props, self.row_tuple))

    def __getitem__(self, key):
        value = self.get(key)
        if value == None:
            raise KeyError
        return value

    def __delitem__(self, key):
        self.__getitem__(key) # Will ensure key exists
        self.cursor.execute('DELETE FROM dictionary WHERE key = ?', (to_db(key),))

    def update(self, other):
        self.cursor.executemany(self.insert_replace_sql, ((to_db(k),) + tuple_to_db(v, self.value_props, self.row_tuple) for k,v in other.iteritems()))

    def replace(self, other):
        self.cursor.execute('DELETE FROM dictionary')
        self.cursor.executemany(self.insert_sql, ((to_db(k),) + tuple_to_db(v, self.value_props, self.row_tuple) for k,v in other.iteritems()))

    def get(self, key):
        self.cursor.execute(self.select_sql, (to_db(key),))
        value = self.cursor.fetchone()
        return tuple_from_db(value, self.value_props, self.row_tuple) if value else None

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