import sys
import time
import inspect
from inspect import currentframe
import ntpath
import traceback

try:
    import socket
except:
    print "No Sockets"
    
class Logger:
    """
    Simple logger.
    Tries to use a socket which connects to localhost port 4444 by default.
    If that fails then it logs to a file
    """
    def __init__(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except:
            print "Couldn't create socket"
            self.socket = None
            
        self.connected = 0
        
        if self.socket:
            try:
                self.socket.connect(("localhost", 4444))
                self.connected = 1
                self.stderr = sys.stderr
                sys.stderr = self
            except:
                print "Couldn't connect socket"

        self.buf = ""

    def log(self,msg):
        if self.connected:
            self.send(msg + '\n')
        else:
            print(msg)
        
    def send(self,msg):
        if self.connected:
            self.socket.send(msg)
    
    def close(self):
        if self.connected:
            self.socket.send("Closing..")
            self.socket.close()
            
    def write(self, msg):
        self.stderr.write(msg)
        self.buf = self.buf + msg
        lines = self.buf.split("\n", 2)
        if len(lines) == 2:
            self.send("STDERR: " + lines[0] + "\n")
            self.buf = lines[1]

logger = Logger()

def log(*args):
    text = ''
    for arg in args:
        if text != '':
            text = text + ' '
        text = text + str(arg)
    if logger != None:
        logger.log(text)

def mystack():
    traceback.print_stack()

def mylog(*msgs):
    li = currentframe().f_back.f_lineno
    text = ""
    for msg in msgs:
        text = text + " " + str(msg)
    myslog(text, li)

def myslog(message, li = -1):
    if li == -1:
        li = currentframe().f_back.f_lineno
    sys.stderr.write(str(li) + ":" + message.encode("utf-8"))

def myelog(message):

    callerframerecord = inspect.stack()[1]
    frame = callerframerecord[0]
    info = inspect.getframeinfo(frame)
    sys.stderr.write("-------")
    sys.stderr.write(ntpath.basename(info.filename))
    sys.stderr.write(info.function)
    sys.stderr.write(str(info.lineno)) #sys.stderr.write(str(frame.f_lineno))
    sys.stderr.write(message.encode("utf-8"))
    sys.stderr.write("-------")
