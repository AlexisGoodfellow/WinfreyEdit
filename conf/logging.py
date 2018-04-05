import os, sys

import logging
import logging.config

def setup():
    """
    Set up logging configs based on a logging config file.
    """

    try:
        os.mkdir("logs")
    except FileExistsError as e:
        pass

    logging.config.fileConfig(os.path.join(os.path.dirname(__file__),
                                           "logging.conf"))

