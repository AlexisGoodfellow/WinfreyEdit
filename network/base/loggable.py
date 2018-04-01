from . import exceptions

import logging

class IsNone(exceptions.GenericError): pass

class Loggable:
    """
    Base class for logging
    """
    def __init__(self, logger):
        if logger == None:
            raise IsNone("Logger must not be None")
        self.logger = logger

    def info    (self, m): self.logger.info    (m)
    def debug   (self, m): self.logger.debug   (m)
    def warn    (self, m): self.logger.warn    (m)
    def error   (self, m): self.logger.error   (m)
    def critical(self, m): self.logger.critical(m)

class Bitbucket(Loggable):
    """
    Toss all logging into the bitbucket
    """
    def __init__(self, logger = None): pass

    def info    (self, m): pass
    def debug   (self, m): pass
    def warn    (self, m): pass
    def error   (self, m): pass
    def critical(self, m): pass

BitBucket = Bitbucket()

class AdHoc:
    """
    Ad-Hoc logger for Loggable. 
    Provide your own file-like object that supports write() - 
    Usually an open file or sys.stderr.
    Does not do formatting, etc
    """
    def __init__(self, sink, loglevel = logging.DEBUG, name = None, **kwargs):
        """
        Use kwargs to provide prefixes for custom loglevels. Defaults are:
            INFO
            DEBUG
            WARNING
            ERROR
            CRITICAL
        Prefixes default to the names of the loglevels
        The logger name is provided alongside all messages
        """
        self.sink = sink
        self.level = loglevel
        self.name = "{}/".format(name) if name else ""

        self.prefixes = {
                "info": "[{}INFO]: ".format(self.name),
                "debug": "[{}DEBUG]: ".format(self.name),
                "warning": "[{}WARNING]: ".format(self.name),
                "error": "[{}ERROR]: ".format(self.name),
                "critical": "[{}CRITICAL]: ".format(self.name),
        }
        self.prefixes.update(kwargs)

    def log(self, message, level):
        message = str(message)
        if self.level <= level:
            self.sink.write(message + "\n")

    def info(self, m):
        self.log(self.prefixes["info"] + str(m), logging.INFO)

    def debug(self, m):
        self.log(self.prefixes["debug"] + str(m), logging.DEBUG)

    def warn(self, m):
        self.log(self.prefixes["warn"] + str(m), logging.WARNING)

    def error(self, m):
        self.log(self.prefixes["error"] + str(m), logging.ERROR)

    def critical(self, m):
        self.log(self.prefixes["critical"] + str(m), logging.CRITICAL)

import sys
StdErr = AdHoc(sys.stderr, name = "stderr")
