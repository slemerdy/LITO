from __future__ import with_statement
import sys
from Logger import mylog
import os
import platform

class Luart:
    def __init__(self):
        mylog("Luart init")
        if platform.system() == "Windows":
            cmd = os.path.join(os.path.dirname(__file__), "loser", "loser.exe")
            mylog(cmd)
            if os.path.exists(cmd) == True:
                os.startfile(cmd)
