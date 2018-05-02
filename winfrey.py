import sys
import queue
import time
import uuid
import json
import logging
import threading
import argparse
import ntplib
from backend import editor_state as WinfreyEditor
import client as clientpoint
import server as serverpoint

def serialize( uid, name, *args ):
    """Creates a JSON string representation of an update message. Mostly legacy now"""
    message = {
            "uuid": uid,
            "name": name,
            "args": [str(arg) for arg in args]
    }

    return json.dumps( message )

def deserialize( message ):
    """Unpacks a JSON string representation of an update message. Mostly legacy now"""

    nobject = json.loads( message )
    if type(nobject) != dict:
        raise DeserializationError("Received malformed data: {}".format(msg))
    return nobject


class WinfreyServer( WinfreyEditor ):
    """A Winfrey file host. Listens for, receives and applies updates from, and broadcasts updates to,
       connected Winfrey clients."""
    def __init__( self, interact_address, broadcast_address, filename ):
        """Creates a new instance of WinfreyServer

        interact_address: Port for clients to connect to
        broadcast_address: Port to broadcast updates over
        filename: File to host
        """
        self.logger = logging.getLogger("main")
        self.endpoint = serverpoint.Server( interact_address, broadcast_address, self.logger )
        super().__init__( filename )                 

        self.rpc_funcs = {
                "subscribe": self.subscribe,
                "unsubscribe": self.unsubscribe,
                "move_cursor": self.move_cursor,
                "insert_char": self.insert_char,
                "echo_response": self.echo_response
        }

        # Number of seconds between batches of updates
        self.batchDelay = .25
        save_thread = threading.Thread( target=self.save )
        self.subscribers = []
        self.latencyAverages = {}

        self.endpoint.startBackground( preprocess=self._preprocess, handler=self._handle, postprocess=self._postprocess, pollTimeout = 2000 )
        save_thread.start()

        # Buffer Queues for incoming edits
        self.Q1 = queue.Queue()
        self.Q2 = queue.Queue()
        self.activeQ = self.Q1
        self.activeLock = threading.Lock()
        # bundle and broadcast messages in separate thread to preserve fairness
        self.buf_thread = threading.Thread(target=self._bundle_and_broadcast)
        self.buf_thread.start()

    def save( self ):
        """Saves the file every thirty seconds"""

        while True:
            time.sleep(30)
            print( "Saving...." )
            self.write( self.fname )

    def subscribe( self ):
        """Creates and returns a new user with a unique UUID"""

        new_uuid = uuid.uuid4().int
        self.subscribers.append(str(new_uuid))
        print( "Created new user with UUID " + str(new_uuid) )
        self.create_cursor(str(new_uuid))
        self.endpoint.broadcast( '[' + serialize( new_uuid, "create_cursor", new_uuid ) + ']')

        return {"status": "subscribed", "other": {"uuid": new_uuid, "file": self.rows, "cursors": self.cursors }}

    def unsubscribe( self, uuid ):
        """Removes the user with the given UUID"""

        print( "User " + uuid + " left." )
        self.subscribers.remove(uuid)
        del self.latencyAverages[uuid]
        self.remove_cursor( uuid );
        self.endpoint.broadcast( '[' + serialize( uuid, "remove_cursor", uuid ) + ']' )

    def create_cursor( self, cid ):
        """Creates a new cursor object with a given cursor ID. Extends WinfreyEditor.create_cursor"""
        super().create_cursor( cid )
        return {"status": "ok", "other": ""}

    def remove_cursor( self, cid ):
        """Removes the cursor object with the given cursor ID. Extends WinfreyEditor.remove_cursor"""
        super().remove_cursor( cid )
        return {"status": "ok", "other": ""}

    def move_cursor( self, cid, direction ):
        """Moves the cursor with the given CID in the given direction. Extends WinfreyEditor.move_cursor"""
        super().move_cursor( cid, direction )
        return {"status": "ok", "other": ""}

    def insert_char( self, cid, char ):
        """Inserts a character at the cursor with the given CID. Extends WinfreyEditor.insert_char"""
        super().insert_char( cid, char )
        return {"status": "ok", "other": ""}

    def echo_response( self, message ):
        """Action to be taken when the server receives a response from an "echo" message"""
        for m in message: 
            print("ECHO " + m)
        return {"status": "ok", "other": ""}

    def no_such_function(*args):
        return {"status": "fail", "other": "No RPC matches this contract"}

    def _handle( self, procedure ):
        """Callback function for when the server receives a new message."""
        f = procedure["name"]

        if f == "subscribe" or f == "unsubscribe":
            # Subscription message: apply immediately
            reply = self._apply_function( f, *procedure["args"] )
        elif f == "echo_response": 
            # Response to an echo message: apply immediately
            self.updateBatchDelay(procedure["uuid"], procedure["args"])
            reply = self._apply_function( f, procedure["args"] )
        else:
            # Delayable message: check for staleness and add to the update queue
            is_too_old = (float(procedure["time"]) < time.time() - self.batchDelay)
            if is_too_old:
                return {"status": "dropped", "other": "message_too_old"}

            self.activeLock.acquire()
            self.activeQ.put(procedure)
            self.activeLock.release()

            reply = None

        return reply

    def _apply_function( self, name, *args ):
        """Runs an RPC function with the given name and the given arguments."""
        function = self.rpc_funcs.get( name, self.no_such_function )
        return function( *args )

    def updateBatchDelay( self, uuid, message ): 
        if uuid in self.subscribers: 
            avg_rtt = 0.0
            i = 0
            t = time.time()
            print("Current time: " + str(t))
            while i < 5: 
                avg_rtt += t - (float(message[i]) - (.01 * (5 - i)))
                i += 1
            avg_rtt /= 5
            self.latencyAverages[uuid] = avg_rtt
            maxLatency = 0
            for k, v in self.latencyAverages.items(): 
                if maxLatency < v: 
                    maxLatency = v
            self.batchDelay = maxLatency + .05
            print("NEW BATCH DELAY: " + str(self.batchDelay))

    def _bundle_and_broadcast( self ):
        """Bundles all messages currently in the update queue into a single message and
           broadcasts it to all clients."""
        while True:
            time.sleep(self.batchDelay)
            ps = []
            
            self.activeLock.acquire()
            # This implies Q2 is empty
            if self.activeQ is self.Q1: 
                while not self.Q1.empty():
                    ps.append(self.Q1.get())
                self.activeQ = self.Q2
            else: 
                while not self.Q2.empty():
                    ps.append(self.Q2.get())
                self.activeQ = self.Q1
            self.activeLock.release()
            # This section is not critical, so the active lock need not be owned
            ps.sort(key=lambda k: float(k["time"]))
            for procedure in ps:
                self._apply_function( procedure["name"], *procedure["args"] )
            self.endpoint.broadcast( json.dumps(ps) )
            ps.clear()

    def _preprocess( self, message ):
        return deserialize( message )

    def _postprocess( self, message ):
        return json.dumps( message )


class WinfreyClient( WinfreyEditor ):
    """A Winfrey file client. Connects to a file host and relays all changes made by the editor to the server
       and vice versa."""
    def __init__( self, remote_address, broadcast_address ):
        """Creates a new instance of a WinfreyClient.

        remote_address: Server port to specifically connect to
        broadcast_address: Server port to passively listen for updates on"""

        self.logger = logging.getLogger("main")
        self.endpoint = clientpoint.Client( remote_address, broadcast_address, self.logger )
   
        super().__init__()
        # For update buffering
        self.updateQueue = []
        self.queueLock = threading.Lock()
        self.fullyLoaded = False

        self.rpc_funcs = {
                "create_cursor": self.create_cursor,
                "remove_cursor": self.remove_cursor,
                "move_cursor": self.move_cursor,
                "insert_char": self.insert_char
        }

        # Time adjustment thread
        self.offset = 0
        self.stopped = False
        self.time_thread = threading.Thread( target=self.get_time )
        self.timelock = threading.Lock()
        self.ntpclient = ntplib.NTPClient()

        self.time_thread.start()
        self.subscribe()
        self.G.launch()

    def get_time( self ):
        """Updates the offset between the local clock and the NTP time authority every thirty seconds.
        Additionally, pings the Winfrey server every thirty seconds to update network latency data"""
        while True:
            try: 
                response = self.ntpclient.request('0.pool.ntp.org', version=3,
                                                  timeout=15)
            except ntplib.NTPException: 
                self.offset = 0 # We don't know any better, so keep it at 0
            self.timelock.acquire()
            self.offset = response.tx_time - time.time()
            self.echo()
            self.timelock.release()
            for i in range(0, 5):
                if self.stopped:
                    return
                time.sleep(3)

    def move_my_cursor( self, direction ):
        """Callback function for when the local cursor is moved in the given direction. Sends this change
        to the connected server."""
        self.timelock.acquire()
        ltime = time.time() - self.offset
        self.timelock.release()
        reply = self.endpoint.send( json.dumps({"uuid": str(self.my_cursor), "name": "move_cursor", "args": [str(self.my_cursor), str(direction)], "time": str(ltime)}) )

    def echo( self ):
        """Sends a bundle of timestamps to the server"""
        i = 0
        message = []
        while i < 5: 
            trueTime = time.time() - self.offset
            message.append(str(trueTime))
            time.sleep(.01)
            i = i + 1
        if not self.stopped:
            reply = self.endpoint.send( json.dumps({"uuid": str(self.my_cursor),
                                                "name": "echo_response", 
                                                "args": message} ))

    def insert_my_char( self, char ):
        """Callback function for when a character is inserted at the local cursor. Sends this change to the
        connected server."""
        self.timelock.acquire()
        ltime = time.time() - self.offset
        self.timelock.release()
        reply = self.endpoint.send( json.dumps({"uuid": str(self.my_cursor), "name": "insert_char", "args": [str(self.my_cursor), str(char)], "time": str(ltime)}) )

    def subscribe( self ):
        """Sends a subscription message to the connected server, then receives and loads the text file from the
        server's response. Buffers incoming changes during this time."""
        reply = self.endpoint.send( serialize( 0, "subscribe" ), preprocess=self._preprocess_indiv )
        self.endpoint.startBackground( self._handleQueue, preprocess=self._preprocess )
        if reply["status"] == "subscribed":
            self.my_cursor = str(reply["other"]["uuid"])
            self.rows = reply["other"]["file"]
            self.numrows = len( self.rows )
            for i in range( 0, len(self.rows) ):
                self.G.add_line( i, self.rows[i][:-1], [] );
            for cid in reply["other"]["cursors"]:
                cursor = reply["other"]["cursors"][cid]
                self.create_cursor( cid, cursor["cx"], cursor["cy"] )
            self.fullyLoaded = True
            while self.updateQueue: 
                self.queueLock.acquire()
                procedure = self.updateQueue.pop(0)
                self._handle([procedure])
                self.queueLock.release()
        else:
            return None

    def unsubscribe( self ):
        """Unsubscribes and disconnects from the connected server."""
        reply = self.endpoint.send( serialize( self.my_cursor, "unsubscribe", self.my_cursor ), preprocess=self._preprocess_indiv )
        
        self.endpoint.stop()

    def interrupt( self ):
        """Callback function for when the user asks to close the client."""
        self.unsubscribe()
        self.stopped = True

    def _handleQueue( self, procedures ): 
        if not self.fullyLoaded or self.updateQueue: 
            self.queueLock.acquire()
            for procedure in procedures:
                self.updateQueue.append(procedure)
            self.queueLock.release()
        else: 
            self._handle(procedures) 

    def _handle( self, procedures ):
        """Callback function for when an update is received from the server."""
        for procedure in procedures:
            if procedure["uuid"] == self.my_cursor and procedure["name"] == "echo":
                self.echo( procedure["args"] )
            else:
                f = procedure["name"]
                function = self.rpc_funcs.get( f, None )
                if function:
                    function( *procedure["args"] )
        return
    
    def _preprocess( self, message ):
        return json.loads( message )

    def _preprocess_indiv( self, message ):
        return json.loads( message )

if __name__ == "__main__":

    parser = argparse.ArgumentParser( description='You get to edit! You get to edit! Everyone gets to edit!' )
    parser.add_argument('-c', metavar='SERVER_ADDR', help='Starts Winfrey as a client of the given address', action='store', dest='server_addr')
    parser.add_argument('-s', metavar='FILENAME', help='Starts Winfrey as server of the given file', action='store', dest='filename')
    parser.add_argument('iport', help='Interactive port to server', action='store' )
    parser.add_argument('bport', help='Broadcast port from server', action='store' )

    args = parser.parse_args()

    if args.filename:
        winfrey = WinfreyServer( "tcp://*:{}".format(args.iport), "tcp://*:{}".format( args.bport ), args.filename )
    else:
        winfrey = WinfreyClient( "tcp://%s:%s" % (args.server_addr, args.iport), "tcp://%s:%s" % (args.server_addr, args.bport))
