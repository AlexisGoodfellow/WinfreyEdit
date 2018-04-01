#!/usr/bin/env python3

import zmq

from base.exceptions import GenericError
from base.loggable import Loggable, StdErr
from conf import logging as log

import logging
from threading import Lock, Thread
from functools import partial

# Need signal handlers to properly run as daemon
import signal
import sys
import traceback

DEBUG = False

# bsock -> Publish/Subscribe
# isock -> Request/Reply
class Server(Loggable):
    cxt = zmq.Context()
    def __init__(self, interactiveAddress, broadcastAddress, logger):
        """
        Server.__init__(self, interactiveAddress, broadcastAddress, logger)
        A network server.
        interactive_address and broadcast_address must be 
        available for this application to bind to.
        logger must support at least the methods of base.loggable.Loggable
        """
        super(Server, self).__init__(logger)

        self.iaddr = interactiveAddress
        self.isock = self.cxt.socket(zmq.REP)
        self.isock.bind(self.iaddr)

        self.baddr = broadcastAddress
        self.bsock = self.cxt.socket(zmq.PUB)
        self.bsock.bind(self.baddr)

        self.dlock = Lock()
        self.done = False

        self.ilock = Lock()
        self.block = Lock()

        self.listenThread = None

    def broadcast(self, message):
        """
        Server.broadcast(self, message)
        Broadcast a message to all subscribed clients
        """
        self.info("Broadcasting {}".format(message))
        with self.block:
            self.bsock.send_string(message)

    def fail(self, message, reason):
        """
        Server.fail(self, message, reason)
        Send a failure message to a client
        """
        self.error("Failure ({}): {}".format(message, reason))
        self.isock.send_string("Failure ({}): {}".format(reason,
            message))

    def startBackground(self, preprocess = lambda msg: msg,
            handler = lambda msg: msg, postprocess = lambda msg: msg,
            pollTimeout = 2000):
        """
        Server.start_background
        Starts Server.continuouslyListen() in a background thread
        For more elaborate info, see Server.continuouslyListen()
        """
        if self.listenThread != None: 
            return
        self.listenThread = Thread(target = self.continuouslyListen,
                args = (preprocess, handler, postprocess, pollTimeout))
        self.listenThread.start()

    def continuouslyListen(self, preprocess = lambda msg: msg,
            handler = lambda x, n: x, postprocess = lambda msg: msg,
            pollTimeout = 2000):
        """
        Server.continuouslyListen(self, preprocess = lambda msg: msg,
                handler = lambda msg: msg, postprocess = lambda msg: msg, 
                poll_timeout = 2000)
        Polls for messages on the interactive socket until the server is
        stopped. A poll operation will wait pollTimeout milliseconds before
        failing.
        Messages pipelined preprocess -> handler -> postprocess
        The tail end of the pipeline is sent back to the client
        """
        try:
            while True:
                with self.dlock:
                    if self.done: 
                        break
                with self.ilock:
                    nmsg = self.isock.poll(pollTimeout)
                    if nmsg == 0:
                        continue
                    message =  self.isock.recv_string()
                    # Catch and ignore _all_ exceptions to keep server up
                    try:
                        try:
                            message = preprocess(message)
                        except GenericError as e:
                            self.fail(message, "Internal server error")
                            continue

                        try:
                            reply = handler(message)
                        except GenericError as e:
                            self.fail(message, "Internal server error")
                            continue

                        try:
                            reply = postprocess(reply)
                        except GenericError as e:
                            self.fail(message, "Internal server error")
                            continue
                    except:
                        self.fail(message, "Malformed message")
                        self.error("Uncaught exception: {}"
                                .format(traceback.format_exc()))
                        continue

                    self.isock.send_string(reply)
        except KeyboardInterrupt as e:
            self.stop()

    def stop(self):
        """
        Server.stop(self)
        Stop the server
        """
        self.info("Server shutdown imminent")
        with self.dlock:
            self.info("Stopping poll requests")
            self.done = True

        with self.ilock:
            iaddr = self.isock.last_endpoint.decode()
            self.info("Unbinding isock from {}".format(iaddr))
            self.isock.unbind(iaddr)

        with self.block:
            baddr = self.bsock.last_endpoint.decode()
            self.info("Unbinding bsock from {}".format(baddr))
            self.bsock.unbind(baddr)

        self.listenThread.join()

        self.info("Server shutdown complete")

def echo(server, message):
    """
    Echo the message back to the client
    """
    server.info("Echoing {}".format(message))
    server.broadcast(message)
    return message

def stop_server(sig, frame, server):
    server.stop()

if __name__ == "__main__":
    log.setup()
    logging.getLogger(__name__).info("This is a test")

    # Set up the server
    s = Server("tcp://127.0.0.1:5000", "tcp://127.0.0.1:6667",
            logging.getLogger("server"))

    # Stop the server on signals
    signal.signal(signal.SIGINT , lambda sig, f: stop_server(sig, f, s))
    signal.signal(signal.SIGQUIT, lambda sig, f: stop_server(sig, f, s))
    signal.signal(signal.SIGTERM, lambda sig, f: stop_server(sig, f, s))


    # Start listening
    s.startBackground(handler=partial(echo, s))

