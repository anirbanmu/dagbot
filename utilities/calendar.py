import warnings, threading, arrow, ics
from urllib3 import PoolManager
from datetime import datetime, timedelta
from collections import namedtuple

def get_raw_events(pool_manager, url):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        print 'Loading calendar from ' + url
        r = pool_manager.request('GET', url).data
        return r

# Conservative delta used. No event should be longer than 5 days.
def prune_event_start(start_time, utc_now):
    delta = utc_now - start_time
    return delta > timedelta(days=5)

def prune_event_end(end_time, utc_now):
    return end_time < utc_now

def prune_event(event, utc_now, start, end):
    return prune_event_start(start, utc_now) or (end and prune_event_end(end, utc_now))

def prune_past_events(calendar, utc_now):
    return [e for e in calendar.events if not prune_event(e, utc_now, e.begin, e.end if e.has_end() else None)]

def event_allowed(event, filter_options, required_string):
    event_name = event.name.lower()
    if required_string not in event_name:
        return False

    field_value = getattr(event, filter_options['event_field_name'], u'')

    # Only handles string & list-like
    if not isinstance(field_value, basestring):
        return any((filter_options['filter_string'] in v.lower()) for v in field_value)

    return filter_options['filter_string'] in field_value.lower()

def closest_event(events, filter_options, required_string):
    deltas = []
    utc_now = arrow.utcnow()
    for event in (e for e in events if event_allowed(e, filter_options, required_string)):
        delta = event.begin - utc_now
        end = event.end if event.has_end() else event.begin
        if delta > timedelta(microseconds=0):
            deltas.append((event, delta))
        elif (event.begin < utc_now and end > utc_now):
            deltas.append((event, utc_now - end))
    deltas.sort(key=lambda x: x[1])
    return deltas[0] if deltas else None

def in_event(events, default_event_duration, longest_duration, required_string):
    utc_now = arrow.utcnow()
    for event in (e for e in events if required_string in e.name.lower()):
        end = event.end if event.has_end() else event.begin + default_event_duration
        if event.begin < utc_now and utc_now < end and end - event.begin < longest_duration:
            return True
    return False

def singleton_per_args(cls):
    singletons = {}
    singletons_lock = threading.Lock()
    def get_instance(*args):
        key = (cls,) + args
        with singletons_lock:
            if key not in singletons:
                singletons[key] = cls(*args)
            return singletons[key]
    return get_instance

@singleton_per_args
class Calendar(object):
    update_interval = timedelta(hours=6)
    default_event_duration = timedelta(minutes=90)
    pool_manager = PoolManager()

    def __init__(self, calendar_url):
        self.lock = threading.Lock()
        self.calendar_url = calendar_url
        self.last_updated = arrow.get(datetime.min)
        self.events = []
        self.__update_calendar()

    def __update_calendar(self):
        if arrow.utcnow() - self.last_updated > self.update_interval:
            self.__get_new_calendar()

    def __get_new_calendar(self):
        self.last_updated = arrow.utcnow()
        self.events = prune_past_events(ics.Calendar(get_raw_events(self.pool_manager, self.calendar_url).decode('utf-8')), self.last_updated)

    def __get_events(self):
        with self.lock:
            self.__update_calendar()
            return list(self.events)

    # filter_options = { 'event_field_name': 'field_name', 'filter_string': 'string to check for' }
    def closest_event(self, filter_options, required_string):
        return closest_event(self.__get_events(), filter_options, required_string)

    def in_event(self, longest_duration, required_string):
        return in_event(self.__get_events(), self.default_event_duration, longest_duration, required_string)
