from __future__ import print_function
from __future__ import division
from builtins import object
from past.utils import old_div
import sys, time, math

def time_function(function):
    def timer_wrapper(*args, **kw):
        start = time.time()
        result = function(*args, **kw)
        end = time.time()

        print('[ %s took %f seconds ]' % (function.__name__, end - start))
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
            percent = old_div(self.current * 100, self.total)
            sys.stdout.write('\r[{0}{1}] {2}%'.format('#' * percent, ' ' * (100 - percent), percent))
            if self.current == self.total:
                sys.stdout.write('\n')
            sys.stdout.flush()