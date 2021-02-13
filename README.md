LITO
=======
MIDI and OSC remote script for Ableton Live 10 based on LiveOSC. See Below for information about LiveOSC. Thanks to the LiveOSC devs.
A Seeed WIO terminal can be used for displaying Live infos.

# Installation
https://help.ableton.com/hc/en-us/articles/209072009-Installing-third-party-remote-scripts
Set up the remote script and the MIDI controller accordingly in Live Setup.

There are 5 modes:
- UTIL
- LAD
- MORPH
- EUCLIDEAN SEQ (EUC)
- LOOPER (LOOP)

The 5 modes are available when using a tablet.
When using a phone or with no OSC device, then only UTIL EUC and LOOPER are available.
A phone is needed to use the euclidean sequencer.

# Configuration of TouchOSC
install TouchOSC on your remote device. Use
\touchosc\LITO.touchosc for tablets
\touchosc\LITOphone.touchosc for phones
Refer to TouchOSC documentation for installation and opening of touchosc files.
Your device shall be configured as is in Connections:OSC
- Enabled: Yes
- Host: your computer local Ip address 10.0.0.5, 192.168.9.17
- Port (Outgoing): 9009
- Port (Ingoing): 9008

Once done, click on SYNC button on the first tab. This last operation shall be done at each startup of Live or if the connection between TouchOSC and the computer has been lost.


# Configuration of the MIDI

edit the file const.py and set:
- midi_relative (False/True). False continuous CC messages are absolute else continous CC messages are relative
- midi_relative_mode. If midi_relative is True, define relative_mode (1,2,3,4)
- midi_relative_acceleration. experimental. can vary between 1.0 and 5.0. Higher value shall give better reaction of controller for continous message with midi_relative is True

messages with "ENCODER" in their name are considered as continous (MIDI_LAD_ENCODER3, MIDI_LOOP_START_QBEAT_ENCODER, MIDI_EUC_ENCODER3) . The configuration midi_relative is applicable to these controller.
MIDI_LOOP_MORPH_SLIDER and MIDI_LAD_MORPH_SLIDER are absolute CC message based (Expected value between 0 and 127).
All the other controls are buttons. The expected behaviour is a push button (no toggle between low and high state). The button is sampled on state low ( CC message value is zero)


# relative_mode
mode 1 is 2’s Complement from 64 / Relative (Binary Offset)
turn right gives 065 - 127
turn left gives 063 - 000
equivalent to mode R2 on BCR2000

mode 2 is 2’s Complement from 0 / Relative (2’s Complement)
turn right gives 001 - 64
turn left gives 127 - 065
equivalent to mode R1 on BCR2000

mode 3 is Sign Magnitude / Relative (Signed Bit) (NOT TESTED !)
turn right gives 065 - 127
turn left gives 001 - 063

mode 4 is Sign Magnitude / Relative (Signed Bit 2)
turn right gives 001 - 063
turn left gives 065 - 127
equivalent to mode R3 on BCR2000

# CC messages

MIDI_MODE allows to switch the different mode:
if CC is set to -1, then this message is not handled by the remote script.
modes are exclusive. Thus, the same CC can be used for the different modes. Note: UTIL, LAD and MORPH are sharing the same MIDI implementation.


the messages:
MIDI_UTIL_TAB_INDICATOR
MIDI_LAD_TAB_INDICATOR
MIDI_MORPH_TAB_INDICATOR
MIDI_EUC_TAB_INDICATOR
MIDI_LOOP_TAB_INDICATOR
are optional and only to give a feedback


LiveOSC
=======

MIDI remote script for communication with Ableton Live over OSC

This is the recommended version of LiveOSC to use with node-liveosc.  This version has been modified to use ports 9005 and 9006 and has a few new OSC callbacks and bug fixes.  I am not the original author of this code, the original version can be found here:

http://livecontrol.q3f.org/ableton-liveapi/liveosc/

# Installation

Please see http://livecontrol.q3f.org/ableton-liveapi/liveosc/ for installation instructions.


