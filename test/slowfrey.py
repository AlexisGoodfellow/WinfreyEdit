import time
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import winfrey

class SlowWinfreyClient(winfrey.WinfreyClient):
    def __init__(self, remote_address, broadcast_address, delay, echo_delay, load_delay):
        self.delay = delay;
        self.echo_delay = echo_delay
        self.load_delay = load_delay
        super().__init__(remote_address, broadcast_address)

    def subscribe( self ):
        reply = self.endpoint.send( json.dumps({"uuid": 0, "name": "subscribe", "args": []}), preprocess=self._preprocess_indiv )
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
            time.sleep(self.load_delay)
            self.fullyLoaded = True
            while self.updateQueue: 
                self.queueLock.acquire()
                procedure = self.updateQueue.pop(0)
                self._handle([procedure])
                self.queueLock.release()
        else:
            return None

    def move_my_cursor( self, direction ):
        self.timelock.acquire()
        ltime = time.time() - self.offset
        self.timelock.release()
        time.sleep(self.delay)
        reply = self.endpoint.send( json.dumps({"uuid": str(self.my_cursor), "name": "move_cursor", "args": [str(self.my_cursor), str(direction)], "time": str(ltime)}))

    def insert_my_char(self, char):
        self.timelock.acquire()
        ltime = time.time() - self.offset
        self.timelock.release()
        time.sleep(self.delay)
        reply = self.endpoint.send( json.dumps({"uuid": str(self.my_cursor), "name": "insert_char", "args": [str(self.my_cursor), str(char)], "time": str(ltime)}))

    def echo( self ):
        i = 0
        message = []
        while i < 5:
            trueTime = time.time() - self.offset
            message.append(str(trueTime))
            time.sleep(.01)
            i = i + 1
        if not self.stopped:
            time.sleep(self.echo_delay)
            reply = self.endpoint.send( json.dumps({"uuid": str(self.my_cursor),
                                                    "name": "echo_response",
                                                    "args": message}))




if __name__ == "__main__":
    winfrey = SlowWinfreyClient( "tcp://127.0.0.1:5000", "tcp://127.0.0.1:5001", float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]))
