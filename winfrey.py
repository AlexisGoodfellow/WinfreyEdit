import sys
import uuid
import json
import logging
from backend import editor_state as WinfreyEditor
import client as clientpoint
import server as serverpoint

def serialize( uid, name, *args ):
    message = {
            "uid": uid,
            "name": name,
            "args": [str(arg) for arg in args]
    }

    return json.dumps( message )

def deserialize( message ):

    nobject = json.loads( message )
    if type(nobject) != dict:
        raise DeserializationError("Received malformed data: {}".format(msg))
    print( nobject )
    return nobject


class WinfreyServer( WinfreyEditor ):
    def __init__( self, interact_address, broadcast_address, filename ):
        self.logger = logging.getLogger("main")
        self.endpoint = serverpoint.Server( interact_address, broadcast_address, self.logger )
        super().__init__( filename )                 

        self.endpoint.startBackground( preprocess=self._preprocess, handler=self._handle, postprocess=self._postprocess, pollTimeout = 2000 )

    def _subscribe( self ):
        new_uuid = uuid.uuid4().int
        print( "Created new user with UUID " + str(new_uuid) )
        self.init_gui()
        self.create_cursor(new_uuid)
        # self.broadcast( serialize( "create_cursor", new_uuid ) )

        return {"status": "subscribed", "other": {"uuid": new_uuid, "file": self.rows }}

    def no_such_function(*args):
        return {"status": "fail", "other": "No RPC matches this contract"}

    def _handle( self, procedure ):
        rpc_funcs = {
                "subscribe": self._subscribe
        }

        f = procedure["name"]

        function = rpc_funcs.get( f, self.no_such_function )

        reply = function( *(procedure["args"]) )

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

    def subscribe( self ):
        reply = self.endpoint.send( serialize( 0, "subscribe" ), preprocess=self._preprocess )
        if reply["status"] == "subscribed":
            self.my_cursor = reply["other"]["uuid"]
            self.rows = [s.replace('\n', '') for s in reply["other"]["file"]]
            self.numrows = len( self.rows )
            self.init_gui()
            self.rows = [s + '\n' for s in self.rows]
            self.create_cursor( self.my_cursor )
            self.G.launch()
        else:
            return None

    def _preprocess( self, message ):
        return json.loads( message )

if __name__ == "__main__":
    if sys.argv[1] == "-s":
        winfrey = WinfreyServer( "tcp://*:{}".format(sys.argv[2]), "tcp://*:{}".format( sys.argv[3] ), "garbage.txt" )
    else:
        winfrey = WinfreyClient( "tcp://%s:%s" % (sys.argv[2], sys.argv[3]), "tcp://%s:%s" % (sys.argv[2], sys.argv[4]))
