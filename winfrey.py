import sys
import uuid
import json
import logging
from backend import editor_state as WinfreyEditor
import client as clientpoint
import server as serverpoint

def serialize( uid, name, *args ):
    message = {
            "uid": uid
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

                

        self.endpoint.startBackground( preprocess=self._preprocess, handler=self._handle, postprocess=self._postprocess, pollTimeout = 2000 )

    def subscribe():


    def fail(*args):
        return ("fail", "Unknown procedure")

    def _handle( self, procedure ):
        rpc_funcs = {
                "print": self._print_a_thing
        }

        f = procedure["name"]

        function = rpc_funcs.get( f, self.fail )

        try:
            (a, b) = function( *procedure["args"] )
        except:
            print( "Something went wrong!" )
            return (None, None)

        return (a, b)

    def _preprocess( self, message ):
        return deserialize( message )

    def _postprocess( self, message ):
        return json.dumps( message )


class WinfreyClient( WinfreyEditor ):
    def __init__( self, remote_address, broadcast_address ):
        self.logger = logging.getLogger("main")
        self.endpoint = clientpoint.Client( remote_address, broadcast_address, self.logger )

        super().__init__()

        self.endpoint.send( serialize( "print", "Hello RPC world!" ) )

if __name__ == "__main__":
    if sys.argv[1] == "-s":
        winfrey = WinfreyServer( "tcp://*:{}".format(sys.argv[2]), "tcp://*:{}".format( sys.argv[3] ), "abc.txt" )
    else:
        winfrey = WinfreyClient( "tcp://%s:%s" % (sys.argv[2], sys.argv[3]), "tcp://%s:%s" % (sys.argv[2], sys.argv[4]))
