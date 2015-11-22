import string
from collections import OrderedDict
from utilities.calendar import Calendar

class CalendarCountdown(object):
    def __init__(self, calendar, filters):
        self.calendar = calendar if type(calendar) is Calendar else Calendar(calendar)
        self.filters = OrderedDict(sorted(filters.iteritems(), reverse=True, key=lambda t: len(t[0])))

    def get_filter(self, str):
        for f in self.filters:
            if str.startswith(f):
                return self.filters[f]
        return ''

    def get_response(self, param_str):
        event = self.calendar.closest_event(self.get_filter(param_str))
        if not event:
            return 'No future event found'

        delta = event[1]
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        response = '%s starting in %d %s %02d:%02d:%02d' % (event[0].summary, delta.days, 'days' if delta.days != 1 else 'day', hours, minutes, seconds)
        return response.encode('utf-8')

class CalendarCountdownPool(object):
    def __init__(self, json_config):
        self.calendars = {}
        for config in json_config:
            calendar = CalendarCountdown(config['calendar_url'], {k.lower(): v.lower() for k,v in config['filters'].iteritems()})
            for id in config['identifiers']:
                self.calendars[id.lower()] = calendar
        self.calendars = OrderedDict(sorted(self.calendars.iteritems(), reverse=True, key=lambda t: len(t[0])))

    # param_str should be lowercase
    def get_response(self, param_str):
        for id in self.calendars:
            if param_str.startswith(id):
                return self.calendars[id].get_response(param_str[len(id):])
        return 'Logic error'

command_handler_properties = (CalendarCountdownPool, ['@next'])