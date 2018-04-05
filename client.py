#!/usr/bin/env python3

import zmq

from base.exceptions import GenericError
from base.loggable import Loggable, BitBucket

from threading import Thread, Lock
from queue import Queue

class Subscription(Loggable):
    def __init__(self, remoteAddress, zmqCxt, logger):
        """
        Subscription.__init__(self, remoteAddress, zmqCxt, logger)
        Subscription to a publishing endpoint at remoteAddress
        Requires a zmq context.
        """
        super(Subscription, self).__init__(logger)

        self.cxt = zmqCxt

        # Subscription to remote broadcasts
        self.addr = remoteAddress
        self.sock = self.cxt.socket(zmq.SUB)
        self.sock.setsockopt_string(zmq.SUBSCRIBE, "")
        self.sock.connect(self.addr)

        self.backlog = Queue(1024)
        self.lock = Lock()

    def recv(self, pollTimeout = 500):
        """
        Subscription.recv(self, pollTimeout = 500)
        Receive a message from the server, timing out after 
        pollTimeout milliseconds.
        Returns string on success, None on failure
        """
        # Check backlog 
        with self.lock:
            if not self.backlog.empty():
                msg = self.backlog.get()
            else:
                nmsg = self.sock.poll(pollTimeout)
                if nmsg == 0:
                    msg = None
                    return msg
                # Process the oldest messages in the backlog first
                for i in range(nmsg):
                    self.backlog.put(self.sock.recv_string())
                msg = self.backlog.get()

        return msg

    def stop(self):
        """
        Subscription.stop(self)
        Stop listening for broadcasts.
        """
        with self.lock:
            self.sock.disconnect(self.addr)
            self.sock.close()

# For legacy reasons, broadcast handler is separate: Subscription.
class Client(Loggable):
    cxt = zmq.Context()
    def __init__(self, remoteAddress, broadcastAddress, logger):
        """
        Client.__init__(self, remoteAddress, broadcastAddress, logger)
        Opens both an interactive connection and a subscription to the server.
        logger must support at least the methods of base.loggable.Loggable
        """
        super(Client, self).__init__(logger)
        # Interact with remote server
        self.raddr = remoteAddress
        self.isock = self.cxt.socket(zmq.REQ)
        self.isock.connect(self.raddr)

        # Receive broadcasts
        self.done = False
        self.background = None
        self.listener = Subscription(broadcastAddress, self.cxt, logger)

        self.lock = Lock()
        self.backgroundLock = Lock()

    def send(self, message, preprocess = lambda x: x):
        """
        Client.send(self, message, preprocess = lambda msg: msg)
        Send a message down the interactive socket, blocking until a reply is
        received.
        The reply is fed through preprocess before being returned
        """
        with self.lock:
            self.isock.send_string(message)
            msg = self.isock.recv_string()

            try:
                msg = preprocess(msg)
            except GenericError as e:
                self.error("Failed to preprocess message {}".format(message))
                raise e
            return msg

    def pauseBackground(self):
        self.backgroundLock.acquire()

    def resumeBackground(self):
        self.backgroundLock.release()

    def continuouslyListen(self, handler, preprocess = lambda x: x,
            pollTimeout = 500):
        """
        Client.continuouslyListen(self, handler,
            preprocess = lambda msg: msg, poll_timeout = 500)
        Poll for messages until the client is stopped
        Messages are pipelined through preprocess and then handler.
        """
        while True:
            with self.lock:
                if self.done: break

            # Don't pause mid-message
            with self.backgroundLock:
                msg = self.listener.recv(pollTimeout)
                if msg == None:
                    continue

                try:
                    msg = preprocess(msg)
                except GenericError as e:
                    self.error("Failed to preprocess {}".format(msg))
                    continue

                try:
                    handler(self, msg)
                except GenericError as e:
                    self.error("Failure when handling {}".format(msg))
                    continue

        self.listener.stop()

    def startBackground(self, handler, preprocess = lambda x: x,
            pollTimeout = 500):
        """
        Client.start_background(self, handler, preprocess = lambda msg: msg,
            pollTimeout = 500)
        Hands off to Client.continuouslyListen()
        Starts a new thread listening for broadcasts from the remote server
        Does nothing if the thread has already been started
        """
        with self.lock:
            if self.background != None:
                return

            self.background = Thread(target = self.continuouslyListen,
                                     args = (handler, preprocess, pollTimeout))

            self.background.start()

    def stop(self):
        """
        Client.stop(self)
        Stop the client entirely.
        """
        self.info("Stopping client")
        with self.lock:
            self.isock.disconnect(self.raddr)
            self.isock.close()

            self.done = True

        self.background.join()
        self.background = None

        self.info("Client stopped")

def echo(server, message):
    return message

def id(n, m):
    return n + m

if __name__ == "__main__":
    # Set up the clients 
    s1 = Client("tcp://127.0.0.1:5000", "tcp://127.0.0.1:5001", BitBucket)
    s2 = Client("tcp://127.0.0.1:5000", "tcp://127.0.0.1:5001", BitBucket)

    # Start broadcast handlers
    s1.startBackground(echo, lambda m: id("1: ", m), 500)
    s2.startBackground(echo, lambda m: id("2: ", m), 500)

    # Poke the server
    for i in range(10):
        rep = s1.send("Hello", lambda m: id("1: ", m))
        print("Reply: " + rep)

        rep = s2.send("Hi", lambda m: id("2: ", m))
        print("Reply: " + rep)

    # Stop the clients
    s1.stop()
    s2.stop()

