import sqlite3
from msgpack import packb, unpackb
from collections import namedtuple
from functools import partial

def to_db(data):
    return sqlite3.Binary(packb(data, use_bin_type=True))

def from_db(data):
    return unpackb(data, use_list=False, encoding='utf-8')

# tuple_type should be a namedtuple if present
def convert_tuple(data, properties, convert, row_values_type):
    assert isinstance(data, tuple)
    converted = []
    for i,field_name in enumerate(row_values_type._fields):
        converted.append(convert(data[i]) if properties[field_name] else data[i])
    return tuple(converted)

# if data has the same fields as tuple_type, then no specific type is required to be passed since a regular tuple is fine when going into the db
def tuple_to_db(data, properties, row_values_type):
    return convert_tuple(data, properties, to_db, row_values_type)

def tuple_from_db(data, properties):
    return convert_tuple(data, properties, from_db)

# tuple_type is expected to be the default namedtuple of all values (key not included) that would be used in the regular case
def named_tuple_factory(cursor, row, properties, row_values_type):
    return row_values_type(*convert_tuple(row, properties, from_db, row_values_type))

ColumnProperties = namedtuple('ColumnProperties', 'blob')

class DatabaseDictionary(object):
    # value_types determines what columns are stored for each key
    def __init__(self, file_name, value_types, row_values_type, auto_vacuum='FULL'):
        assert len(value_types) != 0

        column_types = [('key', 'BLOB UNIQUE NOT NULL')] + value_types

        values_sql = 'VALUES(null' + ',?' * len(column_types) + ')'
        self.insert_sql = 'INSERT INTO dictionary ' + values_sql
        self.insert_replace_sql = 'INSERT OR REPLACE INTO dictionary ' + values_sql
        self.select_sql = 'SELECT ' + ','.join(v[0] for v in value_types) + ' FROM dictionary WHERE key = ?'

        self.connection = sqlite3.connect(file_name, isolation_level = None)
        self.cursor = self.connection.cursor()

        column_properties = {c[0]: 'blob' in c[1].lower() for c in value_types}
        self.cursor.row_factory = partial(named_tuple_factory, properties = column_properties, row_values_type = row_values_type)
        self.tuple_to_db = partial(tuple_to_db, properties = column_properties, row_values_type = row_values_type)

        #self.cursor.execute('PRAGMA journal_mode=WAL')
        #self.cursor.execute('PRAGMA synchronous=OFF')
        self.cursor.execute('PRAGMA auto_vacuum=%s' % (auto_vacuum,))

        self.cursor.execute('CREATE TABLE IF NOT EXISTS dictionary (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,' + ','.join(v[0] + ' ' + v[1] for v in column_types) + ')')

    def get_random_filtered_key(self, filter_conditions):
        cursor = self.connection.cursor()
        cursor.execute('SELECT key FROM dictionary WHERE ' + ' AND '.join(filter_conditions) + ' ORDER BY RANDOM() LIMIT 1')
        row = cursor.fetchone()
        return (from_db(row[0]),) if row else None

    def get_random_key(self):
        cursor = self.connection.cursor()
        cursor.execute('SELECT key FROM dictionary ORDER BY RANDOM() LIMIT 1')
        row = cursor.fetchone()
        return (from_db(row[0]),) if row else None

    def __setitem__(self, key, value):
        self.cursor.execute(self.insert_replace_sql, (to_db(key),) + self.tuple_to_db(value))

    def __getitem__(self, key):
        value = self.get(key)
        if value == None:
            raise KeyError(key)
        return value

    def __delitem__(self, key):
        self.__getitem__(key) # Will ensure key exists
        self.cursor.execute('DELETE FROM dictionary WHERE key = ?', (to_db(key),))

    def __len__(self):
        cursor = self.connection.cursor()
        cursor.execute('SELECT COUNT(*) FROM dictionary')
        return cursor.fetchone()[0]

    def update(self, other):
        self.cursor.executemany(self.insert_replace_sql, ((to_db(k),) + self.tuple_to_db(v) for k,v in other.iteritems()))

    def replace(self, other):
        self.cursor.execute('DELETE FROM dictionary')
        self.cursor.executemany(self.insert_sql, ((to_db(k),) + self.tuple_to_db(v) for k,v in other.iteritems()))

    def get(self, key):
        self.cursor.execute(self.select_sql, (to_db(key),))
        return self.cursor.fetchone()

    def keys(self):
        self.cursor.execute('SELECT key FROM dictionary')
        values = self.cursor.fetchall()
        return [v.key for v in values]

    def begin(self):
        self.cursor.execute('BEGIN')

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.commit()
        self.connection.close()
