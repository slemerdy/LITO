import socket
import OSC
import sys, signal
from time import sleep
import threading
import serial
from serial import tools
from serial.tools import list_ports

ser = None
port = 'COM9'
UDPServerSocket = None

def wio_to_ascii(text):

    rtext = ''

    t_o = ['ó','ò','ô','ö']
    t_O = ['Ó','Ò','Ô','Ö']
    t_e = ['é','è','ë','ê']
    t_E = ['É','È','Ë','Ȇ']
    t_A = ['Á','À','Ä','Ȃ']
    t_a = ['á','à','ä','ȃ']
    t_U = ['Ü','Ú','Ù','Û']
    t_u = ['ü','ú','ù','û']
    t_I = ['Í','Ì','Ȋ','Ï']
    t_i = ['í','ì','ȋ','ï']

    for c in text:
        if ord(c) <= 31:
            pass
        elif ord(c) >= 128:
            if c in t_o:
                rtext += 'o'
            elif c in t_O:
                rtext += 'O'
            elif c in t_e:
                rtext += 'e'
            elif c in t_E:
                rtext += 'e'
            elif c in t_a:
                rtext += 'a'
            elif c in t_A:
                rtext += 'A'
            elif c in t_u:
                rtext += 'u'
            elif c in t_U:
                rtext += 'U'
            elif c in t_i:
                rtext += 'i'
            elif c in t_I:
                rtext += 'I'
            elif c in t_O:
                rtext += 'O'
            elif c == 'ç':
                rtext += 'c'
            elif c == 'ñ':
                rtext += 'n'
            else:
                rtext += '.'
        else:
            rtext += c

    return rtext

'''
def wio_send_string(str):
    if len(str) >= 64:
        return

    bytes_test = [2,1]
    ser.write(bytes_test)

    rtext = wio_to_ascii(str)
    new_bstring = rtext.encode()
    ser.write((len(new_bstring)).to_bytes(1, byteorder='little'))
    ser.write(new_bstring)

    bytes_test = [3]
    ser.write(bytes_test)

def wio_send_int(val):
    bytes_test = [2,2,4]
    ser.write(bytes_test)

    ser.write((val).to_bytes(4, byteorder='little'))

    bytes_test = [3]
    ser.write(bytes_test)
'''
wio_start_line = 5
wio_inter_line = 30

wio_start_row = 20
wio_inter_row = 50

NORM_SIZE = 2
SMALL_SIZE = 1

COLOR_YELLOW = 14
COLOR_WHITE = 15
COLOR_CYAN = 11
COLOR_MAGENTA = 13

def get_wio_line(line):
    return  wio_start_line + line * wio_inter_line

def get_wio_row(row):
    return  wio_start_row + row * wio_inter_row

def wio_reset_screen():
    buffer = [1,1,1,0x7f, 0]
    if ser != None:
        ser.write(buffer)

def wio_send_full_string(row, line, fsize, color, text):
    buffer = [row, line, fsize, color]
    rtext = wio_to_ascii(text)
    new_bstring = rtext.encode()
    new_bstring = new_bstring[:25]
    for c in new_bstring:
        buffer.append(c)
#    i = len(buffer)
#    t = 25 - i
#    for i in range(t):
#        buffer.append(32)
    buffer.append(0)
    if ser != None:
        ser.write(buffer)


def info_cb(msg, source):
    if not hasattr(info_cb, "lens"):
        info_cb.lens = 25
    if len(msg) == 3 and ser != None and type(msg[2]) == str:
        text = msg[2]
        bak_len = len(text)
        if len(text) < info_cb.lens:
            spaces = info_cb.lens - len(text)
            info_cb.lens = len(text)
            for i in range(spaces):
                text += ' '
        info_cb.lens = bak_len
        wioline = get_wio_line(0)
        wio_send_full_string(wio_start_row, wioline, NORM_SIZE, COLOR_WHITE, text)

def track_name_cb(msg, source):
    if not hasattr(track_name_cb, "lens"):
        track_name_cb.lens = 25

    if len(msg) == 3 and ser != None and type(msg[2]) == str:
        text = msg[2]
        bak_len = len(text)
        if len(text) < track_name_cb.lens:
            spaces = track_name_cb.lens - len(text)
            track_name_cb.lens = len(text)
            for i in range(spaces):
                text += ' '
        track_name_cb.lens = bak_len
        wioline = get_wio_line(1)
        wio_send_full_string(wio_start_row, wioline, NORM_SIZE, COLOR_MAGENTA, text)

def device_name_cb(msg, source):
    if not hasattr(device_name_cb, "lens"):
        device_name_cb.lens = 25

    if len(msg) == 3 and ser != None and type(msg[2]) == str:
        text = msg[2]
        bak_len = len(text)
        if len(text) < device_name_cb.lens:
            spaces = device_name_cb.lens - len(text)
            device_name_cb.lens = len(text)
            for i in range(spaces):
                text += ' '
        device_name_cb.lens = bak_len
        wioline = get_wio_line(2)
        wio_send_full_string(wio_start_row, wioline, NORM_SIZE, COLOR_WHITE, text)

def page_cb(msg, source):
    if not hasattr(page_cb, "lens"):
        page_cb.lens = 25
    if len(msg) == 3 and ser != None and type(msg[2]) == str:
        text = msg[2]
        bak_len = len(text)
        if len(text) < page_cb.lens:
            spaces = page_cb.lens - len(text)
            page_cb.lens = len(text)
            for i in range(spaces):
                text += ' '
        page_cb.lens = bak_len
        wioline = get_wio_line(2)
        wio_send_full_string(wio_start_row  + 180, wioline, NORM_SIZE, COLOR_WHITE, text)

def param_name_cb(msg, source):
    if not hasattr(param_name_cb, "lens"):
        param_name_cb.lens = 25

    if len(msg) == 3 and ser != None and type(msg[2]) == str:
        text = msg[2]
        bak_len = len(text)
        if len(text) < param_name_cb.lens:
            spaces = param_name_cb.lens - len(text)
            param_name_cb.lens = len(text)
            for i in range(spaces):
                text += ' '
        param_name_cb.lens = bak_len
        wioline = get_wio_line(3)
        wio_send_full_string(wio_start_row, wioline, NORM_SIZE, COLOR_CYAN, text)


def param_val_cb(msg, source):

    if not hasattr(param_val_cb, "lens"):
        param_val_cb.lens = 25

    if len(msg) == 3 and ser != None and type(msg[2]) == str:
        text = msg[2]
        bak_len = len(text)
        if len(text) < param_val_cb.lens:
            spaces = param_val_cb.lens - len(text)
            param_val_cb.lens = len(text)
            for i in range(spaces):
                text += ' '
        param_val_cb.lens = bak_len
        wioline = get_wio_line(3)
        wio_send_full_string(wio_start_row + 180, wioline, NORM_SIZE, COLOR_CYAN, text)

def device_count_cb(msg, source):
    if not hasattr(device_count_cb, "lens"):
        device_count_cb.lens = 25

    if len(msg) == 3 and ser != None and type(msg[2]) == str:
        text = msg[2]
        bak_len = len(text)
        if len(text) < device_count_cb.lens:
            spaces = device_count_cb.lens - len(text)
            device_count_cb.lens = len(text)
            for i in range(spaces):
                text += ' '
        device_count_cb.lens = bak_len
        wioline = get_wio_line(1)
        wio_send_full_string(wio_start_row + 180, wioline, NORM_SIZE, COLOR_MAGENTA, text)

def param_name2_cb(msg, source):
    if not hasattr(param_name2_cb, "state"):
        param_name2_cb.state = 0

    if not hasattr(param_name2_cb, "labels"):
        param_name2_cb.labels = []
        param_name2_cb.labels = [[] for x in range(8)]
        for i in range(8):
            param_name2_cb.labels[i] = ""

    if len(msg) == 4:
        row = msg[2] - 1
        param_name2_cb.labels[row] = msg[3]
        if row == 0:
            param_name2_cb.state = 1
        elif row == 7:
            param_name2_cb.state = 2

        if param_name2_cb.state == 2:

            param_name2_cb.state == 0
            wioline = get_wio_line(5)

            for i in range(4):
                text = param_name2_cb.labels[i]
                if len(text) < 9:
                    spaces = 9 - len(text)
                    for s in range(spaces):
                        text += ' '

                wio_send_full_string(wio_start_row + 70*i, wioline, SMALL_SIZE, COLOR_YELLOW, text)

            for i in range(4,8):
                text = param_name2_cb.labels[i]
                if len(text) < 9:
                    spaces = 9 - len(text)
                    for s in range(spaces):
                        text += ' '

                wio_send_full_string(wio_start_row + 70*(i-4), wioline+15, SMALL_SIZE, COLOR_YELLOW, text)

def shutdown_cb(msg, source):
    signal.raise_signal(signal.SIGINT)


def open_serial():
    baud = 115200
    try:
        # open a serial connection using the variables above
        ser = serial.Serial(port=port, baudrate=baud)
        ser.timeout = 1  # set the read time out to 1 second
        sleep(0.1)
        return ser
    except:
        return None


port = ""
ports = serial.tools.list_ports.comports(True)
for portinfo in ports:
    if portinfo.vid == 10374 and  portinfo.pid == 32813:
        port = portinfo.name
        print("found port:", port)
        break

if port == "" and len(sys.argv) == 2:
    port = sys.argv[1]

print("opening port:", port)
ser = open_serial()
if ser == None:
    print("No serial device")
    sys.exit(0)

print("serial device opened")
wio_reset_screen()

# OSC
callbackManager = OSC.CallbackManager()
callbackManager.add('/wio/track_name', track_name_cb)
callbackManager.add('/wio/device_name', device_name_cb)
callbackManager.add('/wio/page', page_cb)
callbackManager.add('/wio/param_name', param_name_cb)
callbackManager.add('/wio/param_name2', param_name2_cb)
callbackManager.add('/wio/param_val', param_val_cb)
callbackManager.add('/wio/info', info_cb)
callbackManager.add('/wio/device_count', device_count_cb)
callbackManager.add('/wio/shutdown', shutdown_cb)



# UDP
localIP     = "127.0.0.1"
localPort   = 9008
bufferSize  = 1024

try:
    # Create a datagram socket
    UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
except:
    print("cannot open socket")
    sys.exit(0)

if UDPServerSocket != None:
    try:
        # Bind to address and ip
        UDPServerSocket.bind((localIP, localPort))
    except:
        print("cannot bind")
        sys.exit(0)

print("UDP server up and listening")

def thread_function():

    while(True):
        try:
            # Listen for incoming datagrams
            data, addr = UDPServerSocket.recvfrom(65536)
            callbackManager.handle(data, addr, False)
        except:
            break

def signal_handler(signal, frame):
    if UDPServerSocket != None:
        UDPServerSocket.close()
    wio_reset_screen()
    if ser != None:
        ser.close()

    print("\nprogram exiting gracefully")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


x = threading.Thread(target=thread_function)
x.start()

while(True):
    sleep(1)

