from imagepypelines.core.util import BaseCommThread, TCPServer, EventQueue
from functools import partial
from json import loads, dumps
from struct import pack, unpack
from dataclasses import dataclass
from typing import Tuple
import select
import threading

@dataclass
class Connection:
        addr: Tuple[str, int]
        id: str = "Unidentified"

# __ Chatroom Object _________________________________________________________
class Chatroom(BaseCommThread):

    def __init__(self, host, port, socketio):
        super().__init__()
        self.host = host
        self.port = port
        self.dashboard = socketio
        self.events = EventQueue()  # Class that queues events
        self.sessions = {} # List of all available tcp sessions (including host)
        self.msg_buff = {}

    def disconnect_client(self, c):
        print(f"Yeeting Pipe {self.sessions[c]}")
        del self.msg_buff[self.sessions[c].id]
        c.close()
        del self.sessions[c]

    def disconnect_all(self):
        clients = [c for c in self.sessions if self.sessions[c] is not None]
        map(partial(Chatroom.disconnect_client, self.sessions), clients)
        for s in self.sessions.keys():  # Kill the Socket Server last
            s.close()

    @staticmethod
    def recvall(c, length):
        '''Convenience function to read large amounts of data (>4096 bytes)'''
        data = b''
        while len(data) < length:
            remaining = length - len(data)
            data += c.recv(min(remaining, 4096))
        return data

    @staticmethod
    def write(c, msg):
        msg_b = msg.encode()
        length = pack('>Q', len(msg_b))
        c.sendall(length) # send length of the message as 64bit integer
        c.sendall(msg_b) # send the message itself

    def read(self, c):
        line = c.recv(8) # 8 bytes for 64bit integer
        if line == b'': # Case for a disconnecting Client socket
            return None
        length = unpack('>Q', line)[0]
        return self.recvall(c, length).decode().rstrip()

    def connect(self, c):
        c, a = c.accept()
        print(f"Connecting Pipe {a}")
        self.sessions[c] = Connection(a)

    def push(self, msg):
        ''' Function to be used outside of the Chatroom class '''
        self.events.add_task(msg)

    def parse_session_msg(self, c, msg):
        _msg = loads(msg)
        print('\n***************************************\n')
        try:
            if _msg['type'] == 'graph':
                id = _msg['uuid']
                self.sessions[c].id = id
                self.msg_buff[id] = []
            elif _msg['type'] == 'status':
                pass
            elif _msg['type'] == 'reset':
                pass
            elif _msg['type'] == 'block_error':
                pass
            elif _msg['type'] == 'delete':
                pass
            else:
                pass
        except:
            print(f"Malformed message: {_msg}")

        return msg

    def parse_dashboard_msgs(self, msg_list):
        for msg in msg_list:
            print(msg)
            _msg = loads(msg)
            id = _msg['uuid']
            try:
                self.msg_buff[id].append(msg)
            except KeyError:
                # TODO: Emit error message to client sender; Invalid Pipe ID
                pass

    def run(self):
        t = threading.current_thread()  # Grab current threading context
        # __ Dashboard Event Loop State Info _________________________________
        tcp = TCPServer()
        s = tcp.connect(self.host, self.port) # Grab server object (Chatroom host)
        sock = s.sock
        self.sessions[sock] = None  # Add host to sessions list
        print(self.sessions)
        # __ Dashboard Event Loop Start ______________________________________
        while getattr(t, 'running', True):  # Run until signaled to DIE
            ready2read, ready2write, _ = select.select(self.sessions, self.sessions, [], 0.1)
            for c in ready2read:
                if c is sock:  # If there is a Pipeline requesting a connection
                    self.connect(c)
                    print("Here are our current sessions:  ", self.sessions)
                    continue
                # If we get to this point then a client has sent a message
                msg = self.read(c)
                if msg: # If they sent anything (even a blank return)
                    # Do something to the data (RH: WE WILL REFORMAT TO RETE.JS NODE-LINK HERE)
                    msg = self.parse_session_msg(c, msg)
                    self.dashboard.emit('pipeline-update', msg, broadcast=True)
                else: # If they sent nothing (which for TCP, happens when a client disconnects)
                    self.disconnect_client(c)

            # Now check if any scheduled task is ready to be run
            msgs = self.events.run_scheduled_tasks()  # Runs any scheduled task
            self.parse_dashboard_msgs(msgs)

            # Finally check if there is anything waiting to be sent to anyone
            for c in ready2write:
                # Check if there are messages to be sent to connected clients
                if (c is not sock):
                    id = self.sessions[c].id
                    if (id in self.msg_buff) and self.msg_buff[id]:
                        while self.msg_buff[id]:
                            msg = self.msg_buff[id].pop(0)
                            self.write(c, msg)

        # __ Dashboard Event Loop Cleanup ____________________________________
        self.disconnect_all()
