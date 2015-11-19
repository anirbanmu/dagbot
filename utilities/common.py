import sys, time, math

def time_function(function):
    def timer_wrapper(*args, **kw):
        start = time.time()
        result = function(*args, **kw)
        end = time.time()

        print '[ %s took %f seconds ]' % (function.__name__, end - start)
        return result
    return timer_wrapper

class ProgressBar(object):
    def __init__(self, total):
        self.total = total
        self.interval = int(math.ceil(total * 0.01))
        self.current = 0

    def update(self):
        self.current += 1
        if self.current % self.interval == 0 or self.current == self.total:
            percent = self.current * 100 / self.total
            sys.stdout.write('\r[{0}{1}] {2}%'.format('#' * percent, ' ' * (100 - percent), percent))
            if self.current == self.total:
                sys.stdout.write('\n')
            sys.stdout.flush()

# JSON encoding conversion taken from http://stackoverflow.com/questions/956867/how-to-get-string-objects-instead-of-unicode-ones-from-json-in-python/6633651#6633651
def _json_list_change_encode(l, encoding):
    encoded_list = []
    for v in l:
        if isinstance(v, unicode):
            v = v.encode(encoding)
        elif isinstance(v, list):
            v = _json_list_change_encode(v, encoding)
        elif isinstance(v, dict):
            v = _json_dict_change_encode(v, encoding)
        encoded_list.append(v)
    return encoded_list

def _json_dict_change_encode(d, encoding='utf-8'):
    encoded_dict = {}
    for k,v in d.iteritems():
        if isinstance(k, unicode):
            k = k.encode(encoding)
        if isinstance(v, unicode):
            v = v.encode(encoding)
        elif isinstance(v, list):
            v = _json_list_change_encode(v, encoding)
        elif isinstance(v, dict):
            v = _json_dict_change_encode(v, encoding)
        encoded_dict[k] = v
    return encoded_dict

def json_encode(json_dict, encoding):
    return _json_dict_change_encode(json_dict, encoding)