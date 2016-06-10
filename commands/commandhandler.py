import abc

class CommandHandler(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self, json_config):
        raise NotImplementedError('__init__ must be defined for a command handler')

    @abc.abstractmethod
    def get_help(self, param_str, chan):
        raise NotImplementedError('get_help must be defined for a command handler')

    @abc.abstractmethod
    def get_response(self, param_str, msg, chan):
        raise NotImplementedError('get_response must be defined for a command handler')