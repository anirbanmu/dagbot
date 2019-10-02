from builtins import object
import string
from collections import OrderedDict, namedtuple

from utilities.calendar import Calendar
from commands.commandhandler import CommandHandler
from datetime import timedelta

def generate_current_event(event, delta):
    delta = -delta
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return '%s is in session and will end in %d %s %02d:%02d:%02d.' % (event.name, delta.days, 'days' if delta.days != 1 else 'day', hours, minutes, seconds)

def generate_future_event(event, delta):
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return '%s starting in %d %s %02d:%02d:%02d.' % (event.name, delta.days, 'days' if delta.days != 1 else 'day', hours, minutes, seconds)

EventFilter = namedtuple('EventFilter', ['event_field_name', 'filter_string'])

class CalendarCountdown(object):
    def __init__(self, calendar, filters, description, required_string):
        self.calendar = calendar if type(calendar) is Calendar else Calendar(calendar)
        self.filters = OrderedDict({ k: EventFilter(**v) for k,v in sorted(filters.items(), reverse=True, key=lambda t: len(t[0])) })
        self.description = description
        self.required_string = required_string

    def get_filter(self, str):
        for f,v in self.filters.items():
            if str.startswith(f):
                return (f, v)
        return (u'', EventFilter(event_field_name=u'name', filter_string=u''))

    def get_help(self, param_str):
        if len(self.filters.keys()) == 0:
            return []

        filter_str = self.get_filter(param_str)
        if (filter_str[0] == ''):
            return [', '.join(self.filters.keys())]

        return [filter_str[0] + ' - ' + filter_str[1]]


    def get_response(self, param_str):
        event = self.calendar.closest_event(self.get_filter(param_str)[1], self.required_string)
        if not event:
            return 'No event found'

        # Delta will be negative if event in session
        delta = event[1]
        return generate_current_event(event[0], delta) if delta < timedelta(microseconds=0) else generate_future_event(event[0], delta)

# Keys are assumed to be strings & values are assumed to be strings if not another dict
def lower_and_decode_dict(dictionary):
    return { k.lower(): (lower_and_decode_dict(v) if isinstance(v, dict) else v.lower()) for k,v in dictionary.items() }

class CalendarCountdownPool(CommandHandler):
    def __init__(self, json_config):
        self.calendars = {}
        self.default_id = None
        for config in json_config:
            required_string = config['required_string'] if 'required_string' in config else ''
            filters = lower_and_decode_dict(config['filters'])
            calendar = CalendarCountdown(config['calendar_url'], filters, config['descriptor'], required_string.lower())
            for id in config['identifiers']:
                self.calendars[id.lower()] = calendar

            if 'default_id' in config and config['default_id']:
                self.default_id = config['identifiers'][0].lower()

        self.calendars = OrderedDict(sorted(self.calendars.items(), reverse=True, key=lambda t: len(t[0])))

    def choose_calendar_id(self, param_str, chan):
        for id in self.calendars:
            if param_str.startswith(id):
                return (id, param_str[len(id):])

        if chan[1:] in self.calendars:
            return (chan[1:], param_str)

        return (self.default_id, param_str)

    def get_help(self, param_str, chan):
        base_help = 'Display time to next event in specified calendar'
        if param_str.strip() == '':
            return [base_help, ', '.join(self.calendars.keys())]

        id,filter = self.choose_calendar_id(param_str, chan)
        calendar = self.calendars[id]
        return [base_help, "%s - %s" % (id, calendar.description)] + calendar.get_help(filter)

    # param_str should be lowercase
    def get_response(self, param_str, _, chan):
        param_str = param_str.strip()
        id,filter = self.choose_calendar_id(param_str, chan)
        filter = filter.strip()
        if not id:
            return 'Bad calendar countdown config. Check your JSON.'

        return self.calendars[id].get_response(filter)

command_handler_properties = (CalendarCountdownPool, ['next'], False)
