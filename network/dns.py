#!/usr/bin/env python3

import socket

def ip(name, port = 80):
    """
    Do a dns lookup of name and port to get the host ip
    """
    return socket.getaddrinfo(name, port)[0][4][0]
