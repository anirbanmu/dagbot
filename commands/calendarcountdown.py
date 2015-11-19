from utilities.calendar import Calendar

class CalendarCountdown():
    def __init__(self, calendar, keywords, modifiers, modifier_filters):
        self.calendar = calendar if type(calendar) is Calendar else Calendar(calendar)
        self.keywords = keywords
        self.modifiers = modifiers
        self.modifier_filters = modifier_filters
        self.events = []

    def response(self, command_modifier):
        event = self.calendar.closest_event(self.modifier_filters[command_modifier])
        if not event:
            return 'No future event found'

        delta = event[1]
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        response = '%s starting in %d %s %02d:%02d:%02d' % (event[0].summary, delta.days, 'days' if delta.days != 1 else 'day', hours, minutes, seconds)
        return response.encode('utf-8')