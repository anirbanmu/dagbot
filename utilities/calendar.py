from __future__ import print_function
from past.builtins import basestring
from builtins import object
import warnings, threading, arrow, ics, re
from urllib3 import PoolManager
from datetime import datetime, timedelta
from collections import namedtuple

def get_raw_events(pool_manager, url):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        print('Loading calendar from ' + url)
        r = pool_manager.request('GET', url).data
        return r

def fix_calendar_data(data):
    # Remove semicolon from RRULE to make dateutil happy
    fixed = re.sub(r'^(RRULE:\S+);\s*$', r'\1', data, 0, re.MULTILINE)

    # Correct TZID specified incorrectly as TZID="Australia/Adelaide" (don't need quotes)
    timezones = frozenset(re.findall(r'^TZID:(\S+)\s*$', data, re.MULTILINE))
    def replacement_timezone(matched):
        if matched.group('original') not in timezones and matched.group('inner') in timezones:
            return u';TZID={}'.format(matched.group('inner'))

        return matched.group(0)

    return re.sub(r';TZID=(?P<original>(?<!\\)"(?P<inner>\S+?)(?<!\\)")', replacement_timezone, fixed)

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

def event_allowed(event, event_filter, required_string):
    event_name = event.name.lower()
    if required_string not in event_name:
        return False

    field_value = getattr(event, event_filter.event_field_name, u'')

    # Only handles string & list-like
    if not isinstance(field_value, basestring):
        return any((event_filter.filter_string in v.lower()) for v in field_value)

    return event_filter.filter_string in field_value.lower()

def closest_event(events, event_filter, required_string):
    deltas = []
    utc_now = arrow.utcnow()
    for event in (e for e in events if event_allowed(e, event_filter, required_string)):
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

        calendar_data = fix_calendar_data(get_raw_events(self.pool_manager, self.calendar_url).decode('utf-8'))
        self.events = prune_past_events(ics.Calendar(calendar_data), self.last_updated)

    def __get_events(self):
        with self.lock:
            self.__update_calendar()
            return list(self.events)

    # event_filter = EventFilter(event_field_name='field_name', filter_string='string to check for')
    def closest_event(self, event_filter, required_string):
        return closest_event(self.__get_events(), event_filter, required_string)

    def in_event(self, longest_duration, required_string):
        return in_event(self.__get_events(), self.default_event_duration, longest_duration, required_string)
