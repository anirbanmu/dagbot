import sys

class ProgressBar(object):
    def __init__(self, total, interval):
        self.total = total
        self.interval = interval

    def update(self, progress):
        if progress % self.interval == 0 or progress == self.total:
            percent = progress * 100 / self.total
            sys.stdout.write('\r[{0}{1}] {2}%'.format('#'*(percent), ' '*(100-percent), percent))
            if progress == self.total:
                sys.stdout.write('\n')
            sys.stdout.flush()