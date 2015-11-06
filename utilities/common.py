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

    def update(self, progress):
        if progress % self.interval == 0 or progress == self.total:
            percent = progress * 100 / self.total
            sys.stdout.write('\r[{0}{1}] {2}%'.format('#' * percent, ' ' * (100 - percent), percent))
            if progress == self.total:
                sys.stdout.write('\n')
            sys.stdout.flush()