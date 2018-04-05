import sys
import time
import uuid
import json
import logging
import threading
import argparse
from backend import editor_state as WinfreyEditor
import client as clientpoint
import server as serverpoint

def serialize( uid, name, *args ):
    message = {
            "uuid": uid,
            "name": name,
            "args": [str(arg) for arg in args]
    }

    return json.dumps( message )

def deserialize( message ):

    nobject = json.loads( message )
    if type(nobject) != dict:
        raise DeserializationError("Received malformed data: {}".format(msg))
    return nobject


class WinfreyServer( WinfreyEditor ):
    def __init__( self, interact_address, broadcast_address, filename ):
        self.logger = logging.getLogger("main")
        self.endpoint = serverpoint.Server( interact_address, broadcast_address, self.logger )
        super().__init__( filename )                 

        save_thread = threading.Thread( target=self.save )

        self.endpoint.startBackground( preprocess=self._preprocess, handler=self._handle, postprocess=self._postprocess, pollTimeout = 2000 )
        save_thread.start()

    def save( self ):
        while True:
            time.sleep(30)
            print( "Saving...." )
            self.write( "temp.txt" )

    def subscribe( self ):
        new_uuid = uuid.uuid4().int
        print( "Created new user with UUID " + str(new_uuid) )
        self.create_cursor(str(new_uuid))
        self.endpoint.broadcast( serialize( new_uuid, "create_cursor", new_uuid ) )

        return {"status": "subscribed", "other": {"uuid": new_uuid, "file": self.rows, "cursors": self.cursors }}

    def unsubscribe( self, uuid ):
        print( "User " + uuid + " left." )
        self.remove_cursor( uuid );
        self.endpoint.broadcast( serialize( uuid, "remove_cursor", uuid ) )

    def create_cursor( self, cid ):
        super().create_cursor( cid )
        return {"status": "ok", "other": ""}

    def remove_cursor( self, cid ):
        super().remove_cursor( cid )
        return {"status": "ok", "other": ""}

    def move_cursor( self, cid, direction ):
        super().move_cursor( cid, direction )
        return {"status": "ok", "other": ""}

    def insert_char( self, cid, char ):
        super().insert_char( cid, char )
        return {"status": "ok", "other": ""}

    def no_such_function(*args):
        return {"status": "fail", "other": "No RPC matches this contract"}

    def _handle( self, procedure ):
        rpc_funcs = {
                "subscribe": self.subscribe,
                "unsubscribe": self.unsubscribe,
                "move_cursor": self.move_cursor,
                "insert_char": self.insert_char
        }

        f = procedure["name"]

        function = rpc_funcs.get( f, self.no_such_function )

        reply = function( *procedure["args"] )
        
        if f == "move_cursor" or f == "insert_char":
           self.endpoint.broadcast( serialize( procedure["uuid"], procedure["name"], *procedure["args"] ) )

        return reply

    def _preprocess( self, message ):
        return deserialize( message )

    def _postprocess( self, message ):
        return json.dumps( message )


class WinfreyClient( WinfreyEditor ):
    def __init__( self, remote_address, broadcast_address ):
        self.logger = logging.getLogger("main")
        self.endpoint = clientpoint.Client( remote_address, broadcast_address, self.logger )
   
        super().__init__()

        self.subscribe()
        self.endpoint.startBackground( self._handle, preprocess=self._preprocess )
        self.G.launch()

    def move_my_cursor( self, direction ):
        super().move_my_cursor( direction )
        reply = self.endpoint.send( serialize( self.my_cursor, "move_cursor", self.my_cursor, direction ))

    def insert_my_char( self, char ):
        super().insert_my_char( char )
        reply = self.endpoint.send( serialize( self.my_cursor, "insert_char", self.my_cursor, char ))

    def subscribe( self ):
        reply = self.endpoint.send( serialize( 0, "subscribe" ), preprocess=self._preprocess_indiv )
        if reply["status"] == "subscribed":
            self.my_cursor = str(reply["other"]["uuid"])
            self.rows = reply["other"]["file"]
            self.numrows = len( self.rows )
            for i in range( 0, len(self.rows) ):
                self.G.add_line( i, self.rows[i][:-1], [] );
            for cid in reply["other"]["cursors"]:
                cursor = reply["other"]["cursors"][cid]
                self.create_cursor( cid, cursor["cx"], cursor["cy"] )
        else:
            return None

    def unsubscribe( self ):
        reply = self.endpoint.send( serialize( self.my_cursor, "unsubscribe", self.my_cursor ), preprocess=self._preprocess_indiv )
        
        self.endpoint.stop()

    def interrupt( self ):
        self.unsubscribe();

    def _handle( self, procedure ):
        rpc_funcs = {
                "create_cursor": self.create_cursor,
                "remove_cursor": self.remove_cursor,
                "move_cursor": self.move_cursor,
                "insert_char": self.insert_char,
        }

        if procedure["uuid"] == self.my_cursor:
            return

        f = procedure["name"]
        function = rpc_funcs.get( f, None )
        if function:
            function( *procedure["args"] )

        return
    
    def _preprocess( self, message ):
        return deserialize( message )

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