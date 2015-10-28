import pytz
from urllib2 import urlopen
from datetime import datetime, timedelta
from icalendar import Calendar, Event

def get_raw_events(url):
    file = urlopen(url)
    contents = file.read()
    file.close()
    return contents

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

def prune_event(event, utc_now):
    start = event.get('dtstart')
    end = event.get('dtend')
    return not hasattr(start.dt, 'hour') or prune_event_start(start.dt, utc_now) or (end and prune_event_end(end.dt, utc_now))

def prune_past_events(ics_events, now):
    utc_now = now.replace(tzinfo=pytz.UTC)
    events = []
    for component in ics_events.walk():
            if component.name == "VEVENT":
                end = component.get('dtend')
                if prune_event(component, utc_now):
                    continue
                events.append(component)
    return events

def closest_event(events, event_type_end):
    deltas = []
    utc_now = sanitize_dt(datetime.utcnow())
    for event in events:
        delta = sanitize_dt(event.get('dtstart').dt) - utc_now
        if (event.get('summary').lower().endswith(event_type_end) and delta > timedelta(microseconds=0)):
            deltas.append((event, delta))
    deltas.sort(key=lambda x: x[1])
    if (len(deltas) == 0):
        return None
    return deltas[0]

class CalendarCountdown():
    update_interval = timedelta(days=1)
    def __init__(self, calendar_url, keywords, modifiers, modifier_filters):
        self.calendar_url = calendar_url
        self.keywords = keywords
        self.modifiers = modifiers
        self.modifier_filters = modifier_filters
        self.events = []
        self.last_updated = datetime.min
        self.update_calendar()

    def update_calendar(self):
        if datetime.utcnow() - self.last_updated > self.update_interval:
            self.get_new_calendar()

    def get_new_calendar(self):
        self.last_updated = datetime.utcnow()
        self.events = prune_past_events(Calendar.from_ical(get_raw_events(self.calendar_url)), self.last_updated)

    def response(self, command_modifier):
        self.update_calendar()
        event = closest_event(self.events, self.modifier_filters[command_modifier])
        if not event:
            return 'No future event found'

        delta = event[1]
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        response = '%s starting in %d %s %02d:%02d:%02d' % (event[0].get('summary'), delta.days, 'days' if delta.days != 1 else 'day', hours, minutes, seconds)
        return response.encode('ascii')