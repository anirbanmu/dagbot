import pytz, icalendar, warnings, threading
from urllib3 import PoolManager
from datetime import datetime, timedelta
from collections import namedtuple

Event = namedtuple('Event', ['start', 'end', 'summary'])

def get_raw_events(pool_manager, url):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        with pool_manager.request('GET', url) as r:
            print "Loaded calendar from " + url
            return r.read()

def sanitize_dt(dt):
    # Assume UTC for non tz aware events
    newdt = dt if hasattr(dt, 'hour') else datetime.combine(dt, datetime.min.time()).replace(tzinfo=pytz.UTC)
    newdt = newdt if newdt.tzinfo != None else newdt.replace(tzinfo=pytz.UTC)
    return newdt

# Conservative delta used. No event should be longer than 1 week.
def prune_event_start(start_time, utc_now):
    delta = utc_now - sanitize_dt(start_time)
    return delta > timedelta(weeks=1)

def prune_event_end(end_time, utc_now):
    return sanitize_dt(end_time) < utc_now

def prune_event(event, utc_now, start, end):
    return prune_event_start(start.dt, utc_now) or (end and prune_event_end(end.dt, utc_now))

def prune_past_events(ics_events, now):
    utc_now = now.replace(tzinfo=pytz.UTC)
    events = []
    for component in ics_events.walk():
            if component.name == "VEVENT":
                start = component.get('dtstart')
                end = component.get('dtend')
                if prune_event(component, utc_now, start, end):
                    continue
                events.append(Event(sanitize_dt(start.dt), sanitize_dt(end.dt) if end else None, component.get('summary')))
    return events

def closest_event(events, event_type_end):
    deltas = []
    utc_now = sanitize_dt(datetime.utcnow())
    for event in events:
        delta = event.start - utc_now
        if (event.summary.lower().endswith(event_type_end) and delta > timedelta(microseconds=0)):
            deltas.append((event, delta))
    deltas.sort(key=lambda x: x[1])
    return deltas[0] if deltas else None

def in_event(events, default_event_duration):
    utc_now = sanitize_dt(datetime.utcnow())
    for event in events:
        end = event.end if event.end else event.start + default_event_duration
        if event.start < utc_now and utc_now < end:
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
    update_interval = timedelta(days=1)
    default_event_duration = timedelta(minutes=90)
    pool_manager = PoolManager()

    def __init__(self, calendar_url):
        self.lock = threading.Lock()
        self.calendar_url = calendar_url
        self.last_updated = datetime.min
        self.events = []
        self.__update_calendar()

    def __update_calendar(self):
        if datetime.utcnow() - self.last_updated > self.update_interval:
            self.__get_new_calendar()

    def __get_new_calendar(self):
        self.last_updated = datetime.utcnow()
        self.events = prune_past_events(icalendar.Calendar.from_ical(get_raw_events(self.pool_manager, self.calendar_url)), self.last_updated)

    def __get_events(self):
        with self.lock:
            self.__update_calendar()
            return list(self.events)

    def closest_event(self, event_end_filter):
        return closest_event(self.__get_events(), event_end_filter)

    def in_event(self):
        return in_event(self.__get_events(), self.default_event_duration)