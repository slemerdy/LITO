# revsion
# $Rev: 1454 $
# // revision_for_SVN_0_3

"""
# Copyright (C) 2007 Nathan Ramella (nar@remix.net)
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# For questions regarding this module contact
# Nathan Ramella <nar@remix.net> or visit http://www.remix.net

This script is based off the Ableton Live supplied MIDI Remote Scripts, customised
for OSC request delivery and response. This script can be run without any extra
Python libraries out of the box. 

This is the second file that is loaded, by way of being instantiated through
__init__.py

"""



from __future__ import with_statement
from _Framework.ControlSurface import ControlSurface
import Live
import RemixNet
import OSC
import LiveUtils
import sys
from Logger import log
from Logger import mylog
from Logger import myslog
from Logger import myelog
from Logger import mystack
import random
from time import sleep
from math import floor
from datetime import datetime
import os
import const
import uart

lad_hl_color = "orange"
lad_hl_color2 = "orange"

EUC_PACE_CNT = 16
EUC_PACE_HALF_CNT = 8

GROUP_CNT = 2
PRESET_CNT = 6
UTIL_MAX_PATTERN = 96
LOOP_CNT = 8
cur_meas = 0

UTIL_TAB = 1
LAD_TAB = 2
MORPH_TAB = 4
EUC_TAB = 8
LOOP_TAB = 16

ACCELERATION_ON_LOOPER = False
ACCELERATION_ON_EUC = False
do_param_log = False

class LiveOSC:
    __module__ = __name__
    __doc__ = "Main class that establishes the LiveOSC Component"

    sys.setdefaultencoding( "utf-8" )
    prlisten = {}
    plisten = {}
    dnlisten = {}
    dlisten = {}
    clisten = {}
    slisten = {}
    pplisten = {}
    cnlisten = {}
    cclisten = {}
    ccnlisten = {}
    wlisten = {}
    llisten = {}
    cslisten = {}
    ccslisten = {}

    clip_start_marker_listen = {}
    clip_end_marker_listen = {}
    clip_loop_start_listen = {}
    clip_loop_end_listen = {}
    clip_end_time_listen = {}
    clip_coarse_listen = {}

    # sclisten = {}
    # snlisten = {}
    # stlisten = {}
    
    _send_pos = {}
    
    mlisten = { "solo": {}, "mute": {}, "arm": {}, "panning": {}, "volume": {}, "sends": {}, "name": {}, "om": {}, "color": {}, "collapsed": {} }
    rlisten = { "solo": {}, "mute": {}, "panning": {}, "volume": {}, "sends": {}, "name": {}, "color": {} }
    masterlisten = { "panning": {}, "volume": {}, "crossfader": {} }
    scenelisten = { "name": {} }

# ########################################################################################################

    FADER_CNT = 8
    debug = 0
    lito_tab = UTIL_TAB
    new_song = 0
    tid = -1
    cid = -1
    loop_audio_clips_pitches = {}
    lad_config_changed = False


    def __init__(self, c_instance):
        self._LiveOSC__c_instance = c_instance

        mylog("----------------------------------------") # PERMANENT
        mylog("Starting LITO", datetime.now()) # PERMANENT

        self.dev_pref_read_file()

        self.basicAPI = 0       
        self.oscEndpoint = RemixNet.OSCEndpoint()
        if self.oscEndpoint.get_wio_mode() == True:
            uart.Luart()
        self.new_song = 1
        self.use_midi_cache = True
        self.cache_midi = {}

        if self.song().tracks_has_listener(self.refresh_state) != 1:
            self.song().add_tracks_listener(self.refresh_state)

        self.add_scenes_listener()

        return


######################################################################
# Standard Ableton Methods

    def connect_script_instances(self, instanciated_scripts):
        """
        Called by the Application as soon as all scripts are initialized.
        You can connect yourself to other running scripts here, as we do it
        connect the extension modules
        """
        return

    def is_extension(self):
        return False

    def request_rebuild_midi_map(self):
        """
        To be called from any components, as soon as their internal state changed in a 
        way, that we do need to remap the mappings that are processed directly by the 
        Live engine.
        Dont assume that the request will immediately result in a call to
        your build_midi_map function. For performance reasons this is only
        called once per GUI frame.
        """
        self._LiveOSC__c_instance.request_rebuild_midi_map()
        return
    
    def update_display(self):
        """
        This function is run every 100ms, so we use it to initiate our Song.current_song_time
        listener to allow us to process incoming OSC commands as quickly as possible under
        the current listener scheme.
        """
        ######################################################
        # START OSC LISTENER SETUP

              
        if self.basicAPI == 0:
            # By default we have set basicAPI to 0 so that we can assign it after
            # initialization. We try to get the current song and if we can we'll
            # connect our basicAPI callbacks to the listener allowing us to
            # respond to incoming OSC every 60ms.
            #
            # Since this method is called every 100ms regardless of the song time
            # changing, we use both methods for processing incoming UDP requests
            # so that from a resting state you can initiate play/clip triggering.

            try:
                doc = self.song()
            except:
                log('could not get song handle')
                return
            try:
                self.basicAPI = self.init_cb()
                # Commented for stability
                self.time = 0
                doc.add_current_song_time_listener(self.current_song_time_changed)
            except:
                log('setting up basicAPI failed');
                return

            # If our OSC server is listening, try processing incoming requests.
            # Any 'play' initiation will trigger the current_song_time listener
            # and bump updates from 100ms to 60ms.

        if self.oscEndpoint:
            if self.basicAPI != 0:
                try:
                    self.oscEndpoint.processIncomingUDP()
                except:
                    log('error processing incoming UDP packets:', sys.exc_info());

#        # END OSC LISTENER SETUP
#        ######################################################

    def current_song_time_changed(self):

        time = self.song().current_song_time
        if int(time) != self.time:
            self.time = int(time)
            if self.time % 4 == 0:
                current_track = self.song().view.selected_track
                if current_track == None:
                    return

                tid = self.get_working_midi_track()
                if tid == -1:
                    return

                cs = self.song().view.highlighted_clip_slot
                if cs == None:
                    return

                if cs.has_clip == False:
                    return

                if cs.clip.is_midi_clip == False:
                    return

                if cs.clip.is_playing == False:
                    return

                self.oscEndpoint.send("/euc/euc_status", str((int(cs.clip.playing_position)/4)+1))

        return

    def send_midi_ex(self, midi_event_bytes, lito_tab):

        if len(midi_event_bytes) == 3:
            if midi_event_bytes[1] == -1:
                return

        if (lito_tab & self.lito_tab) == self.lito_tab:
            new_midi_event_bytes = list(midi_event_bytes)
            new_midi_event_bytes[0] = new_midi_event_bytes[0] | const.midi_channel
            midi_event_bytes = tuple(new_midi_event_bytes)
            self.send_midi(midi_event_bytes)


    def send_midi(self, midi_event_bytes):

        """
        Use this function to send MIDI events through Live to the _real_ MIDI devices 
        that this script is assigned to.
        """

        send_it = True
        if self.use_midi_cache == True:
            if len(midi_event_bytes) == 3:
                if (midi_event_bytes[0] & 0xB0) == 0xB0:
                    midi_cc = str(midi_event_bytes[1])
                    midi_val = midi_event_bytes[2]
                    if (midi_cc in self.cache_midi) == False:
                        self.cache_midi[midi_cc] = midi_val
                    else:
                        prev = self.cache_midi[midi_cc]
                        if prev == midi_val:
                            send_it = False
                        else:
                            self.cache_midi[midi_cc] = midi_val

        if send_it == True:
            self.__c_instance.send_midi(midi_event_bytes)


    def receive_midi(self, midi_bytes):

        if self.use_midi_cache == True:
            if len(midi_bytes) == 3:
                if (midi_bytes[0] & 0xB0) == 0xB0:
                    midi_cc = str(midi_bytes[1])
                    midi_val = midi_bytes[2]
                    self.cache_midi[midi_cc] = midi_val

        cc = midi_bytes[1]

        if (cc == const.MIDI_MODE) and midi_bytes[2] == 0:
            if self.oscEndpoint.get_phone_osc() == True:
                if self.lito_tab == UTIL_TAB:
                    self.touch_change_tab(EUC_TAB)
                elif self.lito_tab == EUC_TAB:
                    self.touch_change_tab(LOOP_TAB)
                else:
                    self.touch_change_tab(UTIL_TAB)
            else:
                if self.lito_tab == UTIL_TAB:
                    self.touch_change_tab(LAD_TAB)
                elif self.lito_tab == LAD_TAB:
                    self.touch_change_tab(MORPH_TAB)
                elif self.lito_tab == MORPH_TAB:
                    self.touch_change_tab(EUC_TAB)
                elif self.lito_tab == EUC_TAB:
                    self.touch_change_tab(LOOP_TAB)
                else:
                    self.touch_change_tab(UTIL_TAB)

        if (cc == const.MIDI_LOAD_CFG) and midi_bytes[2] == 0:
            self.util_reload()

        if (self.lito_tab == LAD_TAB) or (self.lito_tab == UTIL_TAB) or (self.lito_tab == MORPH_TAB):

            if cc in self.lad_midi_encoders: # encoders
                fader = self.lad_midi_encoders.index(cc) + 1
                if self.xtouch_lower_encoder == True:
                    fader = fader + 8
                if const.midi_relative == False:
                    val = self.adaptValue(float(midi_bytes[2]), 0, 127.0, 0, 1.0)
                    self.lad_fader_input(fader, float(val), False)
                else:
                    val_midi = self.midi_get_rel_dec_inc_val(midi_bytes[2])

                    negative_val = False
                    if val_midi < 0:
                        negative_val = True
                    val = self.adaptValue(float(abs(val_midi)), 0, 127.0, 0, const.midi_relative_acceleration)
                    if negative_val == True:
                        val = -val

                    self.lad_fader_input(fader, float(val), True)

            elif cc == const.MIDI_LAD_MORPH_SLIDER: #morph slider
                val = self.adaptValue(float(midi_bytes[2]), 0, 127.0, 0, 1.0)
                address = "/lad/faderm1"
                self.oscEndpoint.send(address, float(val))
                self.lad_faderm_input(1, float(val))

            elif cc in self.lad_midi_presets and midi_bytes[2] == 0: # presets
                idx =  self.lad_midi_presets.index(cc)
                self.lad_menu(idx + 19)

            elif cc in self.lad_midi_buttons and midi_bytes[2] == 0:
                if cc == const.MIDI_LAD_LOWER_FADER:
                    self.xtouch_lower_encoder = not self.xtouch_lower_encoder
                    self.util_update_lower_gui() # midi lower
                    self.lad_update_faders() # midi lower
                else:
                    idx =  self.lad_midi_buttons.index(cc)
                    self.lad_menu(idx+1)

        elif self.lito_tab == EUC_TAB:

            if (cc in (self.euc_midi_cur_note)) and midi_bytes[2] == 0: # cur_note
                idx = self.euc_midi_cur_note.index(cc) + 1
                self.euc_note(idx)

            elif (cc in (self.euc_midi_plays)) and midi_bytes[2] == 0: # play
                idx = self.euc_midi_plays.index(cc)
                thistuple = self.euc_cfg[idx]

                pressed  = 0
                if thistuple[0] == 0:
                    pressed  = 1

                self.euc_set_cfg(idx+1, "play", int(pressed))
                self.euc_fill_clip()
                self.euc_update_gui_play()


            elif cc in self.euc_midi_encoders: # encoders
                encoder = self.euc_midi_encoders.index(cc)

                if encoder == 0:

                    thistuple = self.euc_cfg[self.euc_cur_note-1]

                    if const.midi_relative == False:
                        val = int(self.adaptValue(float(midi_bytes[2]), 0, 127.0, 1, 16.0))
                    else:
                        val = thistuple[1]
                        val_midi = self.midi_get_rel_dec_inc_val(midi_bytes[2], ACCELERATION_ON_EUC)
                        val =  val + val_midi
                        if val > EUC_PACE_CNT:
                            val = EUC_PACE_CNT
                        if val < 1 :
                            val = 1

                    self.euc_set_cfg(self.euc_cur_note, "steps", val)
                    thistuple = self.euc_cfg[self.euc_cur_note-1]
                    val2 = int(self.adaptValue(thistuple[2], 1, EUC_PACE_CNT, 0, 127))
                    self.send_midi_ex((0xB0, const.MIDI_EUC_ENCODER2, val2), EUC_TAB)
                    val3 = int(self.adaptValue(thistuple[3], 0, EUC_PACE_CNT-1, 0, 127))
                    self.send_midi_ex((0xB0, const.MIDI_EUC_ENCODER3, val3), EUC_TAB)

                elif encoder == 1:

                    thistuple = self.euc_cfg[self.euc_cur_note-1]

                    if const.midi_relative == False:
                        val = int(self.adaptValue(float(midi_bytes[2]), 0, 127.0, 1, 16.0))
                    else:
                        val = thistuple[2]
                        val_midi = self.midi_get_rel_dec_inc_val(midi_bytes[2], ACCELERATION_ON_EUC)
                        val =  val + val_midi
                        if val > EUC_PACE_CNT:
                            val = EUC_PACE_CNT
                        if val < 1 :
                            val = 1

                    self.euc_set_cfg(self.euc_cur_note, "pulses", val)
                    thistuple = self.euc_cfg[self.euc_cur_note-1]
                    if val > thistuple[2]:
                        val2 = int(self.adaptValue(thistuple[2], 1, 16, 0, 127))
                        self.send_midi_ex((0xB0, const.MIDI_EUC_ENCODER2, val2), EUC_TAB)

                elif encoder == 2:
                    thistuple = self.euc_cfg[self.euc_cur_note-1]

                    if const.midi_relative == False:
                        val = int(self.adaptValue(float(midi_bytes[2]), 0, 127.0, 1, 16.0)) - 1
                    else:
                        val = thistuple[3]
                        val_midi = self.midi_get_rel_dec_inc_val(midi_bytes[2], ACCELERATION_ON_EUC)
                        val =  val + val_midi
                        if val > (EUC_PACE_CNT-1):
                            val = EUC_PACE_CNT-1
                        if val < 0 :
                            val = 0

                    self.euc_set_cfg(self.euc_cur_note, "shift", val)
                    thistuple = self.euc_cfg[self.euc_cur_note-1]
                    if val-1 > thistuple[3]:
                        val3 = int(self.adaptValue(thistuple[3], 0, 15, 0, 127))
                        self.send_midi_ex((0xB0, const.MIDI_EUC_ENCODER3, val3), EUC_TAB)

                self.euc_update_gui_sps(self.euc_cur_note, False)
                self.euc_fill_clip()

        elif self.lito_tab == LOOP_TAB:

            if cc in (self.loop_midi_encoders):
                idx = self.loop_midi_encoders.index(cc) + 1
                self.loop_midi_set_fly(idx, midi_bytes[2])
            elif cc == const.MIDI_LOOP_PITCH_ENCODER:
                self.loop_midi_set_pitch(midi_bytes[2])
            elif (cc in (self.loop_midi_buttons)) and midi_bytes[2] == 0:
                idx = self.loop_midi_buttons.index(cc) + 1
                if self.loop_register_mode == False:
                    self.loop_midi_set_beat(idx)
                else:
                    self.loop_midi_handle_register_ex(idx)
            elif cc == const.MIDI_LOOP_TOGGLE_PRESET_MODE and midi_bytes[2] == 0:
                self.loop_toggle_mode()
            elif cc == const.MIDI_LOOP_MORPH_SLIDER: #morph slider
                val = int(self.adaptValue(float(midi_bytes[2]), 0, 127.0, 9, 16))
                if val != self.loop_morph_prev_val:
                    self.loop_midi_handle_register(val)
                    self.loop_morph_prev_val = val
            elif cc == const.MIDI_LOOP_RAND and midi_bytes[2] == 0:
                self.loop_midi_rand()
            elif cc == const.MIDI_LOOP_CALL_PITCH and midi_bytes[2] == 0:
                self.loop_midi_recall_pitch()
            elif cc == const.MIDI_LOOP_SET_PITCH and midi_bytes[2] == 0:
                self.loop_midi_set_dft_pitch()

        return

    def can_lock_to_devices(self):
        return False

    def suggest_input_port(self):
        return ''

    def suggest_output_port(self):
        return ''

    def __handle_display_switch_ids(self, switch_id, value):
        pass
    
    
######################################################################
# Useful Methods

    def application(self):
        """returns a reference to the application that we are running in"""
        return Live.Application.get_application()

    def song(self):
        """returns a reference to the Live Song that we do interact with"""
        return self._LiveOSC__c_instance.song()

    def handle(self):
        """returns a handle to the c_interface that is needed when forwarding MIDI events via the MIDI map"""
        return self._LiveOSC__c_instance.handle()
            
    def getslots(self):
        tracks = self.song().tracks

        clipSlots = []
        for track in tracks:
            clipSlots.append(track.clip_slots)
        return clipSlots

        
            
######################################################################
# Used Ableton Methods

    def disconnect(self):


        self.lad_save_param_cfg() # disconnect
        self.lad_export_cfg() # disconnect

#        self.rem_cclipSlot_listeners()
#        self.rem_clipSlot_listeners()
        self.rem_clip_listeners()
        self.rem_mixer_listeners()
        self.rem_scene_listeners()
#        self.rem_tempo_listener()
        self.rem_visible_tracks_listener()
#        self.rem_overdub_listener()
        self.rem_tracks_listener()
        self.rem_device_listeners()
#        self.rem_transport_listener()
#        self.rem_master_track_color_listener()
#        self.rem_scene_name_listeners()
#        self.rem_session_record_listener()
#        self.rem_session_record_status_listener()
#        self.rem_groove_amount_listener()
#        self.rem_metronome_listener()
        
        self.rem_scenes_listener()
        self.song().remove_tracks_listener(self.refresh_state)
        self.wio_send_shutdown()
        self.touch_exit()
        self.oscEndpoint.send('/remix/oscserver/shutdown', 1)
        self.oscEndpoint.shutdown()
        self.new_song = 1

        mylog("LITO Disconnecting") # PERMANENT
        mylog("----------------------------------------") # PERMANENT


            
    def build_midi_map(self, midi_map_handle):

        if self.lad_config_changed == True:
            self.lad_config_changed = False
            scene = self.song().scenes[0]
            name = scene.name
            scene.name = "LITO"
            scene.name = name


        script_handle = self.handle()
        for channel in range(16):
            for cc in range(1,128):
                Live.MidiMap.forward_midi_cc(script_handle, midi_map_handle, channel, cc)

        self.refresh_state()
        return
            

    def refresh_state(self):
        self.update_tracks_list()
        self.lad_update_matrix()

#        self.add_cclipSlot_listeners()
#        self.add_clipSlot_listeners()
        self.add_clip_listeners()
        self.add_mixer_listeners()
        self.add_scene_listeners()
#        self.add_tempo_listener()
        self.add_visible_tracks_listener()
#        self.add_overdub_listener()
        self.add_tracks_listener()
        self.add_device_listeners()
        self.add_transport_listener()
#        self.add_master_track_color_listener()
#        self.add_scene_name_listeners()
#        self.add_session_record_listener()
#        self.add_session_record_status_listener()
#        self.add_groove_amount_listener()
#        self.add_metronome_listener()


        if self.new_song == 1:
            self.touch_init()
            self.euc_set_pitch("dr1", False)
            self.new_song = 0
            self.lad_set_info("")
            self.lad_preset_rec_init_values()
            self.lad_load_param_live_cfg()
            self.lad_export_cfg() # refresh_state (open file)
        else:
            self.lad_mixer_mode = 0
            self.lad_set_mixer_gui() # refresh_state
            self.lad_show_currents() # refresh_state

        self.euc_update_status()
        self.touch_send_midi_info(7, self.oscEndpoint.get_disable_osc())

        return

       

######################################################################
# Add / Remove Listeners   
    def add_scene_listeners(self):
        self.rem_scene_listeners()
    
        if self.song().view.selected_scene_has_listener(self.scene_change) != 1:
            self.song().view.add_selected_scene_listener(self.scene_change)

        if self.song().view.selected_track_has_listener(self.track_change) != 1:
            self.song().view.add_selected_track_listener(self.track_change)

    def rem_scene_listeners(self):
        if self.song().view.selected_scene_has_listener(self.scene_change) == 1:
            self.song().view.remove_selected_scene_listener(self.scene_change)
            
        if self.song().view.selected_track_has_listener(self.track_change) == 1:
            self.song().view.remove_selected_track_listener(self.track_change)

    def track_change(self):
        self.lad_device_page = 0
        self.lad_clear_saved_obj()
        self.lad_show_currents() # track_change
        self.scene_change()
        
    def scene_change(self):
        self.loop_update_gui_buttons()
        self.loop_update_pitch_gui()
        tid, cid = self.get_cur_tid_cid()
        if self.tid != tid or self.cid != cid:
            self.tid = tid
            self.cid = cid
            self.euc_load_clip_cfg(tid, cid)
            self.euc_update_gui_full() # scene change


    def add_tempo_listener(self):
        self.rem_tempo_listener()
    
        if self.song().tempo_has_listener(self.tempo_change) != 1:
            self.song().add_tempo_listener(self.tempo_change)
        
    def rem_tempo_listener(self):
        if self.song().tempo_has_listener(self.tempo_change) == 1:
            self.song().remove_tempo_listener(self.tempo_change)

    def tempo_change(self):
        tempo = LiveUtils.getTempo()

    def add_visible_tracks_listener(self):
        self.rem_visible_tracks_listener()
        if self.song().visible_tracks_has_listener(self.visible_tracks_change) != 1:
            self.song().add_visible_tracks_listener(self.visible_tracks_change)

    def rem_visible_tracks_listener(self):
        if self.song().visible_tracks_has_listener(self.visible_tracks_change) == 1:
            self.song().remove_visible_tracks_listener(self.visible_tracks_change)

    def visible_tracks_change(self):
        self.refresh_state()
        return

    def add_transport_listener(self):
        if self.song().is_playing_has_listener(self.transport_change) != 1:
            self.song().add_is_playing_listener(self.transport_change)
            
    def rem_transport_listener(self):
        if self.song().is_playing_has_listener(self.transport_change) == 1:
            self.song().remove_is_playing_listener(self.transport_change)    
    
    def transport_change(self):
        self.euc_disp_play()
        self.lad_disp_play()
        return
    
    def add_metronome_listener(self):
        self.rem_metronome_listener()

        if self.song().metronome_has_listener(self.metronome_change) != 1:
            self.song().add_metronome_listener(self.metronome_change)

    def rem_metronome_listener(self):
        if self.song().metronome_has_listener(self.metronome_change) == 1:
            self.song().remove_metronome_listener(self.metronome_change)

    def add_groove_amount_listener(self):
        self.rem_groove_amount_listener()

        if self.song().groove_amount_has_listener(self.groove_amount_change) != 1:
            self.song().add_groove_amount_listener(self.groove_amount_change)

    def rem_groove_amount_listener(self):
        if self.song().groove_amount_has_listener(self.groove_amount_change) == 1:
            self.song().remove_groove_amount_listener(self.groove_amount_change)


    def add_session_record_status_listener(self):
        self.rem_session_record_status_listener()

        if self.song().session_record_status_has_listener(self.session_record_status_change) != 1:
            self.song().add_session_record_status_listener(self.session_record_status_change)

    def rem_session_record_status_listener(self):
        if self.song().session_record_status_has_listener(self.session_record_status_change) == 1:
            self.song().remove_session_record_status_listener(self.session_record_status_change)

    def add_session_record_listener(self):
        self.rem_session_record_listener()

        if self.song().session_record_has_listener(self.session_record_change) != 1:
            self.song().add_session_record_listener(self.session_record_change)

    def rem_session_record_listener(self):
        if self.song().session_record_has_listener(self.session_record_change) == 1:
            self.song().remove_session_record_listener(self.session_record_change)

    def add_overdub_listener(self):
        self.rem_overdub_listener()
    
        if self.song().overdub_has_listener(self.overdub_change) != 1:
            self.song().add_overdub_listener(self.overdub_change)
        
    def rem_overdub_listener(self):
        if self.song().overdub_has_listener(self.overdub_change) == 1:
            self.song().remove_overdub_listener(self.overdub_change)
        
    def overdub_change(self):
        overdub = LiveUtils.getSong().overdub
    
    def session_record_change(self):
        session_record = LiveUtils.getSong().session_record

    def session_record_status_change(self):
        session_record_status = LiveUtils.getSong().session_record_status

    def metronome_change(self):
        metronome = LiveUtils.getSong().metronome

    def groove_amount_change(self):
        groove_amount = LiveUtils.getSong().groove_amount

    def add_tracks_listener(self):
        self.rem_tracks_listener()
    
        if self.song().tracks_has_listener(self.tracks_change) != 1:
            self.song().add_tracks_listener(self.tracks_change)
    
    def rem_tracks_listener(self):
        if self.song().tracks_has_listener(self.tracks_change) == 1:
            self.song().remove_tracks_listener(self.tracks_change)
    
    def tracks_change(self):
        self.refresh_state()
        return

    def rem_cclipSlot_listeners(self):
        for slot in self.ccslisten:
            if slot != None:
                if slot.controls_other_clips_has_listener(self.ccslisten[slot]) == 1:
                    slot.remove_controls_other_clips_listener(self.ccslisten[slot])

        self.ccslisten = {}

    def rem_clipSlot_listeners(self):
        for slot in self.cslisten:
            if slot != None:
                if slot.playing_status_has_listener(self.cslisten[slot]) == 1:
                    slot.remove_playing_status_listener(self.cslisten[slot])

        self.cslisten = {}

    def rem_clip_listeners(self):
        for slot in self.slisten:
            if slot != None:
                if slot.has_clip_has_listener(self.slisten[slot]) == 1:
                    slot.remove_has_clip_listener(self.slisten[slot])
    
        self.slisten = {}
        
        for clip in self.clisten:
            if clip != None:
                if clip.playing_status_has_listener(self.clisten[clip]) == 1:
                    clip.remove_playing_status_listener(self.clisten[clip])
                
        self.clisten = {}

#        for clip in self.pplisten:
#            if clip != None:
#                if clip.playing_position_has_listener(self.pplisten[clip]) == 1:
#                    clip.remove_playing_position_listener(self.pplisten[clip])
                
#        self.pplisten = {}

        for clip in self.cnlisten:
            if clip != None:
                if clip.name_has_listener(self.cnlisten[clip]) == 1:
                    clip.remove_name_listener(self.cnlisten[clip])
                
        self.cnlisten = {}

        for clip in self.cclisten:
            if clip != None:
                if clip.color_has_listener(self.cclisten[clip]) == 1:
                    clip.remove_color_listener(self.cclisten[clip])
                
        self.cclisten = {}


        for clip in self.ccnlisten:
            if clip != None:
                if clip.notes_has_listener(self.ccnlisten[clip]) == 1:
                    clip.remove_notes_listener(self.ccnlisten[clip])

        self.ccnlisten = {}

        for clip in self.clip_start_marker_listen:
            if clip != None:
                if clip.start_marker_has_listener(self.clip_start_marker_listen[clip]) == 1:
                    clip.remove_start_marker_listener(self.clip_start_marker_listen[clip])
        self.clip_start_marker_listen = {}

        for clip in self.clip_end_marker_listen:
            if clip != None:
                if clip.end_marker_has_listener(self.clip_end_marker_listen[clip]) == 1:
                    clip.remove_end_marker_listener(self.clip_end_marker_listen[clip])
        self.clip_end_marker_listen = {}

        for clip in self.clip_loop_start_listen:
            if clip != None:
                if clip.loop_start_has_listener(self.clip_loop_start_listen[clip]) == 1:
                    clip.remove_loop_start_listener(self.clip_loop_start_listen[clip])
        self.clip_loop_start_listen = {}

        for clip in self.clip_loop_end_listen:
            if clip != None:
                if clip.loop_end_has_listener(self.clip_loop_end_listen[clip]) == 1:
                    clip.remove_loop_end_listener(self.clip_loop_end_listen[clip])
        self.clip_loop_end_listen = {}

        for clip in self.clip_end_time_listen:
            if clip != None:
                if clip.end_time_has_listener(self.clip_end_time_listen[clip]) == 1:
                    clip.remove_end_time_listener(self.clip_end_time_listen[clip])
        self.clip_end_time_listen = {}

        for clip in self.clip_coarse_listen:
            if clip != None:
                if clip.pitch_coarse_has_listener(self.clip_coarse_listen[clip]) == 1:
                    clip.remove_pitch_coarse_listener(self.clip_coarse_listen[clip])
        self.clip_coarse_listen = {}

        for clip in self.wlisten:
            if clip != None:
                if clip.is_audio_clip:
                    if clip.warping_has_listener(self.wlisten[clip]) == 1:
                        clip.remove_warping_listener(self.wlisten[clip])
                
        self.wlisten = {}
        
        for clip in self.llisten:
            if clip != None:
                if clip.looping_has_listener(self.llisten[clip]) == 1:
                    clip.remove_looping_listener(self.llisten[clip])
                
        self.llisten = {}        

    def add_cclipSlot_listeners(self):
            self.rem_cclipSlot_listeners()

            tracks = self.getslots()
            for track in range(len(tracks)):
                for clip in range(len(tracks[track])):
                    c = tracks[track][clip]
                    if c != None:
                        self.add_cclipSlotlistener(c, track, clip)

    def add_clipSlot_listeners(self):
        self.rem_clipSlot_listeners()

        tracks = self.getslots()
        for track in range(len(tracks)):
            for clip in range(len(tracks[track])):
                c = tracks[track][clip]
                if c != None:
                    self.add_clipSlotlistener(c, track, clip)
        
    def add_clip_listeners(self):
        self.rem_clip_listeners()
    
        tracks = self.getslots()
        for track in range(len(tracks)):
            for clip in range(len(tracks[track])):
                c = tracks[track][clip]
                if c.clip != None:
                    self.add_cliplistener(c.clip, track, clip)
                
                self.add_slotlistener(c, track, clip)
        
    def add_cliplistener(self, clip, tid, cid):
        cb = lambda :self.clip_changestate(clip, tid, cid)
        
        if self.clisten.has_key(clip) != 1:
            clip.add_playing_status_listener(cb)
            self.clisten[clip] = cb
            
#        cb2 = lambda :self.clip_position(clip, tid, cid)
#        if self.pplisten.has_key(clip) != 1:
#            clip.add_playing_position_listener(cb2)
#            self.pplisten[clip] = cb2
            
        cb3 = lambda :self.clip_name(clip, tid, cid)
        if self.cnlisten.has_key(clip) != 1:
            clip.add_name_listener(cb3)
            self.cnlisten[clip] = cb3

        if self.cclisten.has_key(clip) != 1:
            clip.add_color_listener(cb3)
            self.cclisten[clip] = cb3

        if clip.is_audio_clip:
            cb4 = lambda: self.clip_warping(clip, tid, cid)
            if self.wlisten.has_key(clip) != 1:
                clip.add_warping_listener(cb4)
                self.wlisten[clip] = cb4
            
        cb5 = lambda: self.clip_looping(clip, tid, cid)
        if self.llisten.has_key(clip) != 1:
            clip.add_looping_listener(cb5)
            self.llisten[clip] = cb5   

        tracks = self.song().tracks
        track = tracks[tid]
        if track.has_midi_input == True:
            cb6 = lambda :self.clip_notes(clip, tid, cid)
            if self.ccnlisten.has_key(clip) != 1:
                clip.add_notes_listener(cb6)
                self.ccnlisten[clip] = cb6

        cb7 = lambda :self.clip_time(clip, tid, cid)
        if self.clip_start_marker_listen.has_key(clip) != 1:
            clip.add_start_marker_listener(cb7)
            self.clip_start_marker_listen[clip] = cb7
        if self.clip_end_marker_listen.has_key(clip) != 1:
            clip.add_end_marker_listener(cb7)
            self.clip_end_marker_listen[clip] = cb7
        if self.clip_loop_start_listen.has_key(clip) != 1:
            clip.add_loop_start_listener(cb7)
            self.clip_loop_start_listen[clip] = cb7
        if self.clip_loop_end_listen.has_key(clip) != 1:
            clip.add_loop_end_listener(cb7)
            self.clip_loop_end_listen[clip] = cb7
        if self.clip_end_time_listen.has_key(clip) != 1:
            clip.add_end_time_listener(cb7)
            self.clip_end_time_listen[clip] = cb7

        if track.has_midi_input == False:
            cb8 = lambda :self.clip_pitch(clip, tid, cid)
            if self.clip_coarse_listen.has_key(clip) != 1:
                clip.add_pitch_coarse_listener(cb8)
                self.clip_coarse_listen[clip] = cb8


    def add_cclipSlotlistener(self, slot, tid, cid):
        cb = lambda :self.clipSlot_change_controls_other_clips(slot, tid, cid)

        if self.ccslisten.has_key(slot) != 1:
            slot.add_controls_other_clips_listener(cb)
            self.ccslisten[slot] = cb


    def add_clipSlotlistener(self, slot, tid, cid):
        cb = lambda :self.clipSlot_changeplaying(slot, tid, cid)

        if self.cslisten.has_key(slot) != 1:
            slot.add_playing_status_listener(cb)
            self.cslisten[slot] = cb

    def add_slotlistener(self, slot, tid, cid):
        cb = lambda :self.slot_changestate(slot, tid, cid)
        
        if self.slisten.has_key(slot) != 1:
            slot.add_has_clip_listener(cb)
            self.slisten[slot] = cb   
            
    
    def rem_mixer_listeners(self):
        # Master Track
        for type in ("volume", "panning", "crossfader"):
            for tr in self.masterlisten[type]:
                if tr != None:
                    cb = self.masterlisten[type][tr]
                
                    test = eval("tr.mixer_device." + type+ ".value_has_listener(cb)")
                
                    if test == 1:
                        eval("tr.mixer_device." + type + ".remove_value_listener(cb)")

        # Normal Tracks
        for type in ("arm", "solo", "mute"):
            for tr in self.mlisten[type]:
                if tr != None:
                    cb = self.mlisten[type][tr]
                    
                    if type == "arm":
                        if tr.can_be_armed == 1:
                            if tr.arm_has_listener(cb) == 1:
                                tr.remove_arm_listener(cb)
                                
                    else:
                        test = eval("tr." + type+ "_has_listener(cb)")
                
                        if test == 1:
                            eval("tr.remove_" + type + "_listener(cb)")
                
        for type in ("volume", "panning"):
            for tr in self.mlisten[type]:
                if tr != None:
                    cb = self.mlisten[type][tr]
                
                    test = eval("tr.mixer_device." + type+ ".value_has_listener(cb)")
                
                    if test == 1:
                        eval("tr.mixer_device." + type + ".remove_value_listener(cb)")
         
        for tr in self.mlisten["sends"]:
            if tr != None:
                for send in self.mlisten["sends"][tr]:
                    if send != None:
                        cb = self.mlisten["sends"][tr][send]

                        if send.value_has_listener(cb) == 1:
                            send.remove_value_listener(cb)
                        
                        
        for tr in self.mlisten["name"]:
            if tr != None:
                cb = self.mlisten["name"][tr]

                if tr.name_has_listener(cb) == 1:
                    tr.remove_name_listener(cb)

        for tr in self.mlisten["collapsed"]:
            if tr != None:
                cb = self.mlisten["collapsed"][tr]

                if tr.view.is_collapsed_has_listener(cb) == 1:
                    tr.view.remove_is_collapsed_listener(cb)


        for tr in self.mlisten["om"]:
            if tr != None:
                cb = self.mlisten["om"][tr]
                
                if tr.output_meter_level_has_listener(cb) == 1:
                    tr.remove_output_meter_level_listener(cb)

                    
        for tr in self.mlisten["color"]:
            if tr != None:
                cb = self.mlisten["color"][tr]

                if tr.color_has_listener(cb) == 1:
                    tr.remove_color_listener(cb)
                   
                    
        # Return Tracks                
        for type in ("solo", "mute"):
            for tr in self.rlisten[type]:
                if tr != None:
                    cb = self.rlisten[type][tr]
                
                    test = eval("tr." + type+ "_has_listener(cb)")
                
                    if test == 1:
                        eval("tr.remove_" + type + "_listener(cb)")
                
        for type in ("volume", "panning"):
            for tr in self.rlisten[type]:
                if tr != None:
                    cb = self.rlisten[type][tr]
                
                    test = eval("tr.mixer_device." + type+ ".value_has_listener(cb)")
                
                    if test == 1:
                        eval("tr.mixer_device." + type + ".remove_value_listener(cb)")
         
        for tr in self.rlisten["sends"]:
            if tr != None:
                for send in self.rlisten["sends"][tr]:
                    if send != None:
                        cb = self.rlisten["sends"][tr][send]
                
                        if send.value_has_listener(cb) == 1:
                            send.remove_value_listener(cb)

        for tr in self.rlisten["name"]:
            if tr != None:
                cb = self.rlisten["name"][tr]

                if tr.name_has_listener(cb) == 1:
                    tr.remove_name_listener(cb)

        for tr in self.rlisten["color"]:
            if tr != None:
                cb = self.rlisten["color"][tr]

                if tr.color_has_listener(cb) == 1:
                    tr.remove_color_listener(cb)
                    
        self.mlisten = { "solo": {}, "mute": {}, "arm": {}, "panning": {}, "volume": {}, "sends": {}, "name": {}, "om": {}, "color": {}, "collapsed":{} }
        self.rlisten = { "solo": {}, "mute": {}, "panning": {}, "volume": {}, "sends": {}, "name": {}, "color": {} }
        self.masterlisten = { "panning": {}, "volume": {}, "crossfader": {} }
    
            
    def add_mixer_listeners(self):
        self.rem_mixer_listeners()
        
        # Master Track
        tr = self.song().master_track
        for type in ("volume", "panning", "crossfader"):
            self.add_master_listener(0, type, tr)
        
        #SLM 26.01.2020
        #self.add_meter_listener(0, tr, 2)

        # Normal Tracks
        tracks = self.song().tracks
        for track in range(len(tracks)):
            tr = tracks[track]

            self.add_trname_listener(track, tr, 0)
            self.add_trcolor_listener(track, tr, 0)
            self.add_trcollapsed_listener(track, tr)
                        
            #SLM 26.01.2020
            #if tr.has_audio_output:
            #    self.add_meter_listener(track, tr)

            for type in ("arm", "solo", "mute"):
                if type == "arm":
                    if tr.can_be_armed == 1:
                        self.add_mixert_listener(track, type, tr)
                else:
                    self.add_mixert_listener(track, type, tr)
                
            for type in ("volume", "panning"):
                self.add_mixerv_listener(track, type, tr)
                
            for sid in range(len(tr.mixer_device.sends)):
                self.add_send_listener(track, tr, sid, tr.mixer_device.sends[sid])
        
        # Return Tracks
        tracks = self.song().return_tracks
        for track in range(len(tracks)):
            tr = tracks[track]

            self.add_trname_listener(track, tr, 1)
            self.add_trcolor_listener(track, tr, 1)
            #SLM 26.01.2020
            #self.add_meter_listener(track, tr, 1)
            
            for type in ("solo", "mute"):
                self.add_retmixert_listener(track, type, tr)
                
            for type in ("volume", "panning"):
                self.add_retmixerv_listener(track, type, tr)
            
            for sid in range(len(tr.mixer_device.sends)):
                self.add_retsend_listener(track, tr, sid, tr.mixer_device.sends[sid])
        
    
    # Add track listeners
    def add_send_listener(self, tid, track, sid, send):
        if self.mlisten["sends"].has_key(track) != 1:
            self.mlisten["sends"][track] = {}
                    
        if self.mlisten["sends"][track].has_key(send) != 1:
            cb = lambda :self.send_changestate(tid, track, sid, send)
            
            self.mlisten["sends"][track][send] = cb
            send.add_value_listener(cb)
    
    def add_mixert_listener(self, tid, type, track):
        if self.mlisten[type].has_key(track) != 1:
            cb = lambda :self.mixert_changestate(type, tid, track)
            
            self.mlisten[type][track] = cb
            eval("track.add_" + type + "_listener(cb)")
            
    def add_mixerv_listener(self, tid, type, track):
        if self.mlisten[type].has_key(track) != 1:
            cb = lambda :self.mixerv_changestate(type, tid, track)
            
            self.mlisten[type][track] = cb
            eval("track.mixer_device." + type + ".add_value_listener(cb)")

    # Add master listeners
    def add_master_listener(self, tid, type, track):
        if self.masterlisten[type].has_key(track) != 1:
            cb = lambda :self.mixerv_changestate(type, tid, track, 2)
            
            self.masterlisten[type][track] = cb
            eval("track.mixer_device." + type + ".add_value_listener(cb)")
            
            
    # Add return listeners
    def add_retsend_listener(self, tid, track, sid, send):
        if self.rlisten["sends"].has_key(track) != 1:
            self.rlisten["sends"][track] = {}
                    
        if self.rlisten["sends"][track].has_key(send) != 1:
            cb = lambda :self.send_changestate(tid, track, sid, send, 1)
            
            self.rlisten["sends"][track][send] = cb
            send.add_value_listener(cb)
    
    def add_retmixert_listener(self, tid, type, track):
        if self.rlisten[type].has_key(track) != 1:
            cb = lambda :self.mixert_changestate(type, tid, track, 1)
            
            self.rlisten[type][track] = cb
            eval("track.add_" + type + "_listener(cb)")
            
    def add_retmixerv_listener(self, tid, type, track):
        if self.rlisten[type].has_key(track) != 1:
            cb = lambda :self.mixerv_changestate(type, tid, track, 1)
            
            self.rlisten[type][track] = cb
            eval("track.mixer_device." + type + ".add_value_listener(cb)")      


    # Track name listener
    def add_trname_listener(self, tid, track, ret = 0):
        cb = lambda :self.trname_changestate(tid, track, ret)

        if ret == 1:
            if self.rlisten["name"].has_key(track) != 1:
                self.rlisten["name"][track] = cb
        
        else:
            if self.mlisten["name"].has_key(track) != 1:
                self.mlisten["name"][track] = cb
        
        track.add_name_listener(cb)

    def add_trcollapsed_listener(self, tid, track):
        cb = lambda :self.trcollapsed_changestate(tid, track)

        if self.mlisten["collapsed"].has_key(track) != 1:
            self.mlisten["collapsed"][track] = cb

        track.view.add_is_collapsed_listener(cb)

    # Track color listener
    def add_trcolor_listener(self, tid, track, ret = 0):
        cb = lambda :self.trcolor_changestate(tid, track, ret)

        if ret == 1:
            if self.rlisten["color"].has_key(track) != 1:
                self.rlisten["color"][track] = cb
        
        else:
            if self.mlisten["color"].has_key(track) != 1:
                self.mlisten["color"][track] = cb
        
        track.add_color_listener(cb)
    
    # output_meter_level
    def add_meter_listener(self, tid, track, r = 0):
        cb = lambda :self.meter_changestate(tid, track, 0, r)

        if self.mlisten["om"].has_key(track) != 1:
            self.mlisten["om"][track] = cb

        track.add_output_meter_level_listener(cb)

        
######################################################################
# Listener Callbacks
        
    # Clip Callbacks
    def clip_warping(self, clip, tid, cid):
        return
        
    def clip_looping(self, clip, tid, cid):
        return

    
    def clip_name(self, clip, tid, cid):
        return


    def clip_pitch(self, clip, tid, cid):

        tr = LiveUtils.getTrack(tid)
        if tr == None:
            return

        cl = LiveUtils.getClip(tid, cid)
        if cl == None:
            return

        (coarse,fine) = LiveUtils.clipPitch(tid, cid)

        self.loop_update_pitch_gui()

        return

    def clip_time(self, clip, tid, cid):
        cl = LiveUtils.getClip(tid, cid)
        if cl == None:
            return
        self.loop_update_gui_buttons()
        return

    def clip_notes_l(self, tid, cid):
        trackNumber = tid
        clipNumber = cid
        in_notes = set()
        cl = LiveUtils.getClip(trackNumber, clipNumber)
        if cl == None:
            return
        #notes = cl.get_notes(self.cur_meas*4, 0, 4, 127)
        notes = cl.get_notes(0, 0, 4, 127)
        self.euc_clear_pad()
        for note in notes:
            #self.euc_send_note_to_out(note[0], note[1] - self.cur_meas*4)
            self.euc_send_note_to_out(note[0], note[1])

    def clip_notes(self, clip, tid, cid):
        self.clip_notes_l(tid, cid)


    def clip_position(self, clip, tid, cid):
        '''
        trackNumber = tid
        clipNumber = cid
        in_notes = set()
        cl = LiveUtils.getClip(trackNumber, clipNumber)
        if cl == None:
            return

        if cl.is_midi_clip:
            if cl.is_playing:
                myslog("playing " + str(cl.playing_position)) # #### PERMANENT
        '''
        return

    def clipSlot_change_controls_other_clips(self, slot, tid, cid):
        '''
        if slot != None:
            controls_other_clips = 0
            if slot.controls_other_clips == True:
                controls_other_clips = 1
        '''
        return



    def clipSlot_changeplaying(self, slot, tid, cid):
        if slot != None:
            pass

    def slot_changestate(self, slot, tid, cid):
        tmptrack = LiveUtils.getTrack(tid)
        armed = tmptrack.arm and 1 or 0


        if slot.clip != None: # Added new clip
            self.add_cliplistener(slot.clip, tid, cid)
            self.euc_clip_create_cfg(slot.clip)
            self.euc_update_status()
            self.loop_update_gui_buttons()
            self.loop_update_pitch_gui()

        else: # removed clip

            self.loop_update_gui_buttons()
            self.loop_update_pitch_gui()
            #self.clip_delete_cfg()
            self.euc_update_status()

#            if self.clisten.has_key(slot.clip) == 1:
#                slot.clip.remove_playing_status_listener(self.clisten[slot.clip])
                
#            if self.pplisten.has_key(slot.clip) == 1:
#                slot.clip.remove_playing_position_listener(self.pplisten[slot.clip])

#            if self.cnlisten.has_key(slot.clip) == 1:
#                slot.clip.remove_name_listener(self.cnlisten[slot.clip])

#            if self.cclisten.has_key(slot.clip) == 1:
#                slot.clip.remove_color_listener(self.cclisten[slot.clip])
            
#            if self.ccnlisten.has_key(slot.clip) == 1:
#                slot.clip.remove_notes_listener(self.ccnlisten[slot.clip])

#            if self.clip_start_marker_listen.has_key(slot.clip) == 1:
#                slot.clip.remove_start_marker_listener(self.clip_start_marker_listen[slot.clip])

#            if self.clip_end_marker_listen.has_key(slot.clip) == 1:
#                slot.clip.remove_end_marker_listener(self.clip_end_marker_listen[slot.clip])

#            if self.clip_loop_start_listen.has_key(slot.clip) == 1:
#                slot.clip.remove_loop_start_listener(self.clip_loop_start_listen[slot.clip])

#            if self.clip_loop_end_listen.has_key(slot.clip) == 1:
#                slot.clip.remove_loop_end_listener(self.clip_loop_end_listen[slot.clip])

#            if self.clip_end_time_listen.has_key(slot.clip) == 1:
#                slot.clip.remove_end_time_listener(self.clip_end_time_listen[slot.clip])

#            if self.clip_coarse_listen.has_key(slot.clip) == 1:
#                slot.clip.remove_pitch_coarse_listener(self.clip_coarse_listen[slot.clip])


    def clip_changestate(self, clip, x, y):

        playing = 1
        
        if clip.is_recording == 1:
            playing = 4

        elif clip.is_playing == 1:
            playing = 2
            
        elif clip.is_triggered == 1:
            playing = 3
            
        self._send_pos[x] = 3
        #log("Clip changed x:" + str(x) + " y:" + str(y) + " status:" + str(playing)) 
        
        
    # Mixer Callbacks
    def mixerv_changestate(self, type, tid, track, r = 0):
        '''
        val = eval("track.mixer_device." + type + ".value")
        types = { "panning": "pan", "volume": "volume", "crossfader": "crossfader" }
        '''
        if type == "volume":
            self.lad_get_match_mixer(track, 0)
        elif type == "panning":
            self.lad_get_match_mixer(track, 1)

        return
        
    def mixert_changestate(self, type, tid, track, r = 0):
        # type is mute, solo
        return
    
    def send_changestate(self, tid, track, sid, send, r = 0):
        self.lad_get_match_mixer(track, 2+sid)
        return
        
    # Track name changestate
    def trname_changestate(self, tid, track, r = 0):
        return

    def trcollapsed_changestate(self, tid, track):
        return


    def trcolor_changestate(self, tid, track, r = 0):
        return
    
    # Meter Changestate
    def meter_changestate(self, tid, track, lr, r = 0):
        return
    
    def check_md(self, param):
        devices = self.song().master_track.devices
        
        if len(devices) > 0:
            if devices[0].parameters[param].value > 0:
                return 1
            else:
                return 0
        else:
            return 0
    
    # Device Listeners
    def add_device_listeners(self):
        self.rem_device_listeners()
    
        self.do_add_device_listeners(self.song().tracks,0)
        self.do_add_device_listeners(self.song().return_tracks,1)
        self.do_add_device_listeners([self.song().master_track],2)
 
 
    def do_add_device_listeners(self, tracks, type):

        for i in range(len(tracks)):
            self.add_devicelistener(tracks[i], i, type)
        
            if len(tracks[i].devices) >= 1:
                for j in range(len(tracks[i].devices)):

                    self.add_devpmlistener(tracks[i].devices[j])
                    self.add_devnamelistener(tracks[i].devices[j], i, j, type)
                
                    if len(tracks[i].devices[j].parameters) >= 1:
                        for k in range (len(tracks[i].devices[j].parameters)):
                            par = tracks[i].devices[j].parameters[k]
                            self.add_paramlistener(par, i, j, k, type)


#    def add_device_param_listeners(self, device)
#        if len(device.parameters) >= 1:
#            for k in range (len(device.parameters)):
#                par = tracks[i].devices[j].parameters[k]
#                self.add_paramlistener(par, i, j, k, type)




    def rem_device_listeners(self):
        for pr in self.prlisten:
            #slm
            if pr != None:
                ocb = self.prlisten[pr]
                if pr.value_has_listener(ocb) == 1:
                    pr.remove_value_listener(ocb)
        
        self.prlisten = {}
        
        for tr in self.dlisten:
            #slm
            if tr != None:
                ocb = self.dlisten[tr]
                if tr.view.selected_device_has_listener(ocb) == 1:
                    tr.view.remove_selected_device_listener(ocb)
                    
        self.dlisten = {}
        
              
        for de in self.dnlisten:
            #slm
            if de != None:
                ocb = self.dnlisten[de]
                if de.name_has_listener(ocb) == 1:
                    de.remove_name_listener(ocb)
                    
        self.dnlisten = {}
        
        for de in self.plisten:
            #slm
            if de != None:
                ocb = self.plisten[de]
                if de.parameters_has_listener(ocb) == 1:
                    de.remove_parameters_listener(ocb)
                    
        self.plisten = {}

    def add_devpmlistener(self, device):
        cb = lambda :self.devpm_change()
        
        if self.plisten.has_key(device) != 1:
            device.add_parameters_listener(cb)
            self.plisten[device] = cb
    
    def add_devnamelistener(self, device, tr_id, dev_id, type):
        cb = lambda :self.devname_change(device, tr_id, dev_id, type)
        
        if self.dnlisten.has_key(device) != 1:
            device.add_name_listener(cb)
            self.dnlisten[device] = cb
    
    def devname_change(self, device, tid, did, type):
        return
    
    def devpm_change(self):
        self.refresh_case = 0
        self.refresh_state()
        
        
    def add_paramlistener(self, param, tid, did, pid, type):
        cb = lambda :self.param_changestate(param, tid, did, pid, type)
        
        if self.prlisten.has_key(param) != 1:
            param.add_value_listener(cb)
            self.prlisten[param] = cb
            
    def param_changestate(self, param, tid, did, pid, type):
        self.lad_get_match_fader(param)
        return
        
    def add_devicelistener(self, track, tid, type):
        # return        
        cb = lambda :self.device_changestate(track, tid, type)
        if self.dlisten.has_key(track) != 1:
            track.view.add_selected_device_listener(cb)
            self.dlisten[track] = cb
        
    def device_changestate(self, track, tid, type):
        self.lad_device_page = 0
        for g in range(GROUP_CNT):
            self.lad_perf_page[g] = 0 #device_changestate
        self.lad_show_currents() #device_changestate
        return
        
    def tuple_idx(self, tuple, obj):
        found = 0
        for i in xrange(0,len(tuple)):
            if (tuple[i] == obj):
                found = 1
                break
        if found == 1:
            return i
        else:
            return -1
       
    def add_master_track_color_listener(self):
        self.rem_master_track_color_listener()
        master_track = self.song().master_track
        master_track.add_color_listener(self.master_track_color_cb)    
        
    def rem_master_track_color_listener(self):
        master_track = self.song().master_track
        if master_track.color_has_listener(self.master_track_color_cb) == 1:
            master_track.remove_color_listener(self.master_track_color_cb)
            
    def master_track_color_cb(self):
        master_track = self.song().master_track

    
    def rem_scene_name_listeners(self):
        for sc in self.scenelisten["name"]:
            if sc != None:
                cb = self.scenelisten["name"][sc]

                if sc.name_has_listener(cb) == 1:
                    sc.remove_name_listener(cb)
        self.scenelisten = { "name": {} }
        
    def add_scene_name_listeners(self):
        self.rem_scene_name_listeners()
        
        scenes = self.song().scenes
        for scene in range(len(scenes)):
            sc = scenes[scene]
            self.add_scname_listener(scene, sc)
    
    def add_scname_listener(self, tid, scene):
        cb = lambda :self.scname_changestate(tid, scene)
        if self.scenelisten["name"].has_key(scene) != 1:
            self.scenelisten["name"][scene] = cb
        
        scene.add_name_listener(cb)
        
    def scname_changestate(self, tid, scene):
        return
        
    ######### scene
    
    def add_scenes_listener(self):
        self.rem_scenes_listener()
    
        if self.song().scenes_has_listener(self.scenes_change) != 1:
            self.song().add_scenes_listener(self.scenes_change)

    def scenes_change(self):
        self.refresh_state()
        return

    def rem_scenes_listener(self):
        if self.song().scenes_has_listener(self.scenes_change) == 1:
            self.song().remove_scenes_listener(self.scenes_change)


    # def add_scenes_listeners(self):
        # self.rem_scenes_listeners()
        # scenes = self.song().scenes
        # for sc in range (len(scenes)):
            # scene = scenes[sc]
            # self.add_scenelistener(scene, sc)

    # def rem_scenes_listeners(self):
        # for scene in self.sclisten:
            # if scene != None:
                # if scene.color_has_listener(self.sclisten[scene]) == 1:
                    # scene.remove_color_listener(self.sclisten[scene])
            # else:
                # pass
        # self.sclisten = {}

        # for scene in self.snlisten:
            # if scene != None:
                # if scene.name_has_listener(self.snlisten[scene]) == 1:
                    # scene.remove_name_listener(self.snlisten[scene])
            # else:
                # pass
        # self.snlisten = {}
        
        # for scene in self.stlisten:
            # if scene != None:
                # if scene.is_triggered_has_listener(self.stlisten[scene]) == 1:
                    # scene.remove_is_triggered_listener(self.stlisten[scene])
            # else:
                # pass
        # self.stlisten = {}
        
    # def add_scenelistener(self, scene, sc):
        # cb = lambda :self.scene_color_changestate(scene, sc)
        # if self.sclisten.has_key(scene) != 1:
            # scene.add_color_listener(cb)
            # self.sclisten[scene] = cb
        # else:
            # pass
            
        # cb2 = lambda :self.scene_name_changestate(scene, sc)
        # if self.snlisten.has_key(scene) != 1:
            # scene.add_name_listener(cb2)
            # self.snlisten[scene] = cb2
        # else:
            # pass
                
        # cb3 = lambda :self.scene_triggered(scene, sc)
        # if self.stlisten.has_key(scene) != 1:
            # scene.add_is_triggered_listener(cb3)
            # self.stlisten[scene] = cb3
        # else:
            # pass
        

    # def scene_color_changestate(self, scene, sc):
        # nm = ""
        # nm = scene.name
        # if scene.color == 0:
            # self.oscServer.sendOSC("/scene", (sc, repr3(nm), 0))
        # else:
            # self.oscServer.sendOSC("/scene", (sc, repr3(nm), scene.color))

    # def scene_name_changestate(self, scene, sc):
        # nm = ""
        # nm = scene.name
        # if scene.color == 0:
            # self.oscServer.sendOSC("/scene", (sc, repr3(nm), 0))
        # else:
            # self.oscServer.sendOSC("/scene", (sc, repr3(nm), scene.color))

    # def scene_triggered(self, scene, sc):
        # self.oscServer.sendOSC("/scene/fired", int(sc+1))

#    ################################################################################################
#    ## TOUCH OSC CB

    def init_cb(self):

        self.oscEndpoint.callbackManager.add("/ping", self.m_ping_cb)

        self.oscEndpoint.callbackManager.group_add("/euc_ext/pitch", self.euc_pitch_x_cb)
        self.oscEndpoint.callbackManager.add("/euc_ext/trsp", self.euc_trsp_ext_cb)

        self.oscEndpoint.callbackManager.add("/euc/tab", self.euc_tab_cb)
        self.oscEndpoint.callbackManager.add("/lad/tab", self.lad_tab_cb)
        self.oscEndpoint.callbackManager.add("/util/tab", self.util_tab_cb)
        self.oscEndpoint.callbackManager.add("/morph/tab", self.morph_tab_cb)
        self.oscEndpoint.callbackManager.add("/loop/tab", self.loop_tab_cb)

        self.oscEndpoint.callbackManager.group_add("/euc/euc_menu", self.euc_menu_cb)
        self.oscEndpoint.callbackManager.group_add("/euc/euc_note", self.euc_note_cb)
        self.oscEndpoint.callbackManager.group_add("/euc/euc_play", self.euc_play_cb)
        self.oscEndpoint.callbackManager.group_add("/euc/euc_steps", self.euc_steps_cb)
        self.oscEndpoint.callbackManager.group_add("/euc/euc_pulses", self.euc_pulses_cb)
        self.oscEndpoint.callbackManager.group_add("/euc/euc_shift", self.euc_shift_cb)
        self.oscEndpoint.callbackManager.group_add("/euc/euc_len", self.euc_len_cb)
        self.oscEndpoint.callbackManager.group_add("/euc/euc_vel", self.euc_vel_cb)
        self.oscEndpoint.callbackManager.group_add("/euc/euc_out", self.euc_out_debug_cb)
        self.oscEndpoint.callbackManager.group_add("/euc/euc_control", self.euc_control_cb)
        self.oscEndpoint.callbackManager.group_add("/euc/euc_drive", self.euc_drive_cb)

        self.lad_init_cb()

        self.util_init_cb()

        self.morph_init_cb()

        return 1


    def util_tab_cb(self, msg, source):
        self.touch_change_tab(UTIL_TAB)
        return

    def lad_tab_cb(self, msg, source):
        self.touch_change_tab(LAD_TAB)
        return

    def morph_tab_cb(self, msg, source):
        self.touch_change_tab(MORPH_TAB)
        return

    def euc_tab_cb(self, msg, source):
        self.touch_change_tab(EUC_TAB)
        return

    def loop_tab_cb(self, msg, source):
        self.touch_change_tab(LOOP_TAB)
        return

    def euc_menu_cb(self, msg, source):
        pressed = msg[2]
        if pressed != 0:
            return
        button = -1
        address = msg[0]
        addresses = address.split("/")
        if len(addresses) == 5:
            button = int(addresses[4])
            y = int(addresses[3])
            x = int(addresses[4])
            button = (4-y)*7 + x

        if button != -1:
            self.euc_menu(button)
        return


    def euc_drive_cb(self, msg, source):
        pressed = msg[2]
        button = -1
        address = msg[0]
        addresses = address.split("/")
        if len(addresses) == 5:
            button = int(addresses[4])
            y = int(addresses[3])
            x = int(addresses[4])
            button = (2-y)*8 + x

        if button != -1:
            self.euc_drive(button, int(pressed))
        return

    def euc_control_cb(self, msg, source):
        pressed = msg[2]
        if pressed != 0:
            return
        button = -1
        address = msg[0]
        addresses = address.split("/")
        if len(addresses) == 5:
            button = int(addresses[4])
            y = int(addresses[3])
            x = int(addresses[4])
            button = (4-y)*3 + x

        if button != -1:
            self.euc_control(button)
        return


    def euc_play_cb(self, msg, source):
        pressed = msg[2]
        button = -1
        address = msg[0]
        addresses = address.split("/")
        if len(addresses) == 5:
            button = int(addresses[4])

        if button != -1:
            self.euc_play(button, int(pressed))
        return

    def euc_note_cb(self, msg, source):
        pressed = msg[2]
        if pressed != 1.0:
            return

        button = -1
        address = msg[0]
        addresses = address.split("/")
        if len(addresses) == 5:
            button = int(addresses[4])

        if button != -1:
            self.euc_note(button)
        return

    def euc_steps_cb(self, msg, source):
        pressed = msg[2]
        if pressed != 1.0:
            return

        button = -1
        address = msg[0]

        addresses = address.split("/")
        if len(addresses) == 5:
            button = int(addresses[4])

        if button != -1:
            self.euc_steps(button)
        return

    def euc_pulses_cb(self, msg, source):
        pressed = msg[2]
        if pressed != 1.0:
            return

        button = -1
        address = msg[0]
        addresses = address.split("/")
        if len(addresses) == 5:
            button = int(addresses[4])

        if button != -1:
            self.euc_pulses(button)
        return

    def euc_shift_cb(self, msg, source):
        pressed = msg[2]
        if pressed != 1.0:
            return

        button = -1
        address = msg[0]
        addresses = address.split("/")
        if len(addresses) == 5:
            button = int(addresses[4])

        if button != -1:
            self.euc_shift(button)
        return

    def euc_len_cb(self, msg, source):
        pressed = msg[2]
        button = -1
        address = msg[0]
        addresses = address.split("/")
        if len(addresses) == 5:
            button = int(addresses[4])

        if button != -1:
            self.euc_len_set(button, int(pressed))
        return

    def euc_vel_cb(self, msg, source):
        pressed = msg[2]
        button = -1
        address = msg[0]
        addresses = address.split("/")
        if len(addresses) == 5:
            button = int(addresses[4])

        if button != -1:
            self.euc_vel_set(button, int(pressed))
        return

    def euc_out_debug_cb(self, msg, source):
        self.euc_display_cfg()
        return


    def euc_pitch_x_cb(self, msg, source):
        address = msg[0]
        rs = "/euc_ext/pitch"
        ls = len(rs)
        ns = address[ls:]
        do_it = False
        try:
            pitch_idx = int(ns)
            do_it = True
        except:
            do_it = False

        if do_it == True:
            self.euc_pitch_x(pitch_idx, msg[2])

    def euc_trsp_ext_cb(self, msg, source):
        self.euc_trsp_ext(msg[2])
        return


    #    ################################################################################################
    #    ## END OF TOUCH OSC CB

    #    ################################################################################################
    #    ## USEFUL FCT

    all_tracks = []
    sends_count = 0
    def update_tracks_list(self):
        self.all_tracks = []
        self.sends_count = 0
        for i in range(len(self.song().tracks)):
            track = self.song().tracks[i]
            self.all_tracks.append(track)
            self.lad_set_track_id(track)

            if i == 0:
                self.sends_count = len(track.mixer_device.sends)

        for i in range(len(self.song().return_tracks)):
            track = self.song().return_tracks[i]
            self.all_tracks.append(track)
            self.lad_set_track_id(track)

        self.all_tracks.append(self.song().master_track)
        self.lad_set_track_id(self.song().master_track)

        return

    def get_working_audio_track(self):
        tid = -1
        current_track = self.song().view.selected_track

        if(current_track != None):
            if(current_track != self.song().master_track):
                returnTracks = self.song().return_tracks
                rid = self.tuple_idx(returnTracks, current_track)
                if rid == -1:
                    tracks = self.song().tracks
                    tid = self.tuple_idx(tracks, current_track)
                    if tid != -1:
                        if current_track.has_midi_input:
                            tid = -1
                        if current_track.is_foldable:
                            tid = -1
        return tid

    def get_working_audio_clip(self):
        clip = None
        tid = self.get_working_audio_track()

        if(tid != -1):
            cs = self.song().view.highlighted_clip_slot
            if cs.clip != None:
                clip = cs.clip

        return clip

    def get_working_midi_track(self):
        tid = -1
        current_track = self.song().view.selected_track

        if(current_track != None):
            if(current_track != self.song().master_track):
                returnTracks = self.song().return_tracks
                rid = self.tuple_idx(returnTracks, current_track)
                if rid == -1:
                    tracks = self.song().tracks
                    tid = self.tuple_idx(tracks, current_track)
                    if tid != -1:
                        if current_track.has_midi_input == False:
                            tid = -1
        return tid



    def get_cur_tid_cid(self):

        current_track = self.song().view.selected_track
        if current_track == None:
            return -1, -1

        tid = self.get_working_midi_track()
        if tid == -1:
            return -1, -1

        cs = self.song().view.highlighted_clip_slot
        if cs == None:
            return -1, -1

        if cs.has_clip == False:
            return -1, -1

        if cs.clip.is_midi_clip == False:
            return -1, -1

        cid = self.tuple_idx(current_track.clip_slots, cs)

        return tid, cid;

    def NoteToMidi(self, KeyOctave):
        # KeyOctave is formatted like 'C#3'
        key = KeyOctave[:-1]  # eg C, Db
        octave = KeyOctave[-1]   # eg 3, 4
        answer = -1
        try:
            if 'b' in key:
                pos = self.NOTES_FLAT.index(key)
            else:
                pos = self.NOTES_SHARP.index(key)
        except:
            myelog('The key is not valid')
            return answer

        answer += pos + 12 * (int(octave) + 2) +1
        return answer

    def MidiToNote(self, pitch, flat = True):
        KeyOctave = ""
        note = pitch%12
        if flat == True:
            note_str = self.NOTES_FLAT[note]
        else:
            note_str = self.NOTES_SHARP[note]
        octave = (pitch - pitch%12)/12 - 2
        KeyOctave = note_str + str(int(octave))
        return KeyOctave


    def adaptValue(self, val, inMin, inMax, outMin, outMax, steps = -1):
        a = (float(outMax) - float(outMin)) / (float(inMax) - float(inMin))
        b = float(outMin) - float(inMin)*float(a)
        rt = float(val)*float(a)+float(b)
        if steps != -1: # steps value is not used
            if rt != outMin:
                if rt != outMax:
                    if rt > 0:
                        i = floor(rt)
                        e = rt - i
                        if e > 0.5:
                            rt = i + 1
                        else:
                            rt = i
        return rt

    def midi_get_rel_dec_inc_val(self, val, get_accelaration = True):

        if const.midi_relative == False:
            return 0

        if const.midi_relative_mode == 1:
            if get_accelaration == True:
                val = val - 64
            else:
                if val > 64:
                    val = 1
                else:
                    val = -1

        elif const.midi_relative_mode == 2:
            if get_accelaration == True:
                if val > 64:
                    val = val - 128
            else:
                if val > 64:
                    val = -1
                else:
                    val = 1

        elif const.midi_relative_mode == 3:
            if get_accelaration == True:
                if val > 64:
                    val = val - 64
                else:
                    val = -val
            else:
                if val > 64:
                    val = 1
                else:
                    val = -1

        elif const.midi_relative_mode == 4:
            if get_accelaration == True:
                if val > 64:
                    val = -(val-64)
            else:
                if val > 64:
                    val = -1
                else:
                    val = 1


        else:
            return 0

        return val

    #    ################################################################################################
    #    ## END OF USEFUL FCT


    #    ################################################################################################
    #    ## GENERAL

    def m_ping_cb(self, msg, source):
        #myslog("ping") # #### PERMANENT
        return

    def touch_init(self):
        self.clear_midi() # touch_init
        self.oscEndpoint.send("/util/push_test/visible", "False")
        self.touch_change_tab(self.lito_tab)
        self.util_init()
        self.lad_init()
        self.morph_init()
        self.euc_init()
        self.loop_init()
        return

    def touch_exit(self):

        self.util_exit()
        self.lad_exit()
        self.loop_exit()

        address = "/lad/led_play"
        self.oscEndpoint.send(address, 0)

        self.euc_exit()

        self.oscEndpoint.send("/util/tab", 1 )
        self.lito_tab = UTIL_TAB
        self.clear_midi() # touch_exit
        return

    def touch_display_tab(self, button):
        if button == -1:
            return

        for i in range(3):
            self.send_midi_ex((0xB0, button, 127), self.lito_tab)
            sleep(0.05)
            self.send_midi_ex((0xB0, button, 0), self.lito_tab)
            sleep(0.05)
        return

    def touch_change_tab(self, lito_tab):
        self.lito_tab = lito_tab

        if self.lito_tab == UTIL_TAB:
            self.oscEndpoint.send("/util/tab", 1 )
            self.oscEndpoint.clean_cache()
            self.touch_display_tab(const.MIDI_UTIL_TAB_INDICATOR)
            self.clear_midi() # UTIL_TAB
            self.lad_update() # UTIL_TAB

        elif self.lito_tab == LAD_TAB:
            self.oscEndpoint.send("/lad/tab", 1 )
            self.oscEndpoint.clean_cache()
            self.touch_display_tab(const.MIDI_LAD_TAB_INDICATOR)
            self.clear_midi() # LAD_TAB
            self.lad_update() # LAD_TAB

        elif self.lito_tab == MORPH_TAB:
            self.oscEndpoint.send("/morph/tab", 1 )
            self.oscEndpoint.clean_cache()
            self.touch_display_tab(const.MIDI_MORPH_TAB_INDICATOR)
            self.clear_midi() # MORPH_TAB
            self.lad_update() # MORPH_TAB

        elif self.lito_tab == EUC_TAB:
            self.oscEndpoint.send("/euc/tab", 1 )
            self.oscEndpoint.clean_cache()
            self.touch_display_tab(const.MIDI_EUC_TAB_INDICATOR)
            self.clear_midi() # EUC_TAB
            self.euc_update_gui_full() # EUC_TAB

        elif self.lito_tab == LOOP_TAB:
            self.oscEndpoint.send("/loop/tab", 1 )
            self.oscEndpoint.clean_cache()
            self.touch_display_tab(const.MIDI_LOOP_TAB_INDICATOR)
            self.clear_midi() # LOOP_TAB
            self.loop_update_gui() # LOOP_TAB

        return

    def clear_midi(self):
        for i in range(128):
            self.send_midi(((0xb0 | const.midi_channel), i, 0))

#    ################################################################################################
#    ## END OF GENERAL


    pitches = [36,37,38,39,40,42,46,51]
    pitches_dr1 = [36,37,38,39,40,42,44,46]
    pitches_dr2 = [36,37,38,39,40,42,46,51]
    pitches_maj = [36,38,40,41,43,45,47,48]
    pitches_min = [36,38,39,41,43,44,46,48]
    pitches_minH = [36,38,39,41,43,44,47,48]
    pitches_minM = [36,38,39,41,43,45,47,48]
    pitches_dor = [36,38,39,41,43,45,46,48]
    pitches_phry = [36,37,39,41,43,44,46,48]
    pitches_lyd = [36,38,40,42,43,45,47,48]
    pitches_mixo = [36,38,40,41,43,45,46,48]
    pitches_loc = [36,37,39,41,42,44,46,48]

    NOTES_FLAT = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
    NOTES_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    euc_rand_mode = False
    euc_trsp = 0
    euc_cur_note = 1
    euc_default_cfg = (0, EUC_PACE_CNT, 1, 0)
    euc_cfg = []
    euc_len = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    euc_vel = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    euc_clips_cfg = {}
    euc_clips_len = {}
    euc_clips_vel = {}
    euc_clips_trsp = {}
    euc_clips_pitches = {}
    euc_trsp_all = True

    euc_midi_encoders = [const.MIDI_EUC_ENCODER1, const.MIDI_EUC_ENCODER2, const.MIDI_EUC_ENCODER3]
    euc_midi_cur_note = [const.MIDI_EUC_CURNOTE1, const.MIDI_EUC_CURNOTE2, const.MIDI_EUC_CURNOTE3, const.MIDI_EUC_CURNOTE4, const.MIDI_EUC_CURNOTE5, const.MIDI_EUC_CURNOTE6, const.MIDI_EUC_CURNOTE7, const.MIDI_EUC_CURNOTE8]
    euc_midi_plays = [const.MIDI_EUC_PLAY1, const.MIDI_EUC_PLAY2, const.MIDI_EUC_PLAY3, const.MIDI_EUC_PLAY4, const.MIDI_EUC_PLAY5, const.MIDI_EUC_PLAY6, const.MIDI_EUC_PLAY7, const.MIDI_EUC_PLAY8]



    def euc_init(self):
#        self.euc_clear_set_note()
        self.euc_cur_note = 1

        self.euc_update_gui_note()

        self.euc_clr_cfg()

        self.euc_update_gui_play()
        self.euc_update_gui_sps(self.euc_cur_note)
        self.euc_update_gui_len(True)
        self.euc_update_gui_vel(True)
        self.euc_update_gui_trsp()

        self.euc_rand_mode = False
        self.euc_update_rand_mode_gui()

        self.euc_trsp_all = True
        self.euc_update_trsp_all_gui()

        self.euc_disp_play()

        self.oscEndpoint.send("/euc/euc_status", str(""))
        self.oscEndpoint.send("/euc/euc_trsp", str(self.euc_trsp))

        self.euc_clear_pad()
        self.euc_update_pitches()
        self.euc_control_gui()
        self.euc_drive_gui() # euc init


    def euc_exit(self):

        self.euc_clear_pad()
        address = "/euc/led_play"
        self.oscEndpoint.send(address, 0)
        self.oscEndpoint.send("/euc/euc_status", str(""))
        self.oscEndpoint.send("/euc/euc_trsp", str(""))

        if self.oscEndpoint.get_phone_osc() == False:
            self.oscEndpoint.send("/euc/label_note_idx", "")
            self.oscEndpoint.send("/euc/label_cur_pitch", "")
            for i in range(EUC_PACE_HALF_CNT):
                address = "/euc/euc_play/1/" + str(i+1)
                self.oscEndpoint.send(address, 0)
                address = "/euc/euc_note/1/" + str(i+1)
                self.oscEndpoint.send(address, 0)
                self.oscEndpoint.send("/euc/label_steps_idx", "" )
                self.oscEndpoint.send("/euc/label_pulses_idx", "" )
                self.oscEndpoint.send("/euc/label_shift_idx", "" )

            for i in range(EUC_PACE_CNT):
                address = "/euc/euc_steps/1/" + str(i+1)
                self.oscEndpoint.send(address, 0)
                address = "/euc/euc_pulses/1/" + str(i+1)
                self.oscEndpoint.send(address, 0)
                address = "/euc/euc_shift/1/" + str(i+1)
                self.oscEndpoint.send(address, 0)

#        self.euc_clear_set_note()
        self.euc_update_gui_len(True)
        self.euc_update_gui_vel(True)

        self.euc_rand_mode = False
        self.euc_update_rand_mode_gui()
        self.euc_update_pitches(True)



    def euc_update_status(self):

        self.euc_clear_pad()
        self.oscEndpoint.send("/euc/euc_status", str("X"))

        current_track = self.song().view.selected_track
        if current_track == None:
            return

        tid = self.get_working_midi_track()
        if tid == -1:
            return

        self.oscEndpoint.send("/euc/euc_status", str("O"))
        cs = self.song().view.highlighted_clip_slot
        if cs != None:
            cid = self.tuple_idx(current_track.clip_slots, cs)
            if cs.has_clip and cs.clip.is_midi_clip:
                cl = cs.clip
                if cl != None:
                    self.oscEndpoint.send("/euc/euc_status", str("I"))
                    notes = cl.get_notes(0, 0, 4, 127)
                    for note in notes:
                        self.euc_send_note_to_out(note[0], note[1])

    def euc_clear_pad(self):
        if self.oscEndpoint.get_phone_osc() == True:
            return
        block = []
        for i in range(EUC_PACE_CNT):
            block.extend([0])
        self.oscEndpoint.send("/euc/euc_out", block)
        return

    def euc_send_note_to_out(self, pitch, time):
        if self.oscEndpoint.get_phone_osc() == True:
            return

        idx_pitch = -1
        for i in range(EUC_PACE_HALF_CNT):
            if pitch == self.pitches[i]:
                idx_pitch = i
                break

        if idx_pitch != -1:
            idx_time = (int)(time*4)
            if idx_time >= 0:
                if idx_time < EUC_PACE_CNT:
                    euc_cur_note = self.euc_cur_note - 1
                    if pitch == self.pitches[euc_cur_note]:
                        add_str = "/euc/euc_out/1/" + str(idx_time+1)
                        self.oscEndpoint.send(add_str, 1.0)


    def euc_update_pitches(self, reset = False):
        for i in range(EUC_PACE_HALF_CNT):
            note_str = ""
            if reset == False:
                note_str = self.MidiToNote(self.pitches[i])
            add_str = "/euc/epitch" + str(i+1) + "/"
            self.oscEndpoint.send(add_str, note_str)
        self.euc_update_gui_note()
        return

    def euc_pitch_x_ext(self, idx, pitch):
       ipitch = self.NoteToMidi(pitch)
       if ipitch != -1:
           self.pitches[idx-1] = ipitch
           self.euc_update_pitches()
       return

    def euc_trsp_ext(self, trsp):
        for i in range(EUC_PACE_HALF_CNT):
            backup_pitch = self.pitches[i]
            backup_pitch = backup_pitch + trsp
            note = self.MidiToNote(backup_pitch)
            new_pitch = self.NoteToMidi(note)
            if new_pitch != -1:
                self.pitches[i] = new_pitch

        self.euc_update_pitches()
        return

    def euc_new_clip(self, fill_clip, clip_length = 4):

        current_track = self.song().view.selected_track
        if current_track == None:
            return None

        tid = self.get_working_midi_track()
        if tid == -1:
            return None

        clip_id = -1

        cid = 0
        self.cur_meas = 0

        original_cs = self.song().view.highlighted_clip_slot

        for cs in current_track.clip_slots:
            if cs.has_clip == False:
                break
            cid = cid + 1

        do_refresh = 0
        scenes = self.song().scenes
        if cid == len(scenes):
            self.song().create_scene(-1)
            do_refresh = 1

        current_track.clip_slots[cid].create_clip(clip_length)
        current_track.clip_slots[cid].fire()

        clr = current_track.clip_slots[cid].clip
        if fill_clip and original_cs != None:
            cl = original_cs.clip
            if cl != None:
                notes = cl.get_notes(0.0, 0, cl.loop_end - cl.loop_start, 127)
                current_track.clip_slots[cid].clip.replace_selected_notes(notes)

        LiveUtils.getSong().view.selected_track = current_track
        LiveUtils.getSong().view.highlighted_clip_slot = current_track.clip_slots[cid]
        LiveUtils.getSong().view.detail_clip = current_track.clip_slots[cid].clip
        Live.Application.get_application().view.show_view("Detail/Clip")
        self.oscEndpoint.send("/jungle/cid", str(int(tid)) + " - " + str(int(cid)) )

        return clr


    #    ################################################################################################
    #    ## EUC ENGINE

    def bjorklund(self, steps, pulses, shift):

        if shift >= steps:
            shift = 0
        steps = int(steps)
        pulses = int(pulses)
        if pulses > steps:
            pulses = steps
        pattern = []
        counts = []
        remainders = []
        divisor = steps - pulses
        remainders.append(pulses)
        level = 0
        while True:
            counts.append(divisor // remainders[level])
            remainders.append(divisor % remainders[level])
            divisor = remainders[level]
            level = level + 1
            if remainders[level] <= 1:
                break
        counts.append(divisor)

        def build(level):
            if level == -1:
                pattern.append(0)
            elif level == -2:
                pattern.append(1)
            else:
                for i in range(0, counts[level]):
                    build(level - 1)
                if remainders[level] != 0:
                    build(level - 2)

        build(level)

        i = pattern.index(1)
        pattern = pattern[i:] + pattern[0:i]
        #pattern = pattern[shift:] + pattern[0:shift]
        if shift != 0:
            pattern = pattern[(steps-shift):] + pattern[0:(steps-shift)]

        sequence = []

        for i in range(EUC_PACE_CNT):
            sequence.append(pattern[i%len(pattern)])

        return sequence


    #    ################################################################################################
    #    ## END OF EUC ENGINE

    #    ################################################################################################
    #    ## EUC TAB

    def euc_clear_cfg(self):
        self.euc_clr_cfg()
        self.euc_clr_cfg_len()
        self.euc_clr_cfg_vel()
        self.euc_trsp = 0
        self.euc_update_gui_play()
        self.euc_update_gui_sps(self.euc_cur_note)
        self.euc_update_gui_len(True)
        self.euc_update_gui_vel(True)
        self.euc_update_gui_trsp()
        return


    def euc_get_menu_coord(self, button):
        if button < 1:
            return 0,0

        if button > 28:
            return 0,0

        button = button - 1
        y = int(button / 7)
        x = button - y*7 + 1
        y = 4 - y

        return x,y


    def euc_menu(self, button):

        if button == 1:
            self.euc_new_clip(False)
            self.euc_fill_clip()
        elif button == 2:
            self.euc_clear_cfg()
            self.euc_fill_clip()
        elif button == 3:
            pass
        elif button == 4:
            self.euc_rnd1()
        elif button == 5:
            self.euc_rnd2()
        elif button == 6:
            self.euc_rand_mode = not self.euc_rand_mode
            x,y = self.euc_get_menu_coord(button)
            address = "/euc/euc_menu/" + str(y) + "/" + str(x)
            self.oscEndpoint.send(address, float(self.euc_rand_mode))

        elif button == 7:
            LiveUtils.ps()
        elif button == 8:
            self.euc_set_pitch("-1")
        elif button == 9:
            self.euc_set_pitch("+1")
        elif button == 10:
            self.euc_set_pitch("-12")
        elif button == 11:
            self.euc_set_pitch("+12")
        elif button == 12:
            self.euc_trsp_all = not self.euc_trsp_all
            self.euc_update_trsp_all_gui()
        elif button == 18:
            self.euc_set_pitch("dr1")
        elif button == 19:
            self.euc_set_pitch("dr2")
        elif button == 20:
            self.euc_set_pitch("maj")
        elif button == 21:
            self.euc_set_pitch("min")
        elif button == 22:
            self.euc_set_pitch("minH")
        elif button == 23:
            self.euc_set_pitch("minM")
        elif button == 24:
            self.euc_set_pitch("dor")
        elif button == 25:
            self.euc_set_pitch("phry")
        elif button == 26:
            self.euc_set_pitch("lyd")
        elif button == 27:
            self.euc_set_pitch("mixo")
        elif button == 28:
            self.euc_set_pitch("loc")
        return



    def euc_set_pitch(self, mode, fill_clip = True):

        lp = []
        if mode == "dr1":
            for i in range(len(self.pitches)):
                nn = self.pitches_dr1[i]
                nn = nn + self.euc_trsp
                lp.extend([nn])

        elif mode == "dr2":
            for i in range(len(self.pitches)):
                nn = self.pitches_dr2[i]
                nn = nn + self.euc_trsp
                lp.extend([nn])

        elif mode == "maj":
            for i in range(len(self.pitches)):
                nn = self.pitches_maj[i]
                nn = nn + self.euc_trsp
                lp.extend([nn])

        elif mode == "min":
            for i in range(len(self.pitches)):
                nn = self.pitches_min[i]
                nn = nn + self.euc_trsp
                lp.extend([nn])

        elif mode == "minH":
            for i in range(len(self.pitches)):
                nn = self.pitches_minH[i]
                nn = nn + self.euc_trsp
                lp.extend([nn])

        elif mode == "minM":
            for i in range(len(self.pitches)):
                nn = self.pitches_minM[i]
                nn = nn + self.euc_trsp
                lp.extend([nn])

        elif mode == "dor":
            for i in range(len(self.pitches)):
                nn = self.pitches_dor[i]
                nn = nn + self.euc_trsp
                lp.extend([nn])

        elif mode == "phry":
            for i in range(len(self.pitches)):
                nn = self.pitches_phry[i]
                nn = nn + self.euc_trsp
                lp.extend([nn])

        elif mode == "lyd":
            for i in range(len(self.pitches)):
                nn = self.pitches_lyd[i]
                nn = nn + self.euc_trsp
                lp.extend([nn])

        elif mode == "mixo":
            for i in range(len(self.pitches)):
                nn = self.pitches_mixo[i]
                nn = nn + self.euc_trsp
                lp.extend([nn])

        elif mode == "loc":
            for i in range(len(self.pitches)):
                nn = self.pitches_loc[i]
                nn = nn + self.euc_trsp
                lp.extend([nn])

        else:

            trsp = int(mode)
            if self.euc_trsp_all == True:
                self.euc_trsp = self.euc_trsp + trsp
                for i in range(len(self.pitches)):
                    lp.extend([self.pitches[i] + trsp])
            else:
                for i in range(len(self.pitches)):
                    if (i+1) == self.euc_cur_note:
                        lp.extend([self.pitches[i] + trsp])
                    else:
                        lp.extend([self.pitches[i]])

        self.pitches = lp
        self.euc_update_pitches()

        if fill_clip == True:
            tid, cid = self.get_cur_tid_cid()
            self.euc_clip_update_cfg(tid, cid)
            self.euc_update_gui_trsp()

            self.euc_fill_clip()

        return

    def euc_play(self, button, pressed):
        if button < 1:
            return
        if button > EUC_PACE_HALF_CNT:
            return

        self.euc_set_cfg(button, "play", int(pressed))
        self.euc_fill_clip()

        return

    def euc_note(self, button):
        if button < 1:
            return
        if button > EUC_PACE_HALF_CNT:
            return

        self.euc_cur_note = button

        self.euc_update_gui_note()
        self.euc_update_gui_sps(self.euc_cur_note)

        tid, cid = self.get_cur_tid_cid()
        if tid == -1:
            return

        if cid == -1:
            return

        self.clip_notes_l(tid, cid)

        return

    def euc_steps(self, button):
        if button < 1:
            return
        if button > EUC_PACE_CNT:
            return

        self.euc_set_cfg(self.euc_cur_note, "steps", button)
        self.euc_update_gui_sps(self.euc_cur_note)
        self.euc_fill_clip()
        return

    def euc_pulses(self, button):
        if button < 1:
            return
        if button > EUC_PACE_CNT:
            return

        self.euc_set_cfg(self.euc_cur_note, "pulses", button)
        self.euc_update_gui_sps(self.euc_cur_note)
        self.euc_fill_clip()
        return

    def euc_shift(self, button):
        if button < 1:
            return
        if button > EUC_PACE_CNT:
            return

        self.euc_set_cfg(self.euc_cur_note, "shift", button-1)
        self.euc_update_gui_sps(self.euc_cur_note)
        self.euc_fill_clip()
        return

    def euc_clr_cfg(self):
        self.euc_cfg = []
        for i in range(EUC_PACE_HALF_CNT):
            self.euc_cfg.append(self.euc_default_cfg)

    def euc_set_cfg(self, note, mode, val):
        if note < 1:
            return
        if note > EUC_PACE_HALF_CNT:
            return

        thistuple = self.euc_cfg[note-1]

        if mode == "play":
            thistuple = (val, thistuple[1], thistuple[2], thistuple[3])
        elif mode == "steps":
            val2 = thistuple[2]
            val3 = thistuple[3]
            if val<val2:
                val2 = val
            if (val-1)<val3:
                val3 = val - 1
            thistuple = (thistuple[0], val, val2, val3)
        elif mode == "pulses":
            if val > thistuple[1]:
                val = thistuple[1]
            thistuple = (thistuple[0], thistuple[1], val, thistuple[3])
        elif mode == "shift":
            if val > (thistuple[1]-1):
                val = thistuple[1]-1
            thistuple = (thistuple[0], thistuple[1], thistuple[2], val)

        self.euc_cfg[note-1] = thistuple
        tid, cid = self.get_cur_tid_cid()
        self.euc_clip_update_cfg(tid, cid)

        return

    def euc_rnd(self, cur_note, mode):
        steps = random.randint(1, EUC_PACE_CNT)
        self.euc_set_cfg(cur_note, "steps", steps)
        set_ps = steps
        if mode == True:
            set_ps = int(steps/2)
            if set_ps == 0:
                set_ps = set_ps + 1
        self.euc_set_cfg(cur_note, "pulses", random.randint(1, set_ps))
        self.euc_set_cfg(cur_note, "shift", random.randint(0, set_ps-1))

    def euc_rnd1(self):
        self.euc_rnd(self.euc_cur_note, self.euc_rand_mode)
        self.euc_update_gui_sps(self.euc_cur_note)
        self.euc_fill_clip()
        return

    def euc_rnd2(self):
        for i in range(1,EUC_PACE_CNT+1):
            self.euc_rnd(i,self.euc_rand_mode)
        self.euc_update_gui_sps(self.euc_cur_note)
        self.euc_fill_clip()
        return


    def euc_fill_clip(self):

        tid, cid = self.get_cur_tid_cid()
        if tid == -1:
            return
        if cid == -1:
            return

        cl = LiveUtils.getClip(tid, cid)

        notes = cl.get_notes(0, 0, cl.length, 127)
        ll = len(notes)
        cl.deselect_all_notes()
        if ll != 0:
            for note in notes:
                cl.remove_notes(float(note[1]), int(note[0]), 0.25, 1)

        def reset_sequence():
            for i in range(EUC_PACE_CNT):
                sequence.append(0)

        new_notes = tuple()

        for i in range(EUC_PACE_HALF_CNT):
            sequence = []
            thistuple = self.euc_cfg[i]
            if thistuple[0] == 0:
                reset_sequence()
            else:
                sequence = self.bjorklund(thistuple[1], thistuple[2], thistuple[3])

            for j in range(len(sequence)):
                if sequence[j] == 1:
                    duration = 0.25
                    velocity = 127
                    if self.euc_len[j] == 1:
                        duration = 0.375
                    if self.euc_vel[j] == 1:
                        velocity = 63
                    nnote = ((self.pitches[i], float(j/4.0), duration, velocity, 0),)
                    new_notes = new_notes + nnote

        cl.replace_selected_notes(new_notes)

        return


    '''
    def euc_clear_set_note(self):
        for i in range(EUC_PACE_HALF_CNT):
            address = "/euc/euc_set_note/1/" + str(i+1)
            self.oscEndpoint.send(address, 0)
    '''

    def euc_len_set(self, button, pressed):
        if button < 1:
            return
        if button > EUC_PACE_CNT:
            return

        button = button - 1

        le = []
        for i in range(EUC_PACE_CNT):
            if i == button:
                val = int(pressed)
            else:
                val = self.euc_len[i]
            le.extend([val])
        self.euc_len = le
        self.euc_fill_clip()

        tid, cid = self.get_cur_tid_cid()
        self.euc_clip_update_cfg(tid, cid)

        return


    def euc_vel_set(self, button, pressed):
        if button < 1:
            return
        if button > EUC_PACE_CNT:
            return

        button = button - 1

        le = []
        for i in range(EUC_PACE_CNT):
            if i == button:
                val = int(pressed)
            else:
                val = self.euc_vel[i]
            le.extend([val])
        self.euc_vel = le
        self.euc_fill_clip()

        tid, cid = self.get_cur_tid_cid()
        self.euc_clip_update_cfg(tid, cid)

        return

    def euc_clr_cfg_len(self):
        le = []
        for i in range(EUC_PACE_CNT):
            le.extend([0])
        self.euc_len = le
        return

    def euc_clr_cfg_vel(self):
        le = []
        for i in range(EUC_PACE_CNT):
            le.extend([0])
        self.euc_vel = le
        return

    def euc_update_trsp_all_gui(self):
        x,y = self.euc_get_menu_coord(12)
        address = "/euc/euc_menu/" + str(y) + "/" + str(x)
        val = 0.0
        if self.euc_trsp_all == True:
            val = 1.0
        self.oscEndpoint.send(address, float(val))

    def euc_update_rand_mode_gui(self):
        x,y = self.euc_get_menu_coord(6)
        address = "/euc/euc_menu/" + str(y) + "/" + str(x)
        val = 0.0
        if self.euc_rand_mode == True:
            val = 1.0
        self.oscEndpoint.send(address, float(val))

    def euc_update_gui_full(self):
        self.euc_update_gui_note()
        self.euc_update_gui_sps(self.euc_cur_note)
        self.euc_update_gui_len()
        self.euc_update_gui_vel()
        self.euc_update_gui_play()
        self.euc_update_gui_trsp()
        self.euc_update_pitches()
        self.euc_update_status()
        self.euc_update_rand_mode_gui()
        self.euc_update_trsp_all_gui()
        self.euc_control_gui()
        self.euc_drive_gui() # euc_update_gui_full

    def euc_update_gui_note(self):

        if self.oscEndpoint.get_phone_osc() == False:
            self.oscEndpoint.send("/euc/label_cur_pitch", self.MidiToNote(self.pitches[self.euc_cur_note-1]))
            self.oscEndpoint.send("/euc/label_note_idx", str(self.euc_cur_note))
            address = "/euc/euc_note/1/" + str(self.euc_cur_note)
            self.oscEndpoint.send(address, 1.0)
        else:
            for i in range(8):
                address = "/euc/euc_drive/2/" + str(i+1)
                self.oscEndpoint.send(address, 0.0)
            address = "/euc/euc_drive/2/" + str(self.euc_cur_note)
            self.oscEndpoint.send(address, 1.0)

        for i in range (EUC_PACE_HALF_CNT):
            address = "/euc/epitch" + str(i+1) + "/color"
            self.oscEndpoint.send(address, "gray")
            self.send_midi_ex((0xB0, self.euc_midi_cur_note[i], 0), EUC_TAB)
        address = "/euc/epitch" + str(self.euc_cur_note) + "/color"
        self.oscEndpoint.send(address, "yellow")
        self.send_midi_ex((0xB0, self.euc_midi_cur_note[self.euc_cur_note-1], 127), EUC_TAB)


    def euc_update_gui_sps(self, note, midi_send = True):

        if note < 1:
            return

        if note > EUC_PACE_HALF_CNT:
            return

        thistuple = self.euc_cfg[note-1]

        if self.oscEndpoint.get_phone_osc() == False:

            self.oscEndpoint.send("/euc/label_steps_idx", str(thistuple[1]) )
            self.oscEndpoint.send("/euc/label_pulses_idx", str(thistuple[2]) )
            self.oscEndpoint.send("/euc/label_shift_idx", str(thistuple[3]) )

            for i in range(EUC_PACE_CNT):
                address = "/euc/euc_steps/1/" + str(i+1)
                self.oscEndpoint.send(address, 0)
                address = "/euc/euc_pulses/1/" + str(i+1)
                self.oscEndpoint.send(address, 0)
                address = "/euc/euc_shift/1/" + str(i+1)
                self.oscEndpoint.send(address, 0)

            address = "/euc/euc_steps/1/" + str(int(thistuple[1]))
            self.oscEndpoint.send(address, float(1.0))

            address = "/euc/euc_pulses/1/" + str(int(thistuple[2]))
            self.oscEndpoint.send(address, float(1.0))

            address = "/euc/euc_shift/1/" + str(1+int(thistuple[3]))
            self.oscEndpoint.send(address, float(1.0))

        else:
            self.oscEndpoint.send("/euc/label_phone_steps2", str(thistuple[1]) )
            self.oscEndpoint.send("/euc/label_phone_pulses2", str(thistuple[2]) )
            self.oscEndpoint.send("/euc/label_phone_shift2", str(thistuple[3]) )

        if midi_send == True:

            if self.lito_tab != EUC_TAB:
                return

            val = int(self.adaptValue(thistuple[1], 1, EUC_PACE_CNT, 0, 127))
            self.send_midi_ex((0xB0, const.MIDI_EUC_ENCODER1, val), EUC_TAB)
            val2 = int(self.adaptValue(thistuple[2], 1, EUC_PACE_CNT, 0, 127))
            self.send_midi_ex((0xB0, const.MIDI_EUC_ENCODER2, val2), EUC_TAB)
            val3 = int(self.adaptValue(thistuple[3], 0, EUC_PACE_CNT-1, 0, 127))
            self.send_midi_ex((0xB0, const.MIDI_EUC_ENCODER3, val3), EUC_TAB)


    def euc_update_gui_play(self):
        if len(self.euc_cfg) == EUC_PACE_HALF_CNT:
            for i in range(EUC_PACE_HALF_CNT):
                thistuple = self.euc_cfg[i]
                if self.oscEndpoint.get_phone_osc() == False:
                    address = "/euc/euc_play/1/" + str(i+1)
                else:
                    address = "/euc/euc_drive/1/" + str(i+1)
                self.oscEndpoint.send(address, thistuple[0])
                self.send_midi_ex((0xB0, self.euc_midi_plays[i], thistuple[0]*127), EUC_TAB)
        return

    def euc_update_gui_len(self, do_clear = False):
        if self.oscEndpoint.get_phone_osc() == False:
            block = []
            for i in range(EUC_PACE_CNT):
                if do_clear:
                    block.extend([0])
                else:
                    block.extend([self.euc_len[i]])
            self.oscEndpoint.send("/euc/euc_len", block)
        else:
            for i in range(EUC_PACE_CNT):
                if do_clear:
                    val = 0
                else:
                    val = self.euc_len[i]
                if i < 8:
                    address = "/euc/euc_drive/2/" + str(i+1)
                else:
                    address = "/euc/euc_drive/1/" + str(i+1-8)
                self.oscEndpoint.send(address, val)
        return

    def euc_update_gui_vel(self, do_clear = False):

        if self.oscEndpoint.get_phone_osc() == False:
            block = []
            for i in range(EUC_PACE_CNT):
                if do_clear:
                    block.extend([0])
                else:
                    block.extend([self.euc_vel[i]])
            self.oscEndpoint.send("/euc/euc_vel", block)
        else:
            for i in range(EUC_PACE_CNT):
                if do_clear:
                    val = 0
                else:
                    val = self.euc_vel[i]
                if i < 8:
                    address = "/euc/euc_drive/2/" + str(i+1)
                else:
                    address = "/euc/euc_drive/1/" + str(i+1-8)
                self.oscEndpoint.send(address, val)
        return


    def euc_update_gui_trsp(self):
        self.oscEndpoint.send("/euc/euc_trsp", str(self.euc_trsp))


    def euc_display_cfg(self):
        myslog("---------------------------") # #### PERMANENT

        j = 0
        for key, value in self.euc_clips_cfg.items():
            j = j + 1
            myslog("cfg: " + str(j) + ":" + str(len(self.euc_clips_cfg[key]))) # #### PERMANENT
            for i in range(len(self.euc_clips_cfg[key])):
                myslog(str(i) + " " + str(self.euc_clips_cfg[key][i])) # #### PERMANENT
        j = 0
        for key, value in self.euc_clips_len.items():
            j = j + 1
            myslog("len: " + str(j) + ":" + str(len(self.euc_clips_len[key]))) # #### PERMANENT
            for i in range(len(self.euc_clips_len[key])):
                myslog(str(i) + " " + str(self.euc_clips_len[key][i])) # #### PERMANENT
        j = 0
        for key, value in self.euc_clips_vel.items():
            j = j + 1
            myslog("vel: " + str(j) + ":" + str(len(self.euc_clips_vel[key]))) # #### PERMANENT
            for i in range(len(self.euc_clips_vel[key])):
                myslog(str(i) + " " + str(self.euc_clips_vel[key][i])) # #### PERMANENT

        j = 0
        for key, value in self.euc_clips_pitches.items():
            j = j + 1
            myslog("vel: " + str(j) + ":" + str(len(self.euc_clips_pitches[key]))) # #### PERMANENT
            for i in range(len(self.euc_clips_pitches[key])):
                myslog(str(i) + " " + str(self.euc_clips_pitches[key][i])) # #### PERMANENT

        return

    def euc_disp_play(self):
        address = "/euc/led_play"
        if self.song().is_playing:
            self.oscEndpoint.send(address, 1)
        else:
            self.oscEndpoint.send(address, 0)

    def euc_load_clip_cfg(self, tid, cid):
        if tid == -1:
            return
        if cid == -1:
            return

        tracks = self.song().tracks
        track = tracks[tid]
        if track == None:
            return

        css = track.clip_slots
        cs = css[cid]
        if cs == None:
            return

        cl = cs.clip
        if cl == None:
            return

        if self.euc_clips_cfg.has_key(cl) == True:
            loc_euc_cfg = []
            for i in range(EUC_PACE_HALF_CNT):
                loc_euc_cfg.append(self.euc_clips_cfg[cl][i])
            self.euc_cfg = loc_euc_cfg

        if self.euc_clips_len.has_key(cl) == True:
            le = []
            for i in range(EUC_PACE_CNT):
                val = self.euc_clips_len[cl][i]
                le.extend([val])
            self.euc_len = le

        if self.euc_clips_vel.has_key(cl) == True:
            ve = []
            for i in range(EUC_PACE_CNT):
                val = self.euc_clips_vel[cl][i]
                ve.extend([val])
                self.euc_vel = ve

        if self.euc_clips_trsp.has_key(cl) == True:
            val = self.euc_clips_trsp[cl]
            self.euc_trsp = val

        if self.euc_clips_pitches.has_key(cl) == True:
            pi = []
            for i in range(EUC_PACE_HALF_CNT):
                val = self.euc_clips_pitches[cl][i]
                pi.extend([val])
            self.pitches = pi

        return

    def euc_clip_create_cfg(self, clip):

        loc_euc_cfg = []
        for i in range(EUC_PACE_HALF_CNT):
            loc_euc_cfg.append(self.euc_cfg[i])
        self.euc_clips_cfg[clip] = loc_euc_cfg

        le = []
        for i in range(EUC_PACE_CNT):
            le.append(self.euc_len[i])
        self.euc_clips_len[clip] = le

        ve = []
        for i in range(EUC_PACE_CNT):
            ve.append(self.euc_vel[i])
        self.euc_clips_vel[clip] = ve

        self.euc_clips_trsp[clip] = self.euc_trsp

        pi = []
        for i in range(EUC_PACE_HALF_CNT):
            pi.append(self.pitches[i])
        self.euc_clips_pitches[clip] = pi

        return

    def clip_delete_cfgs(self):
        for key, value in self.euc_clips_cfg.items():
            del self.euc_clips_cfg[key]
        for key, value in self.euc_clips_len.items():
            del self.euc_clips_len[key]
        for key, value in self.euc_clips_vel.items():
            del self.euc_clips_vel[key]
        for key, value in self.euc_clips_trsp.items():
            del self.euc_clips_trsp[key]
        for key, value in self.euc_clips_pitches.items():
            del self.euc_clips_pitches[key]
        return

    def euc_clip_update_cfg(self, tid, cid):

        if tid != -1 and cid != -1:
            tracks = self.song().tracks
            track = tracks[tid]
            if track != None:
                css = track.clip_slots
                cs = css[cid]
                if cs != None:
                    cl = cs.clip
                    for key, value in self.euc_clips_cfg.items():
                        if key == cl:
                            self.euc_clip_create_cfg(key)

        return

#    ###############################################################################################
#    EUC PHONE TAB

    euc_possible_control = ["note/play", "len", "vel"]
    euc_phone_control = euc_possible_control[0]

    def euc_get_drive_coord(self, button):
        if button < 1:
            return 0,0

        if button > 16:
            return 0,0

        button = button - 1
        y = int(button / 8)
        x = button - y*8 + 1
        y = 2 - y

        return x,y

    def euc_drive_gui(self):

        if self.oscEndpoint.get_phone_osc() == True:

            list = []
            for j in range(1,3):
                for i in range(1,9):
                    address = "/euc/euc_drive/" + str(j) + "/" + str(i)
                    self.oscEndpoint.send(address, 0.0, True)

            if self.euc_phone_control == self.euc_possible_control[0]:
                address = "/euc/euc_drive/2/" + str(self.euc_cur_note)
                self.oscEndpoint.send(address, 1.0)
                self.euc_update_gui_play()
            elif self.euc_phone_control == self.euc_possible_control[1]:
                self.euc_update_gui_len()
            elif self.euc_phone_control == self.euc_possible_control[2]:
                self.euc_update_gui_vel()

        return

    def euc_get_control_coord(self, button):
        if button < 1:
            return 0,0

        if button > 12:
            return 0,0

        button = button - 1
        y = int(button / 3)
        x = button - y*3 + 1
        y = 4 - y

        return x,y


    def euc_control_gui(self):
        if self.oscEndpoint.get_phone_osc() == True:
            x,y = self.euc_get_control_coord(10)
            address_play = "/euc/euc_control/" + str(y) + "/" + str(x)
            x,y = self.euc_get_control_coord(11)
            address_len = "/euc/euc_control/" + str(y) + "/" + str(x)
            x,y = self.euc_get_control_coord(12)
            address_vel = "/euc/euc_control/" + str(y) + "/" + str(x)
            self.oscEndpoint.send(address_play, 0.0)
            self.oscEndpoint.send(address_len, 0.0)
            self.oscEndpoint.send(address_vel, 0.0)
            if self.euc_phone_control == self.euc_possible_control[0]:
                self.oscEndpoint.send(address_play, 1.0)
            elif self.euc_phone_control == self.euc_possible_control[1]:
                self.oscEndpoint.send(address_len, 1.0)
            elif self.euc_phone_control == self.euc_possible_control[2]:
                self.oscEndpoint.send(address_vel, 1.0)
            self.oscEndpoint.send("/euc/euc_drive_mode", str(self.euc_phone_control))

    def euc_drive(self, button, pressed):
        if self.euc_phone_control == self.euc_possible_control[0]:
            if button >= 1 and button <= 8:
                if pressed == 1:
                    self.euc_note(button)
            elif button >= 9 and button <= 16:
                self.euc_set_cfg(button-8, "play", int(pressed))
                self.euc_fill_clip()
            self.euc_drive_gui() # euc_drive
        elif self.euc_phone_control == self.euc_possible_control[1]:
            self.euc_len_set(button, int(pressed))
            self.euc_update_gui_len()
        elif self.euc_phone_control == self.euc_possible_control[2]:
            self.euc_vel_set(button, int(pressed))
            self.euc_update_gui_vel()


    def euc_control(self, button):
        if button == 1:
            self.euc_set_cfg2(self.euc_cur_note, "steps", -1)
            self.euc_fill_clip()
        elif button == 3:
            self.euc_set_cfg2(self.euc_cur_note, "steps", 1)
            self.euc_fill_clip()
        elif button == 4:
            self.euc_set_cfg2(self.euc_cur_note, "pulses", -1)
            self.euc_fill_clip()
        elif button == 6:
            self.euc_set_cfg2(self.euc_cur_note, "pulses", 1)
            self.euc_fill_clip()
        elif button == 7:
            self.euc_set_cfg2(self.euc_cur_note, "shift", -1)
            self.euc_fill_clip()
        elif button == 9:
            self.euc_set_cfg2(self.euc_cur_note, "shift", 1)
            self.euc_fill_clip()
        else:
            if button == 10:
                self.euc_phone_control = self.euc_possible_control[0]
            elif button == 11:
                self.euc_phone_control = self.euc_possible_control[1]
            elif button == 12:
                self.euc_phone_control = self.euc_possible_control[2]
            self.euc_control_gui()
            self.euc_drive_gui() # euc_control

        self.euc_update_gui_sps(self.euc_cur_note)
        return

    def euc_set_cfg2(self, note, mode, indec):
        if note < 1:
            return
        if note > EUC_PACE_HALF_CNT:
            return

        thistuple = self.euc_cfg[note-1]

        if mode == "steps":
            val = thistuple[1] + indec
            if val < 1:
                val = 1
            if val > EUC_PACE_CNT:
                val = EUC_PACE_CNT
            val2 = thistuple[2]
            val3 = thistuple[3]
            if val<val2:
                val2 = val
            if (val-1)<val3:
                val3 = val - 1
            thistuple = (thistuple[0], val, val2, val3)
        elif mode == "pulses":
            val = thistuple[2] + indec
            if val < 1:
                val = 1
            if val > EUC_PACE_CNT:
                val = EUC_PACE_CNT
            if val > thistuple[1]:
                val = thistuple[1]
            thistuple = (thistuple[0], thistuple[1], val, thistuple[3])
        elif mode == "shift":
            val = thistuple[3] + indec
            if val < 0:
                val = 0
            if val > (EUC_PACE_CNT-1):
                val = EUC_PACE_CNT-1
            if val > (thistuple[1]-1):
                val = thistuple[1]-1
            thistuple = (thistuple[0], thistuple[1], thistuple[2], val)

        self.euc_cfg[note-1] = thistuple
        tid, cid = self.get_cur_tid_cid()
        self.euc_clip_update_cfg(tid, cid)

        return



#    ###############################################################################################
#    ## END OF EUC TAB


#    ###############################################################################################
#    ##  LAD TAB

    lad_midi_encoders = [const.MIDI_LAD_ENCODER1, const.MIDI_LAD_ENCODER2, const.MIDI_LAD_ENCODER3, const.MIDI_LAD_ENCODER4, const.MIDI_LAD_ENCODER5, const.MIDI_LAD_ENCODER6, const.MIDI_LAD_ENCODER7, const.MIDI_LAD_ENCODER8]
    lad_midi_presets = [const.MIDI_LAD_PRESET1, const.MIDI_LAD_PRESET2, const.MIDI_LAD_PRESET3, const.MIDI_LAD_PRESET4, const.MIDI_LAD_PRESET5, const.MIDI_LAD_PRESET6]
    lad_midi_buttons = [
    const.MIDI_LAD_LOWER_FADER, const.MIDI_LAD_MIXER_INFO, const.MIDI_LAD_ARM, const.MIDI_LAD_OVD,
    const.MIDI_LAD_RAND, const.MIDI_LAD_TRACK_PLUS, const.MIDI_LAD_DEVICE_PLUS, const.MIDI_LAD_PAGE_PLUS,
    const.MIDI_LAD_SHOW, const.MIDI_LAD_SET_RESET, const.MIDI_LAD_PERF, const.MIDI_LAD_REC,
    const.MIDI_LAD_MORPH, const.MIDI_LAD_TRACK_MINUS, const.MIDI_LAD_DEVICE_MINUS, const.MIDI_LAD_PAGE_MINUS
    ]

    xtouch_lower_encoder = False

    def lad_init(self):

        self.xtouch_lower_encoder = False
        self.util_update_lower_gui() # lad_init

        self.lad_init_preset()

        self.lad_clear_tr_dv_pg_cu(True,True,True,True)
        self.lad_current_group = 0
        self.lad_group_gui()

        self.lad_perf_mode = False
        self.touch_send_midi_info(2, self.lad_perf_mode)
        self.lad_reset_mode = False
        self.lad_reset_mode_gui()
        self.lad_label_info_mode = 0
        self.lad_device_page = 0
        for g in range(GROUP_CNT):
            self.lad_perf_page[g] = 0 #init

        self.lad_called_preset = -1
        self.lad_preset_rec_active = False
        self.lad_preset_rec_gui()
        self.lad_morph = False
        self.lad_morph_prep = 0
        self.lad_preset_morph_gui()

        self.lad_mixer = False
        self.touch_send_midi_info(1, self.lad_mixer)
        self.lad_mixer_mode = 0
        self.lad_set_mixer_gui() # lad_init
        self.lad_show_currents() # lad_init

        self.lad_faderm1_val = 0.0
        self.lad_faderm2_val = 0.0
        for g in range(GROUP_CNT):
            self.lad_perf_reset_mfader(g) # lad_init
            self.lad_perf_active_mfader(g) # lad_init

        self.lad_show_display = False
        self.lad_update_show_gui()

        self.touch_send_midi_info(0, False)
        self.touch_send_midi_info(1, False)
        self.touch_send_midi_info(2, False)
        self.touch_send_midi_info(3, False)
        self.touch_send_midi_info(4, False)
        self.touch_send_midi_info(5, False)


        self.lad_disp_play()

        return

    def lad_exit(self):
        self.lad_current_group = 0
        self.lad_group_gui()

        self.lad_mixer = False
        self.touch_send_midi_info(1, self.lad_mixer)
        self.lad_label_info_mode = 0
        self.lad_set_mixer_gui() # exit
        self.lad_perf_mode = False
        self.touch_send_midi_info(2, self.lad_perf_mode)
        self.lad_display_basic_perf_button()
        self.lad_reset_mode = False
        self.lad_reset_mode_gui()
        self.lad_clear_tr_dv_pg_cu(True,True,True,True)
        self.lad_called_preset = -1
        self.lad_preset_rec_active = False
        self.lad_preset_rec_gui()
        self.lad_morph = False
        self.lad_morph_prep = 0
        self.lad_preset_morph_gui()

        for i in range(self.FADER_CNT):
            self.lad_update_fader_param(None, i+1) # exit

        for g in range(GROUP_CNT):
            if len(self.lad_matrix_morph_presets) == GROUP_CNT:
                self.lad_matrix_morph_presets[g][0] = -1
                self.lad_matrix_morph_presets[g][1] = -1
            self.lad_perf_reset_mfader(g) # lad exit
            self.lad_perf_active_mfader(g)  # lad exit

        self.lad_show_display = False
        self.lad_update_show_gui()

        self.xtouch_lower_encoder = False
        self.util_update_lower_gui() # lad_exit

        self.touch_send_midi_info(0, False)
        self.touch_send_midi_info(1, False)
        self.touch_send_midi_info(2, False)
        self.touch_send_midi_info(3, False)
        self.touch_send_midi_info(4, False)
        self.touch_send_midi_info(5, False)

        self.lad_set_info("")

        return

#    ## LAD CB ################################################################################################
    def lad_init_cb(self):
        self.oscEndpoint.callbackManager.group_add("/lad/menu", self.lad_menu_cb)
        self.oscEndpoint.callbackManager.group_add("/lad/faderd", self.lad_faderd_cb)
        self.oscEndpoint.callbackManager.group_add("/lad/faderm", self.lad_faderm_cb)
        self.oscEndpoint.callbackManager.add("/lad/cfg", self.lad_cfg_cb)
        self.oscEndpoint.callbackManager.group_add("/lad/toggled", self.lad_toggled_cb)
        return

    def lad_cfg_cb(self, msg, source):
        self.lad_clear_registered_obj(self.lad_current_group)
        self.lad_set_info("")
        self.lad_load_param_cfg(self.lad_current_group, msg[2])
        self.lad_save_param_cfg() # load cb
        self.lad_export_cfg() # load cb
        self.lad_show_currents() # load cb
        return


    def lad_menu_cb(self, msg, source):
        pressed = msg[2]
        if pressed != 0:
            return
        button = -1
        address = msg[0]
        addresses = address.split("/")
        if len(addresses) == 5:
            button = int(addresses[4])
            y = int(addresses[3])
            x = int(addresses[4])
            button = (3-y)*8 + x

        if button != -1:
            self.lad_menu(button)
        return

    def lad_toggled_cb(self, msg, source):

        button = 0
        root_add = "/lad/toggled"
        le = len(root_add)
        address = str(msg[0])

        text = address[le:]
        button = int(text)
        val = msg[2]

        if button != 0:
            self.lad_toggle_buttond(button-1)

        return

    def lad_faderd_cb(self, msg, source):
        fader = 0
        root_add = "/lad/faderd"
        le = len(root_add)
        address = str(msg[0])

        text = address[le:]
        fader = int(text)
        val = msg[2]

        if fader != 0:
            self.lad_fader_input(fader, val, False)
        return

    def lad_faderm_cb(self, msg, source):

        fader = 0
        root_add = "/lad/faderm"
        le = len(root_add)
        address = str(msg[0])

        text = address[le:]
        fader = int(text)
        val = msg[2]

        if fader != 0:
            self.lad_faderm_input(fader, val)
        return


#    ## MENU ################################################################################################
    def lad_menu(self, button):
        self.lad_menu_ex(button)

    def lad_menu_ex(self, button):
        if button == 1:
            if self.lad_perf_mode == False:
                self.lad_set_all()
            else:
                if self.lad_preset_rec_active == False:
                    if self.lad_morph == False:
                        if self.lad_reset_mode == False:
                            self.lad_called_preset = -1
                            self.lad_clear_registered_obj(self.lad_current_group)
            self.lad_show_currents() # Button 1

        elif button == 2: # mixer
            self.lad_handle_mixer_button()

        elif button == 3:
            tid = self.get_working_midi_track()
            if tid != -1:
                LiveUtils.toggleArmTrack(tid)

        elif button == 4:
            LiveUtils.getSong().overdub = not LiveUtils.getSong().overdub

        elif button == 5:
            do_it = False
            if self.lad_perf_mode == True:
                if self.lad_preset_rec_active == False:
                    if self.lad_morph == False:
                        if self.lad_reset_mode == False:
                            do_it = True
            else:
                do_it = True

            if do_it == True:
                self.lad_rand()

        elif button == 6:
            if self.lad_perf_mode == False:
                self.lad_change_track(1)

        elif button == 7:
            if self.lad_perf_mode == False:
                self.lad_change_device(1)

        elif button == 8:
            self.lad_change_page(1)

        elif button == 9:
            self.lad_show_display = not self.lad_show_display
            self.lad_update_show_gui()

        elif button == 10: # button SET/RESET
            if self.lad_perf_mode == False:
                self.lad_register_obj(self.lad_current_group, True)
            else:
                if self.lad_preset_rec_active == False:
                    if self.lad_morph == False:
                        self.lad_set_info("")
                        self.lad_called_preset = -1
                        self.lad_reset_mode = not self.lad_reset_mode
                        g = self.lad_current_group
                        if self.lad_reset_mode == True:
                            self.lad_buttonds_state = []
                            for i in range(len(self.lad_matrix_registers_objs[g])):
                                self.lad_buttonds_state.append(False)

                            for i in range(self.FADER_CNT):
                                self.lad_preset_toggle_param_button(i)
                        else:
                            param_to_del = []
                            for i in range(len(self.lad_buttonds_state)):
                                if self.lad_buttonds_state[i] == True:
                                    if i < len(self.lad_matrix_registers_objs[g]):
                                        param = self.lad_matrix_registers_objs[g][i]
                                        if param != None:
                                            param_to_del.append(param)
                            occ = 0
                            for param in param_to_del:
                                self.lad_saved_obj = param
                                done = self.lad_unregister_obj()
                                if done == True:
                                    occ += 1
                            param_to_del = []
                            self.lad_set_info("")
                            self.lad_set_info("removed: " + str(occ) + " param(s)")

                            self.lad_buttonds_state = []
                            self.lad_show_currents() # lad_unregister_obj
                        self.lad_reset_mode_gui()

        elif button == 11: # button BASIC/PERF
            self.lad_perf_mode = not self.lad_perf_mode
            self.touch_send_midi_info(2, self.lad_perf_mode)
            self.lad_switch_perf_mode()
            if self.lad_perf_mode == False:
                self.lad_label_info_mode = 0
                self.lad_set_mixer_gui() # switch perf
            self.lad_show_currents() # switch perf

        elif button == 12: # button REC
            if self.lad_perf_mode == True:
                if self.lad_reset_mode == False:
                    if self.lad_morph == False:
                        self.lad_called_preset = -1
                        self.lad_preset_rec_active = not self.lad_preset_rec_active
                        self.lad_preset_rec_gui()
                        self.lad_buttonds_state = []
                        if self.lad_preset_rec_active == True:
                            g = self.lad_current_group
                            for i in range(len(self.lad_matrix_registers_objs[g])):
                                self.lad_buttonds_state.append(True)

                            for i in range(self.FADER_CNT):
                                self.lad_preset_toggle_param_button(i)
                        self.lad_show_currents() # button REC

        elif button == 13: # button MORPH
            if self.lad_perf_mode == True:
                if self.lad_reset_mode == False:
                    if self.lad_preset_rec_active == False:
                        self.lad_morph_fct()
                        self.lad_show_currents() # button MORPH

        elif button == 14:
            if self.lad_perf_mode == False:
                self.lad_change_track(0)
            else:
                if self.lad_preset_rec_active == True or self.lad_reset_mode == True:
                    self.lad_preset_set_all_params()

        elif button == 15:
            if self.lad_perf_mode == False:
                self.lad_change_device(0)
            else:
                if self.lad_preset_rec_active == True or self.lad_reset_mode == True:
                    self.lad_preset_invert_params()

        elif button == 16:
            self.lad_change_page(0)

        elif button == 17 or button == 18: #lad_menu group
            do_it = False
            if self.lad_perf_mode == True:
                if self.lad_reset_mode == False:
                    if self.lad_preset_rec_active == False:
                        if self.lad_morph == False:
                            do_it = True
            else:
                do_it = True

            if do_it == True:
                self.lad_current_group = button - 16 - 1
                self.lad_perf_page[self.lad_current_group] = 0 #lad_menu group
                self.lad_group_gui()
                self.lad_show_currents() # lad_menu group
                for i in range(PRESET_CNT):
                    self.lad_populate_label_preset(i)

        else: # presets
            self.lad_handle_preset_button(button)

        return

    def lad_handle_mixer_button(self):

        if self.lad_perf_mode == False:
            self.lad_mixer = not self.lad_mixer
            self.touch_send_midi_info(1, self.lad_mixer)
            self.lad_set_mixer_gui() # switch mixer
            self.lad_show_currents() # switch mixer
            self.lad_clear_saved_obj()
        else:
            self.lad_label_info_mode = self.lad_label_info_mode + 1
            if self.lad_label_info_mode == 3:
                self.lad_label_info_mode = 0
            self.lad_show_currents() # update lad_label_info_mode



    def lad_handle_preset_button(self, button):

        if self.lad_perf_mode == True:

            if self.lad_reset_mode == True:
                return

            self.lad_clear_saved_obj()

            preset = button - 19

            if self.lad_morph == True:
                self.lad_morph_prep = self.lad_morph_prep + 1
                if self.lad_morph_prep == 1:
                    self.lad_matrix_morph_presets[self.lad_current_group][0] = preset
                    self.lad_set_current("morph presets " + str(self.lad_matrix_morph_presets[self.lad_current_group][0]+1)+ ":X")
                    pass
                elif self.lad_morph_prep == 2:
                    self.lad_matrix_morph_presets[self.lad_current_group][1] = preset
                    self.lad_set_current("morph presets " + str(self.lad_matrix_morph_presets[self.lad_current_group][0]+1) + ":" + str(self.lad_matrix_morph_presets[self.lad_current_group][1]+1))
                    self.lad_morph_prep = 0
                    self.lad_perf_active_mfader(self.lad_current_group)
                    self.lad_perf_reset_mfader(self.lad_current_group) # preset button

                    self.lad_morph = False
                    self.lad_preset_morph_gui()

            elif self.lad_preset_rec_active == True:
                self.lad_preset_rec_values(preset)
                self.lad_preset_rec_active = False
                self.lad_preset_rec_gui()
                self.lad_show_currents() # rec finish

            else:
                self.lad_preset_recall(preset)

        return

#    ## NAVIGATION ################################################################################################
    lad_device_page = 0
    lad_show_display = False
    lad_perf_page = [0,0]

    def lad_change_track(self, mode):

        if self.lad_perf_mode == True:
            return

        self.lad_clear_saved_obj()
		
        if self.lad_mixer == False:

            current_track = self.song().view.selected_track
            if(current_track == None):
                return

            id = self.tuple_idx(self.all_tracks, current_track)
            if mode == 0:
                if id > 0:
                    id = id - 1
                    LiveUtils.getSong().view.selected_track = self.all_tracks[id]
            else:
                if id < len(self.all_tracks) - 1:
                    id = id + 1
                    LiveUtils.getSong().view.selected_track = self.all_tracks[id]
        else:

            if mode == 0:
                if self.lad_mixer_page > 0:
                    self.lad_mixer_page = self.lad_mixer_page - 1
            else:
                if self.lad_mixer_page < len(self.all_tracks) - 1:
                    self.lad_mixer_page = self.lad_mixer_page + 1
            self.lad_update_faders_mixer()

        return

    def lad_change_device(self, mode):

        if self.lad_perf_mode == True:
            return

        self.lad_clear_saved_obj()

        if self.lad_perf_mode == True:
            return

        if self.lad_mixer == False:
            current_track = self.song().view.selected_track
            if(current_track == None):
                return

            devices = current_track.devices
            if len(devices) == 0:
                return

            device = current_track.view.selected_device
            if device == None:
                device = current_track.devices[0]
                LiveUtils.getSong().view.select_device(device)
            else:
                id = self.tuple_idx(devices, device)
                if mode == 0:
                    if id > 0:
                        id = id - 1
                        device = current_track.devices[id]
                        LiveUtils.getSong().view.select_device(device)
                else:
                    if id < len(devices) - 1:
                        id = id + 1
                        device = current_track.devices[id]
                        LiveUtils.getSong().view.select_device(device)
        else:
            if mode == 0:
                if self.lad_mixer_mode > 0:
                    self.lad_mixer_mode = self.lad_mixer_mode - 1
            else:
                mixer_device_count = 2 + self.sends_count # volume, pan, sends
                if self.lad_mixer_mode < mixer_device_count - 1:
                    self.lad_mixer_mode = self.lad_mixer_mode + 1
            self.lad_update_faders_mixer()
            self.lad_update_mixer_devices()
        return

    def lad_get_perf_pages_count(self, group):
        if len(self.lad_matrix_registers_objs) != GROUP_CNT:
            return
        max_pages = len(self.lad_matrix_registers_objs[group]) / self.FADER_CNT
        if len(self.lad_matrix_registers_objs[group]) % self.FADER_CNT:
            max_pages = max_pages + 1

        return max_pages


    def lad_get_pages_count(self, device):
        max_pages = len(device.parameters) / self.FADER_CNT
        if len(device.parameters) % self.FADER_CNT:
            max_pages = max_pages + 1

        return max_pages

    def lad_change_page(self, mode):

        self.lad_clear_saved_obj()

        if self.lad_perf_mode == False:

            current_track = self.song().view.selected_track
            if(current_track == None):
                return

            devices = current_track.devices
            if len(devices) == 0:
                return

            device = current_track.view.selected_device
            if device == None:
                return

            max_pages = self.lad_get_pages_count(device)

            if mode == 0:
                if self.lad_device_page > 0:
                    self.lad_device_page = self.lad_device_page - 1
            else:
                if self.lad_device_page < max_pages - 1:
                    self.lad_device_page = self.lad_device_page + 1
        else:

            max_pages = self.lad_get_perf_pages_count(self.lad_current_group)

            if mode == 0:
                if self.lad_perf_page[self.lad_current_group] > 0:
                    self.lad_perf_page[self.lad_current_group] = self.lad_perf_page[self.lad_current_group] - 1
            else:
                if self.lad_perf_page[self.lad_current_group] < max_pages - 1:
                    self.lad_perf_page[self.lad_current_group] = self.lad_perf_page[self.lad_current_group] + 1


        self.lad_show_currents() # lad_change_page

        return

#    ## MIXER ################################################################################################

    lad_mixer = False
    lad_mixer_page = 0
    lad_mixer_mode = 0

    def lad_update_faders_mixer(self):
        if self.lad_mixer == False:
            return

        for i in range(self.FADER_CNT):
            tid = i + self.lad_mixer_page
            if tid < len(self.all_tracks):
                track = self.all_tracks[tid]
                param,name = self.lad_get_mixer_fader_settings(track)
                self.lad_update_fader_param(param, i+1) # mixer 1

                labelb = generate_strip_string(track.name)
                address_labelb = "/lad/labelfd" + str(i+1) + "b"
                self.oscEndpoint.send(address_labelb, str(labelb))

            else:
                self.lad_update_fader_param(None, i+1) # mixer 2

        return

    def lad_get_mixer_fader_settings(self, track):
        name = ""
        if track == None:
            return None,name
        if self.lad_mixer_mode == 0:
            param = track.mixer_device.volume
            name = "Volume"
        elif self.lad_mixer_mode == 1:
            param = track.mixer_device.panning
            name = "Pan"
        else :
            if(track == self.song().master_track):
                param = None
            else:
                param = track.mixer_device.sends[self.lad_mixer_mode-2]
        return param,name


    def lad_fader_mixer_input(self, fader, value, relative):
        # get track
        tid = self.lad_mixer_page + fader - 1
        if tid < len(self.all_tracks):
            track = self.all_tracks[tid]
            text = ""
            text2 = ""
            if track != None:
                wio_dname = "Mixer"
                if self.lad_mixer_mode == 0:
                    param = track.mixer_device.volume
                    if relative == False:
                        param.value = self.adaptValue(value, 0.0, 1.0, param.min, param.max)
                    else:
                        self.lad_get_param_relative_value(param, value)
                    text = str(track.name) + " Mixer" + " Volume"
                    wio_pname = "Volume"

                    text2 = str(track.mixer_device.volume)
                    self.lad_saved_obj = track.mixer_device.volume
                elif self.lad_mixer_mode == 1:
                    text =str(track.name) + " Mixer" + " Panning"
                    wio_pname = "Panning"

                    param = track.mixer_device.panning
                    if relative == False:
                        param.value = self.adaptValue(value, 0.0, 1.0, param.min, param.max)
                    else:
                        self.lad_get_param_relative_value(param, value)

                    text2 = str(track.mixer_device.panning)
                    self.lad_saved_obj = track.mixer_device.panning
                else:
                    if track != self.song().master_track:
                        idx = self.lad_mixer_mode-2
                        IDS = str(idx)
                        if idx < len(self.LETTERS):
                            IDS = self.LETTERS[idx]

                        text = str(track.name) + " Mixer" + " Send-" + IDS
                        wio_pname = "Send-" + IDS
                        param = track.mixer_device.sends[self.lad_mixer_mode-2]
                        if relative == False:
                            param.value = self.adaptValue(value, 0.0, 1.0, param.min, param.max)
                        else:
                            self.lad_get_param_relative_value(param, value)

                        text2 = str(track.mixer_device.sends[self.lad_mixer_mode-2])
                        self.lad_saved_obj = track.mixer_device.sends[self.lad_mixer_mode-2]


            self.lad_set_current(text, text2) #lad_fader_mixer_input
            self.wio_send_track_name(str(track.name))
            self.wio_send_device_name(wio_dname)
            self.wio_send_param_name(wio_pname)
            self.wio_send_param_val(text2)

        return

    def lad_get_match_mixer(self, track, type):

        param = None

        if track == None:
            return

        if self.lad_perf_mode == False:
            if self.lad_mixer == False:
                return

            fader = -1
            idx = self.tuple_idx(self.all_tracks,track)
            fader = idx - self.lad_mixer_page + 1

            if fader != -1:
                param,name = self.lad_get_mixer_fader_settings(track)
                self.lad_update_fader_param(param, fader) # match mixer basic

                labelb = generate_strip_string(track.name)
                address_labelb = "/lad/labelfd" + str(fader) + "b"
                self.oscEndpoint.send(address_labelb, str(labelb))


        else:


            # get param
            if type == 0:
                param = track.mixer_device.volume
            elif type == 1:
                param = track.mixer_device.panning
            else:
                param = track.mixer_device.sends[type-2]

            if param != None:
                if len(self.lad_matrix_registers_objs) != GROUP_CNT:
                    return

                idx = self.tuple_idx(self.lad_matrix_registers_objs[self.lad_current_group], param)
                if idx != -1:
                    perf_page = int(idx / self.FADER_CNT)
                    if perf_page == self.lad_perf_page[self.lad_current_group]:
                        fd = idx - (self.lad_perf_page[self.lad_current_group] * self.FADER_CNT)
                        self.lad_update_fader_param(param, fd + 1) # match mixer perf

                        if self.lad_reset_mode == True:
                            if idx < len(self.lad_buttonds_state):
                                self.lad_buttonds_state[idx] = True
                                self.lad_preset_toggle_param_button(fd)

        if self.lad_show_display == True and self.lad_reset_mode == False:
            self.lad_show_display = False
            self.lad_update_show_gui()
            self.lad_saved_obj = param



#    ## FADERS ###########################################################################################

    lad_fader_vals = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    lad_fader_params = []
    lad_saved_obj = None


    def lad_get_param_relative_value(self, param, value):


        self.lad_log_device_param(param)

        if value < 0:
            if param.value == param.min:
                return

        if value > 0:
            if param.value == param.max:
                return

        if param.is_quantized == True:
            end_value = param.value
            if value > 0:
                end_value += 1
            else:
                end_value -= 1
        else:

            str_init = param.str_for_value(param.value)
            init_value = self.adaptValue(param.value, param.min, param.max, 0, 1.0)


            f_end_value = init_value + value
            out = 0
            occ = 0
            while out != 1:

                end_value = self.adaptValue(f_end_value, 0, 1.0, param.min, param.max)
                str_end = param.str_for_value(end_value)

                if str_end == str_init:
                    f_end_value += value
                else:
                    out = 0
                    break

                occ += 1

                if (occ >= 100) :
                    end_value = param.value
                    out = 1
                    break

        if end_value < param.min:
            end_value = param.min
        elif end_value > param.max:
            end_value = param.max

        param.value = end_value

#    ## GET FROM FADERS ########################
    def lad_fader_input(self, fader, val, relative):
        if self.lad_perf_mode == False:
            if self.lad_mixer == False:
                self.lad_faderd_basic_input(fader, val, relative)
            else:
                self.lad_fader_mixer_input(fader, val, relative)

        else:
            self.lad_fader_perf_input(fader, val, relative)
        return


    def lad_faderd_basic_input(self, fader, value, relative):

        track = LiveUtils.getSong().view.selected_track
        if track == None:
            return

        device = LiveUtils.getSong().view.selected_track.view.selected_device
        if device == None:
            return

        if (fader <= len(self.lad_fader_params)) and (self.lad_fader_params[fader-1] != None):
            param = self.lad_fader_params[fader-1]
            if relative == False:
                if param.is_quantized == True:
                    param.value = self.adaptValue(value, 0.0, 1.0, param.min, param.max, len(param.value_items)-1)
                else:
                    param.value = self.adaptValue(value, 0.0, 1.0, param.min, param.max)
            else:
                self.lad_get_param_relative_value(param, value)

            self.lad_saved_obj = param # fader input basic
            dname = ""
            tname = ""
            device = param.canonical_parent
            if device != None:
                track = device.canonical_parent
                if track != None:
                    tname = str(track.name) + " "
                    if isinstance(device, Live.MixerDevice.MixerDevice):
                        dname = "Mixer "
                    else:
                        dname = str(device.name) + " "

            text = tname + dname + str(param.name)
            text2 = str(param.str_for_value(param.value))
            self.lad_set_current(text, text2) #lad_faderd_basic_input

            self.wio_send_track_name(tname)
            self.wio_send_device_name(dname)
            self.wio_send_param_name(str(param.name))
            self.wio_send_param_val(text2)
        return

    def lad_fader_perf_input(self, fader, value, relative):

        if len(self.lad_matrix_registers_objs) != GROUP_CNT:
            return

        fader = fader - 1
        fader = (self.lad_perf_page[self.lad_current_group] * self.FADER_CNT) + fader

        if fader < len(self.lad_matrix_registers_objs[self.lad_current_group]):
            param = self.lad_matrix_registers_objs[self.lad_current_group][fader]
            if param == None:
                return
            if relative == False:
                if param.is_quantized == True:
                    param.value = self.adaptValue(value, 0.0, 1.0, param.min, param.max, len(param.value_items)-1)
                else:
                    param.value = self.adaptValue(value, 0.0, 1.0, param.min, param.max)
            else:
                self.lad_get_param_relative_value(param, value)

            self.lad_saved_obj = param # fader input perf
            dname = ""
            tname = ""
            device = param.canonical_parent
            if device != None:
                track = device.canonical_parent
                if track != None:
                    tname = str(track.name) + " "
                    if isinstance(device, Live.MixerDevice.MixerDevice):
                        dname = "Mixer "
                    else:
                        dname = str(device.name) + " "

            text = tname + dname + str(param.name)
            text2 = str(param.str_for_value(param.value))
            self.lad_set_current(text, text2) #lad_fader_perf_input
            self.wio_send_track_name(tname)
            self.wio_send_device_name(dname)
            self.wio_send_param_name(str(param.name))
            self.wio_send_param_val(text2)

        return

#    ## SET TO FADERS ########################

    def lad_update_faders(self):
        if self.lad_perf_mode == False:
            if self.lad_mixer:
                self.lad_update_faders_mixer()
            else:
                self.lad_update_faders_device()
        else:
            self.lad_update_faders_perf()


    def lad_update_fader_param(self, param, fader, name=""):

        address_label = "/lad/labelfd" + str(fader)
        address_fader = "/lad/faderd" + str(fader)
        address_labelb = "/lad/labelfd" + str(fader) + "b"
        address_color = "/lad/faderd" + str(fader) + "/color"
        color = "gray"
        fd = -1
        if param == None:
            label = "--"
            labelb = "--"
            value = 0.0
        else:
            value = self.adaptValue(param.value, param.min, param.max, 0.0, 1.0)
            label = generate_strip_string(param.str_for_value(param.value))
            if len(name) == 0:
                name = generate_strip_string(self.lad_update_label_name(param))
            labelb = name

            if self.lad_perf_mode == False:
                if len(self.lad_matrix_registers_objs) == GROUP_CNT:
                    idx = self.tuple_idx(self.lad_matrix_registers_objs[self.lad_current_group], param)
                    if idx != -1:
                        color = lad_hl_color2
            else:
                if self.lad_called_preset != -1:
                    if self.lad_current_group >= 0:
                        if self.lad_current_group < GROUP_CNT:
                            g = self.lad_current_group
                            p = self.lad_called_preset
                            if len(self.lad_matrix_registers_objs[g]) != 0:
                                if param in self.lad_matrix_registers_objs[g]:
                                    idx = self.lad_matrix_registers_objs[g].index(param)
                                    if self.lad_matrix_presets_valid[g][p][idx] == True:
                                        color = lad_hl_color2

        self.oscEndpoint.send(address_label, str(label))
        self.oscEndpoint.send(address_fader, value)
        self.oscEndpoint.send(address_labelb, str(labelb))
        self.oscEndpoint.send(address_color, color)

        address_label = address_label + "/color"
        address_labelb = address_labelb + "/color"

        if self.lad_preset_rec_active == True or self.lad_reset_mode == True:
            self.lad_preset_toggle_param_button(fader - 1)

        if self.xtouch_lower_encoder == False:
            if fader < 9:
                midi_val = self.adaptValue(value, 0, 1.0, 0, float(127))
                cc = self.lad_midi_encoders[fader-1]
                self.send_midi_ex( (0xB0, cc, int(midi_val)), UTIL_TAB | LAD_TAB | MORPH_TAB)
                self.oscEndpoint.send(address_label, lad_hl_color)
                self.oscEndpoint.send(address_labelb, lad_hl_color)
                self.util_update_phone_label(fader, labelb)
            else:
                self.oscEndpoint.send(address_label, "gray")
                self.oscEndpoint.send(address_labelb, "gray")
        else:
            if fader >= 9:
                midi_val = self.adaptValue(value, 0, 1.0, 0, float(127))
                cc = self.lad_midi_encoders[fader-9]
                self.send_midi_ex((0xB0, cc, int(midi_val)), UTIL_TAB | LAD_TAB | MORPH_TAB)
                self.oscEndpoint.send(address_label, lad_hl_color)
                self.oscEndpoint.send(address_labelb, lad_hl_color)
                self.util_update_phone_label(fader-8, labelb)
            else:
                self.oscEndpoint.send(address_label, "gray")
                self.oscEndpoint.send(address_labelb, "gray")

        return

    def lad_update_faders_device(self):
        if self.lad_mixer == True:
            return

        track = LiveUtils.getSong().view.selected_track
        if track == None:
            return

        device = LiveUtils.getSong().view.selected_track.view.selected_device
        self.lad_fader_params = []

        if device == None:
            for i in range(self.FADER_CNT):
                self.lad_update_fader_param(None, i+1) # device 1
        else:
            _params = device.parameters
            params = []

            if self.dev_pref_dict.has_key(device.class_display_name) == False:
                occ = 0
                for p in _params:
                    if occ != 0:
                        params.append(p)
                    occ += 1
                params.append(_params[0])
            else:
                for n in self.dev_pref_dict[device.class_display_name]:
                    for p in _params:
                        if p.name == n:
                            params.append(p)
                occ = 0
                for p in _params:
                    if occ != 0:
                        idx = self.tuple_idx(params, p)
                        if idx == -1:
                            params.append(p)
                    occ += 1
                params.append(_params[0])


            for i in range(self.FADER_CNT):
#                p = (self.lad_device_page * self.FADER_CNT) + i + 1 # + 1 => skip device on
                p = (self.lad_device_page * self.FADER_CNT) + i
                if p >= len(params):
                    self.lad_update_fader_param(None, i+1) # device 2
                else:
                    self.lad_fader_params.append(params[p])
                    self.lad_update_fader_param(params[p], i+1) # device 3


        return

    def lad_show_select_tr_dv(self, param):

        if self.lad_show_display == True:
            self.lad_show_display = False
            self.lad_update_show_gui()
            self.lad_saved_obj = param

            obj = param.canonical_parent
            if obj != None:
                device = obj
                obj = device.canonical_parent
                if obj != None:
                    track = obj
                    self.song().view.selected_track = track
                    LiveUtils.getSong().view.select_device(device)

                    fader = -1
                    if self.lad_perf_mode == False:
                        idx = self.tuple_idx(device.parameters, param)
                        if idx != -1:
                            self.lad_device_page = int(idx / self.FADER_CNT)
                            fader = idx - self.lad_device_page*self.FADER_CNT
                    else:
                        idx = self.tuple_idx(self.lad_matrix_registers_objs[self.lad_current_group], param) # to be tested
                        if idx != -1:
                            self.lad_perf_page[self.lad_current_group] = int(idx / self.FADER_CNT)
                            fader = idx - self.lad_perf_page[self.lad_current_group]*self.FADER_CNT

                    if fader != -1:
                        if fader < 9:
                            self.xtouch_lower_encoder = False
                        else:
                            self.xtouch_lower_encoder = True
                        self.lad_show_currents() # lad_show_select_tr_dv

    def lad_get_match_fader(self, param):

        fader = -1
        if param == None:
            return

        self.lad_log_device_param(param)

        if self.lad_perf_mode == False:
            if self.lad_mixer == True:
                return

            self.lad_show_select_tr_dv(param)

            fader = self.tuple_idx(self.lad_fader_params, param)
            if fader != -1:
                self.lad_update_fader_param(param, fader+1) # match fader basic
        else:

            if self.lad_show_display == True and self.lad_reset_mode == False:
                self.lad_show_select_tr_dv(param)

            fader = -1
            idx = self.tuple_idx(self.lad_matrix_registers_objs[self.lad_current_group], param)

            if idx != -1:
                page = int(idx / self.FADER_CNT)
                if page == self.lad_perf_page[self.lad_current_group]:
                    fader = idx - page*self.FADER_CNT


            if fader != -1:
                self.lad_update_fader_param(param, fader+1) # match fader perf

                if self.lad_reset_mode == True:
                    if idx < len(self.lad_buttonds_state):
                        self.lad_buttonds_state[idx] = True
                        self.lad_preset_toggle_param_button(fader)


#    ## SET/RESET ################################################################################################

    def lad_clear_saved_obj(self):
        self.lad_saved_obj = None
        self.lad_clear_tr_dv_pg_cu(False, False, False,True)


    def lad_register_obj(self, group, save_cfg):

        if len(self.lad_matrix_registers_objs) != GROUP_CNT:
            return


        free_place = -1

        if self.lad_saved_obj != None:
            if (self.lad_saved_obj in self.lad_matrix_registers_objs[group]) == False:
                self.lad_matrix_registers_objs[group].append(self.lad_saved_obj)


                for p in range(PRESET_CNT):
                    self.lad_matrix_presets_valid[group][p].append(False)
                    self.lad_matrix_presets[group][p].append(0)


                self.lad_update_faders() #register obj
                if save_cfg == True:
                    self.lad_save_param_cfg() # lad_register_obj
                free_place = len(self.lad_matrix_registers_objs[group])
                self.lad_set_info("Registered: " + str(free_place))
                free_place = free_place - 1
                self.lad_perf_page[group] = 0
            self.lad_clear_saved_obj()

        return free_place

    def lad_unregister_obj(self):

        if len(self.lad_matrix_registers_objs) != GROUP_CNT:
            return False

        done = False

        if self.lad_saved_obj != None:
            fd = self.tuple_idx(self.lad_matrix_registers_objs[self.lad_current_group], self.lad_saved_obj)
            if fd != -1:
                self.lad_matrix_registers_objs[self.lad_current_group].remove(self.lad_saved_obj)
                for p in range(PRESET_CNT):
                    self.lad_matrix_presets_valid[self.lad_current_group][p].pop(fd)
                    self.lad_matrix_presets[self.lad_current_group][p].pop(fd)

                done = True
                self.lad_perf_page[self.lad_current_group] = 0


        self.lad_clear_saved_obj()
        if done == True:
            self.lad_save_param_cfg() # lad_unregister_obj

        return done

    def lad_clear_registered_obj(self, group):
        self.lad_matrix_registers_objs[group] = []
        self.lad_preset_rec_init_values_group(group)
        self.lad_set_info("all params removed")

    def lad_set_all(self):

        if self.lad_perf_mode == True:
            return

        if self.lad_mixer_mode == True:
            return

        #mylog("lad_set_all: registered before (group", self.lad_current_group, ") =>", len(self.lad_matrix_registers_objs[self.lad_current_group])) # PERMANENT
        track = self.song().view.selected_track
        if track != None:
            device =  track.view.selected_device
            if device != None:
                i = 0
                for param in device.parameters:
                    if i != 0:
                        self.lad_saved_obj = param
                        self.lad_register_obj(self.lad_current_group, True)
                    i = i + 1
        #mylog("lad_set_all: registered after (group", self.lad_current_group, ") =>", len(self.lad_matrix_registers_objs[self.lad_current_group])) # PERMANENT


#    ## PERF ################################################################################################
    lad_perf_mode = False
    lad_reset_mode = False

    def lad_switch_perf_mode(self):
        self.lad_clear_saved_obj()

        self.lad_called_preset = -1

        self.lad_preset_rec_active = False
        self.lad_preset_rec_gui()

        self.lad_reset_mode = False
        self.lad_reset_mode_gui()

        self.lad_morph = False
        self.lad_morph_prep = 0
        self.lad_preset_morph_gui()

        self.lad_display_basic_perf_button()

        self.lad_set_info("")

        return

#    ## GROUP ################################################################################################
    lad_current_group = 0

    def lad_group_gui(self):
        for g in range(GROUP_CNT):
            address = "/lad/label_grp" + str(g+1) + "/color"
            color = "gray"
            if g == self.lad_current_group:
                color = lad_hl_color
            self.oscEndpoint.send(address, color)

#    ## PRESET ################################################################################################
    lad_called_preset = -1
    lad_preset_rec_active = False

    lad_matrix_registers_objs = []
    lad_matrix_presets_valid = []
    lad_matrix_presets = []
    lad_matrix_morph_presets = []

    lad_buttonds_state = []

    def lad_update_matrix(self):

        if len(self.lad_matrix_registers_objs) != GROUP_CNT:
            return

        for g in range(GROUP_CNT):

            matrix_registers_objs = []
            valid_objs = []
            for i in range(len(self.lad_matrix_registers_objs[g])):
                if self.lad_matrix_registers_objs[g][i] != None:
                    valid_objs.append(i)
                    matrix_registers_objs.append(self.lad_matrix_registers_objs[g][i])
            self.lad_matrix_registers_objs[g] = matrix_registers_objs

            if len(valid_objs) > 0:
                for p in range(PRESET_CNT):
                    matrix_presets_valid = []
                    matrix_presets = []
                    for i in valid_objs:
                        matrix_presets_valid.append(self.lad_matrix_presets_valid[g][p][i])
                        matrix_presets.append(self.lad_matrix_presets[g][p][i])

                    self.lad_matrix_presets_valid[g][p] = matrix_presets_valid
                    self.lad_matrix_presets[g][p] = matrix_presets


        return

    def lad_init_preset(self):
        g, p = GROUP_CNT, PRESET_CNT

        self.lad_matrix_registers_objs = []
        self.lad_matrix_registers_objs = [[] for x in range(g)]

        self.lad_matrix_presets_valid = []
        self.lad_matrix_presets_valid = [[[] for x in range(p)] for y in range(g)]

        self.lad_matrix_presets = []
        self.lad_matrix_presets = [[[] for x in range(p)] for y in range(g)]

        self.lad_matrix_morph_presets = []
        self.lad_matrix_morph_presets = [[-1 for i in range(2)] for x in range(g)]

        return

    def lad_preset_rec_gui(self):

        color = "gray"
        if self.lad_preset_rec_active == True:
            self.lad_set_info("")
            for i in range(1,PRESET_CNT+1):
                self.lad_preset_gui(i, 1)
            color = lad_hl_color
        else:
            for i in range(1,PRESET_CNT+1):
                self.lad_preset_gui(i, 0)


        address = "/lad/label_rec/color"
        self.oscEndpoint.send(address, color)
        self.touch_send_midi_info(4, self.lad_preset_rec_active)

        address = "/lad/label_trm/color"
        self.oscEndpoint.send(address, color)

        address = "/lad/label_dvm/color"
        self.oscEndpoint.send(address, color)

        self.lad_edit_preset_buttonds_mode_gui()

        return


    def lad_preset_gui(self, button, mode):
        if mode == 0:
            color = "gray"
        elif mode == 1:
            color = lad_hl_color

        address = "/lad/label_p" + str(button) + "/color"
        self.oscEndpoint.send(address, color)

        return

    def lad_populate_label_preset(self, preset):

        if self.lad_perf_mode == False:
            return

        if preset < 0:
            return
        if preset >= PRESET_CNT:
            return

        address = "/lad/label_p" + str(preset+1)
        label = "PRESET " + str(preset+1)

        for j in range(len(self.lad_matrix_presets_valid[self.lad_current_group][preset])):
            if self.lad_matrix_presets_valid[self.lad_current_group][preset][j] == True:
                label = label + "R"
                break

        self.oscEndpoint.send(address, label)

        return

    def lad_preset_rec_init_values_group(self, group):
        for p in range(PRESET_CNT):
            self.lad_matrix_presets_valid[group][p] = []
            self.lad_matrix_presets[group][p] = []
            if group == self.lad_current_group:
                self.lad_populate_label_preset(p)

    def lad_preset_rec_init_values(self):
        for g in range(GROUP_CNT):
            self.lad_preset_rec_init_values_group(g)
        return

    def lad_preset_rec_values(self, preset):

        if len(self.lad_matrix_registers_objs) != GROUP_CNT:
            return

        if self.lad_perf_mode == False:
            return

        if self.lad_morph == True:
            return

        if self.lad_preset_rec_active == True:
            if preset >= 0 and preset < PRESET_CNT:

                done = False
                self.lad_matrix_presets_valid[self.lad_current_group][preset] = []
                self.lad_matrix_presets[self.lad_current_group][preset] = []
                for i in range(len(self.lad_matrix_registers_objs[self.lad_current_group])):
                    if self.lad_matrix_registers_objs[self.lad_current_group][i] != None:
                        valid = True
                        if i < len(self.lad_buttonds_state):
                            valid = self.lad_buttonds_state[i]
                        self.lad_matrix_presets_valid[self.lad_current_group][preset].append(valid)
                        param = self.lad_matrix_registers_objs[self.lad_current_group][i]
                        self.lad_matrix_presets[self.lad_current_group][preset].append(self.adaptValue(param.value, param.min, param.max, 0.0, 1.0))
                        done = True

                self.lad_populate_label_preset(preset)
                if done == True:
                    self.lad_set_info("preset " + str(preset+1) + " recorded")
                    self.lad_called_preset = preset
                    self.lad_save_param_cfg() # lad_preset_rec_values
                    self.lad_buttonds_state = []


    def lad_preset_recall(self, preset):

        if len(self.lad_matrix_registers_objs) != GROUP_CNT:
            return

        if self.lad_perf_mode == False:
            return

        if self.lad_morph == True:
            return

        if self.lad_preset_rec_active == True:
            return

        if self.lad_reset_mode == True:
            return

        self.lad_set_info("")

        if preset >= 0 and preset < PRESET_CNT:
            display = False
            self.lad_called_preset = -1

            for i in range(len(self.lad_matrix_registers_objs[self.lad_current_group])):
                if i < len(self.lad_matrix_presets_valid[self.lad_current_group][preset]):
                    if self.lad_matrix_presets_valid[self.lad_current_group][preset][i] == True:
                        if self.lad_matrix_registers_objs[self.lad_current_group][i] != None:
                            param = self.lad_matrix_registers_objs[self.lad_current_group][i]
                            param.value = self.adaptValue(self.lad_matrix_presets[self.lad_current_group][preset][i], 0.0, 1.0, param.min, param.max)
                            self.lad_called_preset = preset
                            display = True

            if display == True:
                self.lad_set_info("recall preset " + str(preset+1))

            self.lad_show_currents() # lad_preset_recall

    def lad_preset_toggle_param_button(self, button):

        valid = False

        if self.lad_preset_rec_active == True or self.lad_reset_mode == True:
            if self.lad_current_group >= 0:
                if self.lad_current_group < GROUP_CNT:
                    g = self.lad_current_group
                    page = self.lad_perf_page[g]
                    f = button + page*self.FADER_CNT
                    if f < len(self.lad_buttonds_state):
                        valid = self.lad_buttonds_state[f]

        address = "/lad/toggled" + str(button + 1)
        if valid == True:
            self.oscEndpoint.send(address, 1.0)
        else:
            self.oscEndpoint.send(address, 0.0)

    def lad_reset_buttonds_mode_gui(self):
        self.lad_buttonds_mode_gui(self.lad_reset_mode)

    def lad_edit_preset_buttonds_mode_gui(self):
        self.lad_buttonds_mode_gui(self.lad_preset_rec_active)

    def lad_buttonds_mode_gui(self, enable):
        if enable == False:
            for i in range(self.FADER_CNT):
                addressfd = "/lad/faderd" + str(i+1) + "/visible"
                self.oscEndpoint.send(addressfd, "True")
        else:
            for i in range(self.FADER_CNT):
                addressfd = "/lad/faderd" + str(i+1) + "/visible"
                self.oscEndpoint.send(addressfd, "False")

    def lad_toggle_buttond(self, button):
        if self.lad_preset_rec_active == True or self.lad_reset_mode == True:
            if self.lad_current_group >= 0:
                if self.lad_current_group < GROUP_CNT:
                    g = self.lad_current_group
                    page = self.lad_perf_page[g]
                    f = button + page*self.FADER_CNT
                    if f < len(self.lad_buttonds_state):
                        self.lad_buttonds_state[f] = not self.lad_buttonds_state[f]
                        self.lad_preset_toggle_param_button(button)

    def lad_preset_set_all_params(self):
        for b in range(len(self.lad_buttonds_state)):
            self.lad_buttonds_state[b] = True
            self.lad_preset_toggle_param_button(b)


    def lad_preset_invert_params(self):
        for b in range(len(self.lad_buttonds_state)):
            self.lad_buttonds_state[b] = not self.lad_buttonds_state[b]
            self.lad_preset_toggle_param_button(b)


#    ## MORPH ################################################################################################
    lad_morph = False
    lad_morph_prep = 0

    def lad_morph_fct(self):

        self.lad_morph_prep = 0

        if self.lad_perf_mode == False:
            return

        if self.lad_preset_rec_active == True:
            return

        if self.lad_reset_mode == True:
            return

        self.lad_called_preset = -1
        self.lad_matrix_morph_presets[self.lad_current_group][0] = -1
        self.lad_matrix_morph_presets[self.lad_current_group][1] = -1
        self.lad_morph = not self.lad_morph
        self.lad_preset_morph_gui()

        if self.lad_matrix_morph_presets[self.lad_current_group][0] == -1 or self.lad_matrix_morph_presets[self.lad_current_group][1] == -1:
            self.lad_perf_reset_mfader(self.lad_current_group) # morph fct
        self.lad_perf_active_mfader(self.lad_current_group) # lad_morph_fct


        return

    def lad_preset_morph_gui(self):
        color = "gray"
        if self.lad_morph == True:
            color = lad_hl_color
        address = "/lad/label_morph/color"
        self.oscEndpoint.send(address, color)
        self.touch_send_midi_info(5, self.lad_morph)
        return

    def lad_perf_reset_mfader(self, group):
        address = "/lad/faderm" + str(group+1)
        self.oscEndpoint.send(address, float(0))
        address = "/morph/xy"
        if group == 0:
            self.lad_faderm1_val = 0.0
        else:
            self.lad_faderm2_val = 0.0

        self.morph_set_current(group, "")
        self.oscEndpoint.send(address, (float(self.lad_faderm2_val), float(self.lad_faderm1_val)) )

        if group == 0:
            val = int(self.adaptValue(self.lad_faderm1_val, 0, 1.0, 0, 127))
            self.send_midi_ex((0xB0, const.MIDI_LAD_MORPH_SLIDER, val), UTIL_TAB | LAD_TAB | MORPH_TAB)

        return

    def lad_perf_active_mfader(self, group):
        address = "/lad/faderm" + str(group+1) + "/color"
        if (len(self.lad_matrix_morph_presets) == GROUP_CNT) and (self.lad_matrix_morph_presets[group][0] != -1) and (self.lad_matrix_morph_presets[group][1] != -1):
            text = lad_hl_color2
        else:
            text = "gray"
        self.oscEndpoint.send(address, text)



        return

    lad_faderm1_val = 0.0
    lad_faderm2_val = 0.0

    def lad_faderm_input(self, _fader, val_fader, update_morph_fader = True):

        if len(self.lad_matrix_registers_objs) != GROUP_CNT:
            return

        if _fader == 1:
            self.lad_faderm1_val = val_fader
        else:
            self.lad_faderm2_val = val_fader

        if update_morph_fader == True:
            address = "/morph/xy"
            self.oscEndpoint.send(address, (float(self.lad_faderm2_val),float(self.lad_faderm1_val)) )

        group = _fader - 1

        if self.lad_matrix_morph_presets[group][0] == -1:
            return

        if self.lad_matrix_morph_presets[group][-1] == -1:
            return


        preset_src = self.lad_matrix_morph_presets[group][0]
        preset_dest = self.lad_matrix_morph_presets[group][1]

        for i in range(len(self.lad_matrix_registers_objs[group])):
            if self.lad_matrix_registers_objs[group][i] != None:
                param = self.lad_matrix_registers_objs[group][i]

                if self.lad_matrix_presets_valid[group][preset_src][i] == True:
                    if self.lad_matrix_presets_valid[group][preset_dest][i] == True:
                        if self.lad_matrix_presets[group][preset_dest][i] != self.lad_matrix_presets[group][preset_src][i]:
                            value = self.lad_matrix_presets[group][preset_dest][i] - self.lad_matrix_presets[group][preset_src][i]
                            value = value * val_fader
                            value = self.lad_matrix_presets[group][preset_src][i] + value
                            param.value = self.adaptValue(value, 0.0, 1.0, param.min, param.max)
                            text = "morphing " + str(preset_src + 1) + ":" + str(preset_dest + 1) + " (" + str(int(val_fader*100)) + " %)"
                            self.lad_set_current(text)
                            self.wio_send_info(str(int(val_fader*100)) + " %")
                            self.morph_set_current(group, text)
                            if group == 0:
                                val = int(self.adaptValue(val_fader, 0, 1.0, 0, 127))
                                self.send_midi_ex((0xB0, const.MIDI_LAD_MORPH_SLIDER, val), UTIL_TAB | LAD_TAB | MORPH_TAB)



        return

    def lad_update_faders_perf(self):

        if self.lad_perf_mode == False:
            return

        if len(self.lad_matrix_registers_objs) != GROUP_CNT:
            return

        for i in range(self.FADER_CNT):
            param = None
            if (i + self.lad_perf_page[self.lad_current_group]*self.FADER_CNT) < len(self.lad_matrix_registers_objs[self.lad_current_group]):
                param = self.lad_matrix_registers_objs[self.lad_current_group][i + self.lad_perf_page[self.lad_current_group]*self.FADER_CNT]

            self.lad_update_fader_param(param, i+1) #perf



        return

		
#    ## RANDOM ###########################################################################################

    lad_rand_exclude = ["volume", "gain", "param"]

    def lad_rand_param(self, param):
        obj = param.canonical_parent
        if obj != None:
            if isinstance(obj, Live.MixerDevice.MixerDevice):
                dname = "MixerDevice"
            else:
                dname = str(obj.name)

        if dname == "Utility":
            return

        if dname == "MixerDevice":
            return

        nname = param.name.lower()
        to_be_excluded = False
        for j in range(len(self.lad_rand_exclude)):
            if nname == self.lad_rand_exclude[j]:
                to_be_excluded = True
                break

        if to_be_excluded == False:

            val = param.value

            if param.is_quantized == True:
                nval = random.randint(0,len(param.value_items)-1)
            else:
                rval = random.random()
                nval = self.adaptValue(rval, 0.0, 1.0, param.min, param.max)

                text = param.str_for_value(nval).lower()
                if text.endswith('db') == True:
                    idx = text.index(" db")
                    text = text[:idx]
                    dbval = float(text)
                    if dbval > 0.0:
                        nval = (param.max - param.min)/2

            param.value = nval

        return


    def lad_rand(self):

        if self.lad_perf_mode == False:
            if self.lad_mixer_mode == False:
                current_track = self.song().view.selected_track
                if(current_track == None):
                    return

                devices = current_track.devices
                if len(devices) == 0:
                    return

                device = current_track.view.selected_device
                if device == None:
                    return

                for i in range(1,len(device.parameters)):
                    param = device.parameters[i]
                    self.lad_rand_param(param)

        else:
            for i in range(0,len(self.lad_matrix_registers_objs[self.lad_current_group])):
                param = self.lad_matrix_registers_objs[self.lad_current_group][i]
                if param != None:
                    device = param.canonical_parent
                    if device != None:
                        if isinstance(device, Live.MixerDevice.MixerDevice) == False:
                            self.lad_rand_param(param)

        return


#    ## LAD GUI ###########################################################################################

    lad_label_info_mode = 0

    def lad_disp_play(self):
        address = "/lad/led_play"
        if self.song().is_playing:
            self.oscEndpoint.send(address, 1)
        else:
            self.oscEndpoint.send(address, 0)

    def lad_update_show_gui(self):

        self.touch_send_midi_info(0, self.lad_show_display)

        address = "/lad/label_show/color"
        if self.lad_show_display == True:
            self.oscEndpoint.send(address, lad_hl_color)
        else:
            self.oscEndpoint.send(address, "gray")

    def lad_update_volume_pan_name(self, label):
        if label == "Track Volume":
            label = "Volume"
        if label == "Track Panning":
            label = "Pan"
        return label

    def lad_update_label_name(self, param):
        label = ""
        if self.lad_perf_mode == False:
            # force lad_label_info_mode to 0 in basic mode
            self.lad_label_info_mode = 0

        if self.lad_label_info_mode == 0:
            label = self.lad_update_volume_pan_name(str(param.name))

        elif self.lad_label_info_mode == 1:
            label = self.lad_update_volume_pan_name(str(param.name))
            obj = param.canonical_parent
            if obj != None:
                if isinstance(obj, Live.MixerDevice.MixerDevice):
                    label = "MixerDevice"
                else:
                    label = str(obj.name)

        elif self.lad_label_info_mode == 2:
            label = self.lad_update_volume_pan_name(str(param.name))
            obj = param.canonical_parent
            if obj != None:
                obj = obj.canonical_parent
                if obj != None:
                    label = str(obj.name)

        return label

    LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z" ]

    def lad_set_mixer_gui(self):

        if self.lad_perf_mode == True:
            return

        address = "/lad/label_mixer/color"

        if self.lad_mixer == True:
            self.oscEndpoint.send(address, lad_hl_color)
            address = "/lad/label_pgm"
            self.oscEndpoint.send(address, "")
            address = "/lad/label_pgp"
            self.oscEndpoint.send(address, "")
            address = "/lad/label_set_all_clear"
            self.oscEndpoint.send(address, "")
            address = "/lad/label_rand"
            self.oscEndpoint.send(address, "")
        else:
            self.oscEndpoint.send(address, "gray")
            address = "/lad/label_pgm"
            self.oscEndpoint.send(address, "PG -")
            address = "/lad/label_pgp"
            self.oscEndpoint.send(address, "PG +")
            address = "/lad/label_set_all_clear"
            self.oscEndpoint.send(address, "SET ALL")
            address = "/lad/label_rand"
            self.oscEndpoint.send(address, "RAND")

    lad_last_info_message = ""
    def lad_set_last_info(self):
        address = "/lad/label_info"
        self.oscEndpoint.send(address, self.lad_last_info_message)
        address = "/util/label_info"
        self.oscEndpoint.send(address, self.lad_last_info_message)

    def lad_set_info(self, message):
        self.lad_last_info_message = message
        address = "/lad/label_info"
        self.oscEndpoint.send(address, message)
        address = "/util/label_info"
        self.oscEndpoint.send(address, message)
        self.wio_send_info(message)


    def lad_set_current(self, message, message2 = ""):
        if len(message2) != 0:
            message = message + " : " + message2
        address = "/lad/label_current"
        self.oscEndpoint.send(address, message)
        address = "/util/label_current"
        self.oscEndpoint.send(address, message)


    def lad_show_currents(self):
        self.lad_update_faders() #show currents
        if self.lad_perf_mode == False:
            if self.lad_mixer == False:
                self.lad_update_tr_dv_pg()
            else:
                self.lad_update_mixer_devices()
        else:
            self.lad_update_tr_dv_pg()
        return

    def lad_update_mixer_devices(self):

        if self.lad_mixer == True:
            if self.lad_mixer_mode == 0:
                label = "Volume"
            elif self.lad_mixer_mode == 1:
                label = "Pan"
            else:
                idx = self.lad_mixer_mode-2
                text = str(idx)
                if idx < len(self.LETTERS):
                    text = self.LETTERS[idx]

                label = "Send-" + text

            address = "/lad/label_track"
            self.oscEndpoint.send(address, str(label))
            address = "/util/label_track"
            self.oscEndpoint.send(address, str(label))
            self.wio_send_track_name(str(label))

            self.lad_clear_tr_dv_pg_cu(False,True,True,True)
            self.wio_send_device_count(" ")

    def lad_update_tr_dv_pg(self):

        no_device = False

        track = LiveUtils.getSong().view.selected_track
        if track == None:
            self.lad_clear_tr_dv_pg_cu(True,True,True,True)
            return

        device = LiveUtils.getSong().view.selected_track.view.selected_device
        if device == None:
            no_device = True

        address = "/lad/label_track"
        self.oscEndpoint.send(address, str(track.name))
        address = "/util/label_track"
        self.oscEndpoint.send(address, str(track.name))
        self.wio_send_track_name(str(track.name))

        if self.lad_perf_mode == False:


            if no_device:
                self.lad_clear_tr_dv_pg_cu(False,True,False,False)
                if len(track.devices) == 0:
                    self.wio_send_device_count("No device")
                else:
                    self.wio_send_device_count(" ")
            else:
                address = "/lad/label_device"
                self.oscEndpoint.send(address, str(device.name))
                address = "/util/label_device"
                self.oscEndpoint.send(address, str(device.name))
                self.wio_send_device_name(str(device.name))
                idx = self.tuple_idx(track.devices, device)
                if idx == -1:
                    self.wio_send_device_count(" ")
                else:
                    text = str(idx+1) + "/" + str(len(track.devices))
                    self.wio_send_device_count(text)

            if no_device:
                self.lad_clear_tr_dv_pg_cu(False,False,True,False)
            else:
                address = "/lad/label_page"
                text = str(self.lad_device_page+1) + "/" + str(self.lad_get_pages_count(device))
                self.oscEndpoint.send(address, text)
                address = "/util/label_page"
                self.oscEndpoint.send(address, text)
                self.wio_send_page(text)

        else:

            address = "/lad/label_device"
            self.oscEndpoint.send(address, "")
            address = "/util/label_device"
            self.oscEndpoint.send(address, "")
            self.wio_send_device_name("")

            address = "/lad/label_page"
            self.oscEndpoint.send(address, "")
            address = "/util/label_page"
            self.oscEndpoint.send(address, "")
            self.wio_send_page(" ")

            self.wio_send_device_count(" ")


        self.lad_clear_tr_dv_pg_cu(False,False,False,True)

        return

    def lad_display_basic_perf_button(self):
        
        self.lad_perf_active_mfader(self.lad_current_group) # lad_display_basic_perf_button

        self.lad_reset_mode_gui()
#        address = "/lad/label_rec/color"
#        self.oscEndpoint.send(address, "gray")
#        self.touch_send_midi_info(4, False)

        address = "/lad/label_morph/color"
        self.oscEndpoint.send(address, "gray")

        address = "/lad/label_arm"
        self.oscEndpoint.send(address, "ARM")
        address = "/lad/label_arm/color"
        self.oscEndpoint.send(address, "red")

        address = "/lad/label_ovd"
        self.oscEndpoint.send(address, "OVD")
        address = "/lad/label_ovd/color"
        self.oscEndpoint.send(address, "red")

        if self.lad_perf_mode == False:

            self.touch_send_midi_info(1, self.lad_mixer)
            address = "/lad/label_mixer"
            self.oscEndpoint.send(address, "MIXER")

            address = "/lad/label_trm"
            self.oscEndpoint.send(address, "TR -")
            address = "/lad/label_trp"
            self.oscEndpoint.send(address, "TR +")
            address = "/lad/label_dvm"
            self.oscEndpoint.send(address, "DV -")
            address = "/lad/label_dvp"
            self.oscEndpoint.send(address, "DV +")

            address = "/lad/label_basic_perf"
            self.oscEndpoint.send(address, "BASIC")
            address = "/lad/label_basic_perf/color"
            self.oscEndpoint.send(address, "gray")
            address = "/lad/label_set_reset"
            self.oscEndpoint.send(address, "SET")
            address = "/lad/label_rec"
            self.oscEndpoint.send(address, "")
            address = "/lad/label_morph"
            self.oscEndpoint.send(address, "")

            address = "/lad/label_set_all_clear"
            self.oscEndpoint.send(address, "SET ALL")

            for i in range(PRESET_CNT):
                address = "/lad/label_p" + str(i+1)
                self.oscEndpoint.send(address, "")
                address = "/lad/label_p" + str(i+1) + "/color"
                self.oscEndpoint.send(address, "gray")

        else:


            self.touch_send_midi_info(1, False)

            address = "/lad/label_mixer"
            self.oscEndpoint.send(address, "INFO")

            address = "/lad/label_mixer/color"
            self.oscEndpoint.send(address, "gray")

            address = "/lad/label_trm"
            self.oscEndpoint.send(address, "ALL")
            address = "/lad/label_trp"
            self.oscEndpoint.send(address, "")
            address = "/lad/label_dvm"
            self.oscEndpoint.send(address, "INVERT")
            address = "/lad/label_dvp"
            self.oscEndpoint.send(address, "")
            address = "/lad/label_pgm"
            self.oscEndpoint.send(address, "PG -")
            address = "/lad/label_pgp"
            self.oscEndpoint.send(address, "PG +")

            address = "/lad/label_basic_perf"
            self.oscEndpoint.send(address, "PERF")
            address = "/lad/label_basic_perf/color"
            self.oscEndpoint.send(address, lad_hl_color)
            address = "/lad/label_set_reset"
            self.oscEndpoint.send(address, "RESET")
            address = "/lad/label_rec"
            self.oscEndpoint.send(address, "REC")
            address = "/lad/label_rec/color"
            self.oscEndpoint.send(address, "gray")
            self.touch_send_midi_info(4, False)

            address = "/lad/label_morph"
            self.oscEndpoint.send(address, "MORPH")

            address = "/lad/label_set_all_clear"
            self.oscEndpoint.send(address, "CLEAR")

            address = "/lad/label_rand"
            self.oscEndpoint.send(address, "RAND")


            for i in range(PRESET_CNT):
                self.lad_populate_label_preset(i)
                address = "/lad/label_p" + str(i+1) + "/color"
                self.oscEndpoint.send(address, "gray")

        return


    def lad_clear_tr_dv_pg_cu(self, tr, dv, pg, cu):
        if tr == True:
            address = "/lad/label_track"
            self.oscEndpoint.send(address, str(""))
            address = "/util/label_track"
            self.oscEndpoint.send(address, str(""))
            self.wio_send_track_name(" ")

        if dv == True:
            address = "/lad/label_device"
            self.oscEndpoint.send(address, str(""))
            address = "/util/label_device"
            self.oscEndpoint.send(address, str(""))
            self.wio_send_device_name(" ")

        if pg == True:
            address = "/lad/label_page"
            self.oscEndpoint.send(address, str(""))
            address = "/util/label_page"
            self.oscEndpoint.send(address, str(""))
            self.wio_send_page(" ")


        if cu == True:
            self.lad_set_current("")
            self.wio_send_param_name(" ")
            self.wio_send_param_val(" ")

        return


    def lad_update(self):

        self.lad_set_last_info()
        self.lad_display_basic_perf_button() # lad_update
        self.lad_set_mixer_gui() # lad_update
        self.lad_show_currents() # lad_update
        self.lad_group_gui() # lad_update
        self.util_update_lower_gui() # lad_update
        self.util_update_midi_button() # lad_update
        self.util_update_disable_osc_gui() # lad_update

        return

    def lad_reset_mode_gui(self):
        address = "/lad/label_set_reset/color"
        if self.lad_reset_mode == False:
            self.oscEndpoint.send(address, "gray")
        else:
            self.oscEndpoint.send(address, "yellow")
        self.touch_send_midi_info(3, self.lad_reset_mode)
        self.lad_reset_buttonds_mode_gui()



#    ## LAD MIDI ###########################################################################################

    def touch_send_midi_info(self, mode, enable):

        val = 0
        if enable == True:
            val = 127

        if (self.lito_tab == LAD_TAB) or (self.lito_tab == UTIL_TAB):
            if mode == 0: # auto
                self.send_midi_ex((0xB0, const.MIDI_LAD_SHOW, val), UTIL_TAB | LAD_TAB | MORPH_TAB)
            elif mode == 1: # mixer
                self.send_midi_ex((0xB0, const.MIDI_LAD_MIXER_INFO, val), UTIL_TAB | LAD_TAB | MORPH_TAB)
            elif mode == 2: # perf
                self.send_midi_ex((0xB0, const.MIDI_LAD_PERF, val), UTIL_TAB | LAD_TAB | MORPH_TAB)
            elif mode == 3: # set/reset
                self.send_midi_ex((0xB0, const.MIDI_LAD_SET_RESET, val), UTIL_TAB | LAD_TAB | MORPH_TAB)
            elif mode == 4: # rec
                self.send_midi_ex((0xB0, const.MIDI_LAD_REC, val), UTIL_TAB | LAD_TAB | MORPH_TAB)
            elif mode == 5: # morph
                self.send_midi_ex((0xB0, const.MIDI_LAD_MORPH, val), UTIL_TAB | LAD_TAB | MORPH_TAB)
            elif mode == 6: # lower
                self.send_midi_ex((0xB0, const.MIDI_LAD_LOWER_FADER, val), UTIL_TAB | LAD_TAB | MORPH_TAB)

#    ## LAD SAVE/RESTORE ###########################################################################################

    def lad_set_track_id(self, track):
        text = track.get_data("LITO_TR_ID", 'null')
        if text == "null":
            text = str(random.randint(1,65536))+str(random.randint(1,65536))
            track.set_data("LITO_TR_ID", text)
        return

    def dgb_log(self, *msgs):
        debug = False
        if debug == True:
            mylog(msgs) # PERMANENT
        return

    def lad_load_one_param_cfg(self, group, items):
        self.dgb_log("-----------------------------------------------")
        self.dgb_log("---- lad_load_one_param_cfg ----")
        self.dgb_log(items)

        free_place = -1
        param = None
        tid = int(items[0])
        self.dgb_log("tid", tid)
        if tid >= 0:
            self.dgb_log("tid not < 0")

            if tid < len(self.all_tracks):
                self.dgb_log("tid valid")

                track = self.all_tracks[tid]
                if track != None:
                    self.dgb_log("track not None")

                    id = track.get_data("LITO_TR_ID", "null")
                    self.dgb_log("LITO_TR_ID", id)
                    if id != "null":
                        self.dgb_log("track id not null")
                        self.dgb_log("track id stored/live", items[3], id)
                        if id == items[3]:
                            self.dgb_log("track id OK !")

                            did = int(items[1])
                            self.dgb_log("did", did)
                            if did == -2:
                                pid = int(items[2])
                                param = None
                                if pid == 0:
                                    param = track.mixer_device.volume
                                elif pid == 1:
                                    param = track.mixer_device.panning
                                else:
                                    sid = pid-2
                                    if sid >= 0:
                                        if sid < self.sends_count:
                                            param = track.mixer_device.sends[sid]
                                if param != None:
                                    self.lad_saved_obj = param
                                    free_place = self.lad_register_obj(group, False)

                            else:
                                if did >= 0:
                                    self.dgb_log("did not < 0")

                                    if did < len(track.devices):
                                        self.dgb_log("did valid")

                                        dname = items[4]
                                        device = track.devices[did]
                                        if device != None:
                                            self.dgb_log("device not None")

                                            self.dgb_log("device name stored/live", dname, device.name)
                                            if dname == device.name:
                                                self.dgb_log("device name OK !")

                                                pid = int(items[2])
                                                self.dgb_log("pid", pid)
                                                if pid >= 0:
                                                    self.dgb_log("pid not < 0")

                                                    if pid < len(device.parameters):
                                                        self.dgb_log("pid valid")

                                                        pname = items[5]
                                                        param = device.parameters[pid]
                                                        if param!= None:
                                                            self.dgb_log("param not None")
                                                            self.dgb_log("param name stored/live", pname, param.name)
                                                            if pname == param.name:
                                                                self.dgb_log("param name OK !")

                                                                self.lad_saved_obj = param
                                                                free_place = self.lad_register_obj(group, False)

        if free_place != -1 and param != None:
            #saved_val = param.value
            for p in range(6):
                if p < PRESET_CNT:
                    if items[6+p] != "...":
                        val = float(items[6+p])
                        self.lad_matrix_presets_valid[group][p][free_place] = True
                        self.lad_matrix_presets[group][p][free_place] = val
            #param.value = saved_val

        self.dgb_log("---- end of lad_load_one_param_cfg ----")

    def lad_load_param_cfg(self, group, cfg):
        cfgs = cfg.split("\n")
        for c in range(len(cfgs)):
            items = cfgs[c].split("###")
            if len(items) == 13:
                #myslog(str(cfgs[c])) # PERMANENT
                if items[len(items)-1] == "end":
                    self.lad_load_one_param_cfg(group, items)

        return

    def lad_load_param_live_cfg(self):
        for g in range(GROUP_CNT):
            key = "LITO_CFG_GRP" + str(g)
            cfg = self.song().get_data(key, "null")
            if cfg != "null":
                self.lad_load_param_cfg(g, cfg)
        return

    def lad_save_param_cfg(self, export_only = False):

        self.dgb_log("-----------------------------------------------")
        self.dgb_log("---- lad_save_param_cfg ----")

        self.dgb_log("len(self.lad_matrix_registers_objs)", len(self.lad_matrix_registers_objs))

        if len(self.lad_matrix_registers_objs) == 0:
            return

        for g in range(GROUP_CNT):
            cfg_text = ""
            cfg_count = 0
            for f in range(len(self.lad_matrix_registers_objs[g])):
                tid = -1
                did = -1
                pid = -1
                tname = ""
                dname = ""
                config_ok = False


                if self.lad_matrix_registers_objs[g][f] != None:
                    param = self.lad_matrix_registers_objs[g][f]
                    obj = param.canonical_parent
                    if obj != None:
                        if isinstance(obj, Live.MixerDevice.MixerDevice):
                            dname = "MixerDevice"
                        else:
                            dname = str(obj.name)
                        device = obj
                        obj = obj.canonical_parent
                        if obj != None:
                            self.dgb_log("track not None")
                            track = obj
                            tname = track.get_data("LITO_TR_ID", 'null')
                            if tname != "null":
                                self.dgb_log("tname not null")
                                tid = self.tuple_idx(self.all_tracks, track)
                                if tid != -1:
                                    self.dgb_log("tid not -1")
                                    did = -1
                                    if isinstance(device, Live.MixerDevice.MixerDevice):
                                        did = -2 # mixer device ID is -2
                                        pid = -1
                                        if param == device.volume:
                                            pid = 0
                                        elif param == device.panning:
                                            pid = 1
                                        else:
                                            if track != self.song().master_track:
                                                for s in range(self.sends_count):
                                                    if param == device.sends[s]:
                                                        pid = s + 2
                                                        break
                                    else:
                                        did = self.tuple_idx(track.devices, device)
                                        if did != -1:
                                            self.dgb_log("did not -1")
                                            pid = self.tuple_idx(device.parameters, param)

                                    if pid != -1:
                                        self.dgb_log("pid not -1")
                                        cfg_text = cfg_text + str(tid) + "###"
                                        cfg_text = cfg_text + str(did) + "###"
                                        cfg_text = cfg_text + str(pid) + "###"
                                        cfg_text = cfg_text + tname + "###"
                                        cfg_text = cfg_text + dname + "###"
                                        cfg_text = cfg_text + param.name + "###"

                                        for p in range(PRESET_CNT):

                                            if self.lad_matrix_presets_valid[g][p][f] == True:
                                                val = self.lad_matrix_presets[g][p][f]
                                                cfg_text = cfg_text + str(val) + "###"
                                            else:
                                                cfg_text = cfg_text + "..." + "###"


                                        cfg_text = cfg_text + "end\n"
                                        cfg_count = cfg_count + 1

            self.dgb_log(cfg_text)

            if cfg_text != "" :
                if export_only == False:
                    key = "LITO_CFG_GRP" + str(g)
                    self.song().set_data(key, cfg_text)
                    self.lad_config_changed = True
                    self.request_rebuild_midi_map()
                else:
                    text = "config count " + str(cfg_count) + "\n"
                    cfg_text = text + cfg_text
                    myslog("\n---------------------------\n---- group: " + str(g) + " ----\n" + cfg_text) # PERMANENT
            else:
                if export_only == True:
                     myslog("\n---------------------------\nNo configuration for group " + str(g)) # PERMANENT
                else:
                    key = "LITO_CFG_GRP" + str(g)
                    self.song().set_data(key, 'null')
                    self.lad_config_changed = True
                    self.request_rebuild_midi_map()

        self.dgb_log("---- end of lad_save_param_cfg ----")
        return

    def lad_export_cfg(self):
        song = None
        try:
            song = LiveUtils.getSong()
        except:
            pass

        if song != None:
            track = song.view.selected_track
            if track != None:
                device = LiveUtils.getSong().view.selected_track.view.selected_device
                if device != None:
                    if not isinstance(device, Live.MixerDevice.MixerDevice):
                        text = "\n---------------------------\nCurrent device log:"
                        text += "\ndevice = "
                        text += device.class_display_name
                        text += "\n"
                        for param in device.parameters:
                            text += param.name
                            text += "\n"
                        mylog(text)

        tracks_txt = ""
        for track in self.all_tracks:
            tracks_txt = tracks_txt + track.name + " : " + track.get_data("LITO_TR_ID", 'null') + "\n"
        myslog("\n---------------------------\nTracks list:\n" + str(tracks_txt)) # PERMANENT

        self.lad_save_param_cfg(True)

        for g in range(GROUP_CNT):
            key = "LITO_CFG_GRP" + str(g)
            cfg = self.song().get_data(key, "null")
            if cfg != "null":
                myslog("\n---------------------------\nStored configuration for group " + str(g) + "\n" + cfg) # PERMANENT
            else:
                myslog("\n---------------------------\nNo stored configuration for group " + str(g)) # PERMANENT




#    ## LAD MISC ###########################################################################################
    def lad_log_d(self, *msgs):
        mylog(msgs) # PERMANENT

    def lad_log_device_param(self, param):
        if do_param_log == False:
            return

        self.lad_log_d("--")
        device = param.canonical_parent
        if device != None:
            if not isinstance(device, Live.MixerDevice.MixerDevice):
                self.lad_log_d(device.name, ",", device.class_name, ",", device.class_display_name)
                self.lad_log_d(param.name, param.is_quantized, param.value, param.min, param.max)
                if param.is_quantized == True:
                    vals = []
                    self.lad_log_d("param.value_items len", len(param.value_items))
                    for val in param.value_items:
                        vals.append(val)
                    self.lad_log_d(vals)

#    ################################################################################################
#    ##  MORPH TAB

    def morph_init_cb(self):
        self.oscEndpoint.callbackManager.add("/morph/xy", self.morph_xy_cb)

    def morph_init(self):
        for g in range(GROUP_CNT):
            self.morph_set_current(g, "")
        return

    def morph_xy_cb(self, msg, source):
        # msg[2] ord
        # msg[3] abs

        val = msg[3]
        self.lad_faderm_input(1, float(val), False)
        address = "/lad/faderm1"
        self.oscEndpoint.send(address, float(val))
        val_midi = int(self.adaptValue(val, 0, 1.0, 0, 127))
        self.send_midi_ex((0xB0, const.MIDI_LAD_MORPH_SLIDER, val_midi), UTIL_TAB | LAD_TAB | MORPH_TAB)

        val = msg[2]
        self.lad_faderm_input(2, float(val), False)
        address = "/lad/faderm2"
        self.oscEndpoint.send(address, float(val))


        return

    def morph_set_current(self, group, text):
        group = group + 1
        address = "/morph/label_current" + str(group)
        self.oscEndpoint.send(address, text)
        return


#    ################################################################################################
#    ##  END OF MORPH TAB

#    ################################################################################################
#    ##  UTIL TAB

    util_apply_to_all_tr = False
    util_EQs_list = []
    util_comps_list = []
    util_debug = 0

    def util_update_disable_osc_gui(self):
        if self.oscEndpoint.get_disable_osc() == False:
            val = 1
        else:
            val = 0

        self.oscEndpoint.send("/util/led2", float(val))

        return

    def util_update_midi_button(self):

        for i in self.lad_midi_buttons:
            self.send_midi_ex((0xB0, i, 0), UTIL_TAB | LAD_TAB | MORPH_TAB)

        self.touch_send_midi_info(0, self.lad_show_display)
        if self.lad_perf_mode == False:
            self.touch_send_midi_info(1, self.lad_mixer)
        else:
            self.touch_send_midi_info(1, False)
        self.touch_send_midi_info(2, self.lad_perf_mode)
        self.touch_send_midi_info(3, False)
        self.touch_send_midi_info(4, self.lad_preset_rec_active)
        self.touch_send_midi_info(5, self.lad_morph)
        self.touch_send_midi_info(6, self.xtouch_lower_encoder)
        self.touch_send_midi_info(7, self.oscEndpoint.get_disable_osc())

        return

    def util_update_lower_gui(self):
        if self.xtouch_lower_encoder == True:
            val = 1
        else:
            val = 0

        self.oscEndpoint.send("/util/led1", float(val))
        self.touch_send_midi_info(6, self.xtouch_lower_encoder)

        return


    def util_init_cb(self):
        self.oscEndpoint.callbackManager.add("/util/push_test", self.util_test_cb)
        self.oscEndpoint.callbackManager.add("/util/push_sync", self.util_sync_cb)
        self.oscEndpoint.callbackManager.add("/util/push_noosc_phone", self.util_noosc_phone_cb)
        self.oscEndpoint.callbackManager.add("/util/push_noosc", self.util_noosc_cb)
        self.oscEndpoint.callbackManager.add("/util/push_sync_phone", self.util_sync_phone_cb)
        self.oscEndpoint.callbackManager.add("/util/toggle_all_tracks", self.util_apply_to_all_tracks_cb)
        self.oscEndpoint.callbackManager.add("/util/toggle_EQs", self.util_disable_fx_cb)
        self.oscEndpoint.callbackManager.add("/util/toggle_comps", self.util_disable_fx_cb)
        self.oscEndpoint.callbackManager.add("/util/push_export", self.util_export_cb)
        self.oscEndpoint.callbackManager.add("/util/push_load", self.util_load_cb)
        self.oscEndpoint.callbackManager.add("/util/push_patm", self.util_push_push_patm_cb)
        self.oscEndpoint.callbackManager.add("/util/push_patp", self.util_push_push_patp_cb)
        self.oscEndpoint.callbackManager.add("/util/push_create_clip", self.util_push_create_clip_cb)

        return

    def util_init(self):
        self.util_EQs_list = []
        self.util_comps_list = []
        self.util_apply_to_all_tr = False
        self.oscEndpoint.send("/util/toggle_all_tracks", float(0))
        self.oscEndpoint.send("/util/toggle_EQs", float(0))
        self.oscEndpoint.send("/util/toggle_comps", float(0))
        self.oscEndpoint.send("/util/label_pattern", "PATTERN")
        self.util_pattern = -1
        self.util_update_disable_osc_gui()

        self.util_debug = 0

        return

    def util_exit(self):
        self.util_init()
        self.oscEndpoint.set_disable_osc(True)
        self.touch_send_midi_info(7, self.oscEndpoint.get_disable_osc())
        self.util_update_disable_osc_gui()

        return

    def util_test_cb(self, msg, source):
        if msg[2] != 0:
            return
        self.test_fct()
        return

    def util_noosc_cb(self, msg, source):
        self.util_noosc_phone_cb(msg, source)
        return

    def util_noosc_phone_cb(self, msg, source):
        if msg[2] != 0:
            return

        self.oscEndpoint.set_disable_osc(True)
        self.util_update_disable_osc_gui()
        return

    def util_sync_phone_cb(self, msg, source):
        if msg[2] != 0:
            return
        self.wio_send_shutdown()
        self.oscEndpoint.set_wio_mode(False)
        self.oscEndpoint.set_phone_osc(True)
        self.FADER_CNT = 8
        self.util_sync_ext(msg, source)
        return

    def util_sync_cb(self, msg, source):
        if msg[2] != 0:
            return
        self.FADER_CNT = 16
        self.wio_send_shutdown()
        self.oscEndpoint.set_wio_mode(False)
        self.oscEndpoint.set_phone_osc(False)
        self.util_sync_ext(msg, source)
        return

    def util_sync_ext(self, msg, source):
        if msg[2] != 0:
            return

        self.oscEndpoint.setPeer_lt(msg, source)

        self.oscEndpoint.set_disable_osc(False)
        self.touch_send_midi_info(7, self.oscEndpoint.get_disable_osc())
        self.util_update_disable_osc_gui()
        self.clear_midi()
        self.lad_update() # util_sync_ext
        return

    def util_export_cb(self, msg, source):
        if msg[2] != 0:
            return

        self.lad_export_cfg() # util_export_cb
        return

    def util_reload(self):
        for i in range(GROUP_CNT):
            self.lad_clear_registered_obj(i)
        self.lad_set_info("")
        self.lad_load_param_live_cfg()
        self.lad_show_currents() # util_reload
        self.lad_export_cfg() # util_reload

    def util_load_cb(self, msg, source):
        if msg[2] != 0:
            return

        self.util_reload()
        return

    def util_apply_to_all_tracks_cb(self, msg, source):
        pressed = msg[2]
        self.util_apply_to_all_tracks(int(pressed))
        return

    def util_disable_fx_cb(self, msg, source):
        address = msg[0]
        pressed = msg[2]

        if address == "/util/toggle_EQs":
            self.util_disable_fx(1,int(pressed))
        elif address == "/util/toggle_comps":
            self.util_disable_fx(2,int(pressed))

        return

    def util_apply_to_all_tracks(self, on):
        if on:
            self.util_apply_to_all_tr = True
        else:
            self.util_apply_to_all_tr = False
        return

    def util_disable_fx(self, fx, disable):
        if disable:
            self.util_update_EQ_comp_list(fx)

        self.util_disable_devices(fx, disable)

        if disable == 0:
            self.util_clear_EQ_comp_list(fx)

        self.util_display_list()
        return

    def util_disable_devices(self, EQ, disable):
        if EQ == 1:
            list = self.util_EQs_list
        elif EQ == 2:
            list = self.util_comps_list


        for j in range(len(list)):
            if list[j] != None:
                if disable == True:
                    list[j].parameters[0].value = 0
                else:
                    list[j].parameters[0].value = 1

        return

    def util_append_list_EQ_comp_list(self, EQ, track):
        if EQ == 1:
            list = self.util_EQs_list
        elif EQ == 2:
            list = self.util_comps_list


        for j in range(len(track.devices)):
            device = track.devices[j]

            if device.parameters[0].value == 1:

                if EQ == 1:
                    if device.name == "EQ Eight":
                        list.append(device)
                    if device.name == "EQ Three":
                        list.append(device)
                    if device.name == "Channel EQ":
                        list.append(device)

                elif EQ == 2:
                    if device.name == "LoudMax":
                        list.append(device)
                    if device.name == "Glue Compressor":
                        list.append(device)
                    if device.name == "Compressor":
                        list.append(device)
        return

    def util_update_EQ_comp_list(self, EQ):
        if EQ == 1:
            list = self.util_EQs_list
        elif EQ == 2:
            list = self.util_comps_list


        if self.util_apply_to_all_tr == True:
            for i in range(len(self.all_tracks)):
                track = self.all_tracks[i]
                self.util_append_list_EQ_comp_list(EQ, track)
        else:
            track = self.song().view.selected_track
            self.util_append_list_EQ_comp_list(EQ, track)

        return

    def util_clear_EQ_comp_list(self, EQ):
        if EQ == 1:
            self.util_EQs_list = []
        elif EQ == 2:
            self.util_comps_list = []
        return

    def util_display_list(self):
        if self.util_debug == 1:
            myslog("**** EQ") # #### PERMANENT
            list = self.util_EQs_list
            for j in range(len(list)):
                if list[j] != None:
                    myslog(str(list[j].canonical_parent.name) + ":" + str(list[j].name)) # #### PERMANENT
            myslog("**** comp") # #### PERMANENT
            list = self.util_comps_list
            for j in range(len(list)):
                if list[j] != None:
                    myslog(str(list[j].canonical_parent.name) + ":" + str(list[j].name)) # #### PERMANENT

        return

    def util_update_phone_label(self, fader, text):
        address = "/util/labelf" + str(fader)
        self.oscEndpoint.send(address, text)
        self.wio_send_param_name2(fader, text)

    def test_fct(self):
        return

    util_pattern = -1

    def util_push_push_patm_cb(self, msg, source):
        if msg[2] != 0:
            return
        if self.util_pattern > 0:
            self.util_pattern = self.util_pattern - 1
        else:
            self.util_pattern = UTIL_MAX_PATTERN - 1
        text = "PATTERN " + str(self.util_pattern+1)
        self.oscEndpoint.send("/util/label_pattern", text)
        return

    def util_push_push_patp_cb(self, msg, source):
        if msg[2] != 0:
            return
        if self.util_pattern < (UTIL_MAX_PATTERN-1):
            self.util_pattern = self.util_pattern + 1
        else:
            self.util_pattern = 0
        text = "PATTERN " + str(self.util_pattern+1)
        self.oscEndpoint.send("/util/label_pattern", text)
        return

    def util_push_create_clip_cb(self, msg, source):
        if msg[2] != 0:
            return

        if self.util_pattern >= 0:
            if self.util_pattern < UTIL_MAX_PATTERN:
                lp = len(self.util_patterns[self.util_pattern])
                if (lp % 4) != 0:
                    mylog("bad pattern") # PERMANENT
                else:
                    clr = self.euc_new_clip(False, 4)
                    if clr != None:
                        new_notes = tuple()
                        for i in range(0,lp,4):
                            pattern = self.util_patterns[self.util_pattern]
                            nnote = ((pattern[i],pattern[i+1],pattern[i+2],pattern[i+3], 0),)
                            new_notes = new_notes + nnote
                        clr.replace_selected_notes(new_notes)

        return


    util_patterns = [
    [24, 2, 0.148027, 32, 27, 0.75, 0.147982, 32, 27, 2.75, 0.147982, 32, 39, 3, 0.148027, 32, 39, 3.75, 0.147982, 32, 48, 0.25, 0.147982, 32, 48, 1, 0.148027, 32, 48, 1.25, 0.147982, 64, 48, 3.25, 0.147982, 32, 51, 1.75, 0.147982, 64, 51, 2.5, 0.148027, 32, 51, 3.5, 0.148027, 32, 60, 0.5, 0.398005, 32, 60, 1.5, 0.148027, 32, 60, 2.25, 0.147982, 32, 61, 0, 0.398005, 64],
    [36, 3, 0.148027, 32, 36, 3.25, 0.147982, 32, 36, 3.75, 0.147982, 32, 48, 2.5, 0.148027, 64, 51, 0, 0.398005, 32, 51, 1.5, 0.148027, 64, 60, 1.25, 0.147982, 64, 60, 3.5, 0.148027, 64],
    [27, 2.75, 0.147982, 32, 36, 0.5, 0.148027, 32, 36, 1, 0.148027, 32, 36, 1.25, 0.147982, 32, 36, 1.75, 0.147982, 32, 36, 3, 0.148027, 32, 36, 3.25, 0.147982, 32, 36, 3.75, 0.147982, 32, 39, 0.75, 0.147982, 64, 46, 2.25, 0.147982, 32, 48, 0.25, 0.398005, 32, 48, 1.5, 0.148027, 32, 51, 2.5, 0.398005, 32, 58, 2, 0.398005, 32, 58, 3.5, 0.398005, 64, 60, 0, 0.398005, 64],
    [36, 0.25, 0.398005, 32, 36, 1, 0.148027, 32, 36, 1.5, 0.148027, 32, 36, 1.75, 0.147982, 32, 36, 2.25, 0.398005, 32, 36, 3, 0.148027, 32, 36, 3.5, 0.148027, 32, 36, 3.75, 0.147982, 32, 48, 0.75, 0.398005, 64, 48, 2.75, 0.398005, 64, 58, 0, 0.148027, 64, 58, 2, 0.148027, 64, 60, 1.25, 0.147982, 32, 60, 3.25, 0.147982, 32],
    [24, 0, 0.398005, 32, 24, 1.5, 0.398005, 32, 28, 0.75, 0.398005, 32, 31, 0.25, 0.398005, 32, 43, 2.25, 0.147982, 32, 43, 3, 0.398005, 32, 47, 1.75, 0.147982, 32, 47, 2, 0.148027, 64, 47, 3.25, 0.398005, 32, 48, 1, 0.398005, 32, 55, 0.5, 0.148027, 32, 55, 2.5, 0.648027, 64, 60, 1.25, 0.147982, 32, 60, 3.5, 0.5, 32],
    [24, 1.75, 0.647982, 64, 26, 1, 0.398005, 64, 34, 1.5, 0.148027, 32, 36, 0.25, 0.398005, 32, 36, 2.5, 0.148027, 64, 36, 3.25, 0.147982, 64, 36, 3.5, 0.148027, 64, 43, 0.5, 0.148027, 32, 43, 0.75, 0.147982, 32, 48, 0, 0.148027, 64, 48, 1.25, 0.398005, 64, 58, 2.25, 0.147982, 32, 60, 2.75, 0.398005, 32, 62, 3, 0.398005, 64, 67, 3.75, 0.249977, 32],
    [36, 0, 0.148027, 32, 36, 0.25, 0.147982, 32, 36, 2.75, 0.147982, 64, 36, 3, 0.148027, 32, 36, 3.25, 0.147982, 32, 36, 3.5, 0.148027, 32, 36, 3.75, 0.147982, 32, 43, 1.5, 0.148027, 32, 43, 1.75, 0.398005, 64, 45, 0.5, 0.148027, 32, 46, 0.75, 0.398005, 32, 46, 2.25, 0.147982, 32, 46, 2.5, 0.398005, 64, 50, 1, 0.148027, 32, 50, 1.25, 0.147982, 32],
    [31, 2, 0.148027, 32, 31, 2.75, 0.398005, 64, 35, 0.75, 0.147982, 32, 36, 3.5, 0.148027, 64, 40, 1, 0.148027, 64, 40, 2.5, 0.148027, 32, 47, 0.25, 0.147982, 32, 47, 3.25, 0.147982, 32, 48, 0, 0.398005, 32, 48, 3.75, 0.147982, 32, 52, 1.75, 0.398005, 32, 52, 2.25, 0.147982, 64, 55, 1.5, 0.398005, 32, 59, 0.5, 0.148027, 32, 59, 1.25, 0.398005, 32],
    [31, 1.75, 0.147982, 32, 31, 3.75, 0.249977, 32, 34, 3.25, 0.147982, 32, 34, 3.5, 0.148027, 64, 36, 1.25, 0.147982, 32, 39, 2.5, 0.398005, 32, 43, 1.5, 0.398005, 32, 43, 2.25, 0.147982, 32, 43, 3, 0.398005, 32, 46, 0.5, 0.148027, 32, 48, 0.25, 0.147982, 32, 48, 0.75, 0.147982, 32, 55, 1, 0.148027, 32, 58, 0, 0.398005, 32, 58, 2.75, 0.147982, 32, 60, 2, 0.148027, 64],
    [24, 3, 0.148027, 32, 28, 0.5, 0.148027, 32, 28, 2.25, 0.147982, 32, 31, 1.5, 0.148027, 32, 36, 3.75, 0.147982, 64, 40, 2.5, 0.398005, 64, 43, 0.25, 0.147982, 32, 47, 3.25, 0.398005, 32, 48, 1, 0.148027, 32, 48, 2.75, 0.147982, 32, 48, 3.5, 0.148027, 32, 55, 0, 0.148027, 32, 55, 0.75, 0.147982, 64, 55, 1.25, 0.398005, 32, 59, 2, 0.148027, 32, 60, 1.75, 0.147982, 32],
    [27, 3.25, 0.130249, 64, 37, 1.75, 0.385805, 32, 39, 0.25, 0.130249, 32, 39, 0.75, 0.885805, 64, 39, 2, 0.410249, 64, 39, 3, 0.165805, 32, 46, 0.5, 0.165805, 32, 46, 2.5, 0.165805, 32, 49, 1.5, 0.165805, 32, 51, 0, 0.165805, 64, 51, 2.25, 0.385805, 64, 55, 3.5, 0.410249, 64, 63, 3.75, 0.130249, 64],
    [26, 1.25, 0.147982, 32, 33, 2.75, 0.147982, 64, 36, 3.75, 0.147982, 32, 38, 0.25, 0.147982, 32, 38, 1.5, 0.148027, 64, 38, 3.5, 0.148027, 32, 43, 1, 0.148027, 32, 43, 2.5, 0.148027, 32, 43, 3.25, 0.147982, 32, 45, 3, 0.148027, 32, 50, 0.5, 0.148027, 32, 50, 0.75, 0.147982, 64, 62, 0, 0.148027, 64, 62, 2, 0.148027, 32],
    [24, 1, 0.420045, 32, 24, 2, 0.18, 32, 24, 2.25, 0.116009, 32, 24, 3, 0.18, 64, 24, 3.5, 0.18, 32, 36, 1.25, 0.116009, 32, 39, 2.75, 0.116009, 32, 39, 3.75, 0.195964, 32, 41, 0.5, 0.18, 32, 43, 3.25, 0.116009, 32, 48, 0.75, 0.116009, 64, 51, 1.75, 0.375964, 32, 60, 1.5, 0.18, 64, 67, 2.5, 0.18, 32, 72, 0, 0.18, 32, 72, 0.25, 0.116009, 64],
    [24, 0.5, 0.169342, 32, 24, 0.75, 0.126667, 64, 36, 0, 0.412699, 64, 36, 1.25, 0.126667, 32, 36, 1.5, 0.169342, 64, 36, 1.75, 0.383311, 64, 36, 3.25, 0.126667, 32, 36, 3.75, 0.126667, 32, 43, 2.5, 0.169342, 32, 43, 2.75, 0.126667, 32, 46, 3.5, 0.412699, 32, 63, 1, 0.169342, 32, 63, 3, 0.412699, 64],
    [27, 3.25, 0.147982, 64, 35, 3.5, 0.398005, 32, 44, 2, 0.25, 32, 44, 2.25, 0.147982, 64, 44, 3.75, 0.147982, 64, 47, 2.75, 0.147982, 32, 51, 0.25, 0.249977, 32, 51, 0.5, 0.148027, 64, 51, 0.75, 0.249977, 32, 51, 1, 0.148027, 64, 51, 1.5, 0.25, 32, 51, 1.75, 0.147982, 64],
    [28, 0.5, 0.148027, 32, 28, 1.25, 0.147982, 32, 28, 2, 0.148027, 32, 28, 2.75, 0.147982, 32, 28, 3.5, 0.148027, 32, 29, 3.75, 0.147982, 32, 34, 0.25, 0.147982, 32, 34, 1, 0.148027, 32, 34, 1.75, 0.147982, 32, 34, 2.5, 0.148027, 32, 34, 3.25, 0.147982, 32, 40, 0, 0.148027, 64, 40, 0.75, 0.147982, 32, 40, 1.5, 0.148027, 32, 40, 2.25, 0.147982, 64, 40, 3, 0.148027, 32],
    [24, 0.25, 0.147982, 64, 31, 0.75, 0.147982, 32, 34, 0, 0.148027, 32, 34, 2.25, 0.147982, 32, 34, 3.5, 0.148027, 32, 36, 1, 0.148027, 64, 36, 2.75, 0.147982, 32, 36, 3.25, 0.147982, 32, 40, 3.75, 0.147982, 32, 46, 1.75, 0.147982, 32, 48, 0.5, 0.148027, 64, 52, 2, 0.148027, 32, 55, 2.5, 0.148027, 32, 58, 1.5, 0.148027, 64, 60, 1.25, 0.147982, 32, 60, 3, 0.148027, 64],
    [24, 3, 0.398005, 32, 27, 0.5, 0.398005, 64, 27, 1.75, 0.147982, 64, 36, 0.25, 0.147982, 32, 36, 1.25, 0.147982, 32, 36, 2.25, 0.147982, 32, 36, 2.5, 0.148027, 32, 36, 2.75, 0.147982, 32, 48, 0, 0.148027, 32, 51, 0.75, 0.147982, 32, 51, 1.5, 0.398005, 32, 51, 2, 0.398005, 64, 58, 3.25, 0.398005, 64, 60, 1, 0.398005, 64, 60, 3.75, 0.249977, 32],
    [24, 2.25, 0.147982, 32, 36, 0, 0.648027, 32, 36, 1, 0.148027, 32, 36, 1.25, 0.147982, 64, 36, 1.75, 0.147982, 32, 36, 2, 0.148027, 64, 36, 2.5, 0.148027, 32, 36, 3.75, 0.147982, 32, 39, 1.5, 0.148027, 32, 48, 2.75, 0.398005, 32, 60, 0.75, 0.398005, 32, 60, 3, 0.148027, 32, 60, 3.25, 0.147982, 64, 60, 3.5, 0.148027, 32],
    [24, 1, 0.148027, 32, 24, 2.75, 0.147982, 32, 31, 3.25, 0.147982, 64, 36, 1.75, 0.147982, 64, 36, 3.75, 0.147982, 32, 48, 0, 0.148027, 64, 48, 1.25, 0.147982, 64, 51, 2, 0.148027, 64, 55, 0.5, 0.148027, 32, 60, 3, 0.398005, 64, 60, 3.5, 0.398005, 64, 63, 1.5, 0.148027, 32, 63, 2.5, 0.148027, 64, 67, 0.25, 0.147982, 64],
    [24, 2.75, 0.147982, 64, 34, 2.5, 0.398005, 32, 36, 0, 0.148027, 32, 36, 1, 0.148027, 32, 36, 1.75, 0.147982, 64, 36, 2, 0.148027, 32, 36, 3, 0.148027, 32, 36, 3.25, 0.147982, 64, 36, 3.75, 0.147982, 32, 42, 0.25, 0.147982, 64, 48, 0.75, 0.147982, 32, 54, 0.5, 0.148027, 32, 55, 1.25, 0.249977, 32, 55, 1.5, 0.148027, 64, 58, 2.25, 0.398005, 32, 60, 3.5, 0.398005, 64],
    [24, 3, 0.148027, 32, 24, 3.25, 0.147982, 32, 36, 0.5, 0.398005, 64, 36, 1.5, 0.148027, 32, 48, 2, 0.148027, 32, 51, 3.5, 0.398005, 32],
    [24, 0.25, 0.147982, 32, 24, 0.75, 0.147982, 32, 24, 2, 0.148027, 32, 24, 3, 0.398005, 32, 36, 0, 0.148027, 32, 36, 0.5, 0.398005, 32, 36, 1.5, 0.148027, 64, 36, 1.75, 0.147982, 32, 36, 2.75, 0.147982, 32, 44, 1, 0.398005, 32, 48, 2.25, 0.147982, 64, 48, 2.5, 0.148027, 32, 48, 3.25, 0.147982, 32, 48, 3.5, 0.5, 32],
    [24, 0.25, 0.147982, 32, 36, 0, 0.148027, 32, 36, 0.5, 0.148027, 32, 36, 1, 0.148027, 32, 36, 1.25, 0.147982, 32, 36, 1.5, 0.148027, 64, 36, 1.75, 0.147982, 32, 36, 2, 0.148027, 32, 36, 2.25, 0.147982, 32, 36, 2.5, 0.148027, 32, 36, 2.75, 0.147982, 32, 48, 0.75, 0.147982, 64, 48, 3.5, 0.398005, 32, 60, 3, 0.648027, 32],
    [31, 2, 0.148027, 32, 36, 0, 0.148027, 32, 36, 0.25, 0.147982, 32, 36, 0.5, 0.148027, 32, 36, 1, 0.148027, 32, 36, 1.25, 0.147982, 32, 36, 2.25, 0.147982, 32, 36, 2.5, 0.148027, 32, 36, 2.75, 0.147982, 32, 51, 3, 0.648027, 64, 55, 1.5, 0.148027, 64, 55, 1.75, 0.398005, 32, 56, 0.75, 0.147982, 64, 60, 3.5, 0.398005, 32],
    [24, 0.75, 0.147982, 32, 24, 1, 0.148027, 32, 36, 0, 0.148027, 32, 36, 0.25, 0.147982, 32, 36, 1.75, 0.147982, 32, 36, 2, 0.25, 32, 36, 2.25, 0.147982, 64, 36, 3, 0.398005, 64, 44, 1.25, 0.398005, 64, 48, 0.5, 0.398005, 32, 55, 3.75, 0.147982, 32, 56, 3.5, 0.148027, 32, 60, 2.5, 0.398005, 32],
    [24, 3.25, 0.647982, 32, 36, 0.75, 0.398005, 64, 36, 1.75, 0.147982, 32, 36, 3, 0.148027, 32, 48, 1.5, 0.148027, 32, 51, 0.25, 0.398005, 32, 60, 1, 0.148027, 32, 60, 2.75, 0.398005, 32, 60, 3.75, 0.147982, 32],
    [25, 1.75, 0.147982, 32, 27, 3.75, 0.147982, 32, 28, 2.5, 0.148027, 64, 31, 3.25, 0.398005, 32, 34, 3, 0.148027, 32, 37, 0.75, 0.398005, 64, 39, 2.25, 0.147982, 32, 40, 1, 0.148027, 32, 40, 3.5, 0.398005, 32, 46, 0, 0.148027, 64, 51, 2.75, 0.398005, 32, 52, 1.5, 0.148027, 32, 55, 0.5, 0.148027, 32, 58, 0.25, 0.398005, 32],
    [24, 2.25, 0.147982, 64, 25, 1.5, 0.398005, 64, 27, 2.5, 0.148027, 32, 31, 2.75, 0.147982, 32, 31, 3.5, 0.398005, 32, 36, 0.75, 0.147982, 32, 36, 3.25, 0.147982, 64, 38, 1.75, 0.147982, 32, 46, 1.25, 0.147982, 64, 50, 1, 0.398005, 32, 50, 2, 0.398005, 32, 57, 0, 0.148027, 64, 68, 3.75, 0.147982, 64, 72, 0.25, 0.147982, 64],
    [50, 0, 0.148027, 32, 50, 0.25, 0.147982, 32, 50, 1, 0.148027, 64, 50, 1.5, 0.148027, 32, 50, 1.75, 0.147982, 32, 52, 0.5, 0.148027, 32, 52, 0.75, 0.147982, 32, 52, 1.25, 0.147982, 32, 52, 2.25, 0.5, 32, 52, 2.75, 0.147982, 64, 52, 3, 0.398005, 64, 55, 2, 0.148027, 32, 55, 3.5, 0.5, 32],
    [36, 0, 0.148027, 32, 36, 1.5, 0.148027, 32, 36, 2, 0.148027, 32, 36, 3.5, 0.148027, 32, 42, 0.5, 0.398005, 64, 42, 1.75, 0.398005, 32, 42, 2.5, 0.398005, 64, 42, 3.75, 0.249977, 32, 54, 0.75, 0.147982, 32, 54, 2.75, 0.147982, 32, 57, 0.25, 0.147982, 32, 57, 2.25, 0.147982, 32],
    [31, 3.25, 0.147982, 64, 36, 0, 0.148027, 32, 36, 0.25, 0.147982, 64, 36, 0.75, 0.147982, 32, 36, 1, 0.148027, 32, 36, 1.5, 0.148027, 32, 36, 1.75, 0.147982, 32, 36, 2, 0.148027, 32, 36, 2.25, 0.147982, 32, 43, 3.5, 0.398005, 32, 46, 1.25, 0.147982, 32, 46, 2.5, 0.398005, 32, 48, 0.5, 0.148027, 32, 55, 3, 0.148027, 32],
    [24, 0.25, 0.147982, 64, 24, 0.5, 0.148027, 32, 24, 1, 0.148027, 32, 24, 3.25, 0.147982, 32, 28, 3.75, 0.147982, 32, 35, 1.25, 0.147982, 64, 35, 2.5, 0.148027, 32, 35, 2.75, 0.147982, 32, 36, 1.5, 0.148027, 32, 36, 1.75, 0.147982, 64, 43, 2.25, 0.147982, 32, 48, 0.75, 0.147982, 64, 48, 3.5, 0.148027, 64, 55, 0, 0.148027, 64, 55, 3, 0.148027, 32, 60, 2, 0.148027, 64],
    [32, 0, 0.398005, 32, 32, 0.5, 0.398005, 32, 32, 1, 0.398005, 32, 32, 1.5, 0.398005, 32, 44, 0.25, 0.398005, 32, 44, 0.75, 0.398005, 32, 44, 1.25, 0.398005, 32, 44, 1.75, 0.398005, 32, 56, 2.25, 0.147982, 64, 56, 2.5, 0.148027, 64, 56, 2.75, 0.398005, 64, 56, 3.25, 0.147982, 64, 56, 3.75, 0.147982, 64],
    [33, 0.25, 0.398005, 32, 33, 0.75, 0.398005, 32, 40, 2.5, 0.148027, 64, 40, 3.5, 0.148027, 32, 45, 0, 0.398005, 32, 45, 0.5, 0.398005, 32, 45, 1.5, 0.148027, 64, 52, 1.75, 0.147982, 32],
    [33, 2, 1.898, 32, 36, 3.75, 0.147982, 32, 40, 0.5, 0.898005, 64, 41, 0, 0.148027, 64, 45, 1.5, 0.148027, 32],
    [32, 0.25, 0.398005, 32, 32, 1, 0.398005, 32, 32, 1.75, 0.398005, 32, 32, 2.5, 0.398005, 32, 32, 3.25, 0.398005, 32, 44, 0, 0.148027, 64, 44, 0.5, 0.148027, 32, 44, 0.75, 0.147982, 64, 44, 1.25, 0.147982, 32, 44, 1.5, 0.148027, 64, 44, 2, 0.148027, 32, 44, 2.25, 0.147982, 64, 44, 2.75, 0.147982, 32, 44, 3, 0.148027, 64, 44, 3.5, 0.148027, 32, 44, 3.75, 0.147982, 64],
    [32, 0.5, 0.148027, 64, 32, 1.25, 0.147982, 64, 32, 3, 0.148027, 64, 32, 3.75, 0.147982, 64, 35, 0.75, 0.398005, 32, 35, 3.25, 0.398005, 64, 39, 0.25, 0.147982, 32, 39, 1.75, 0.147982, 32],
    [26, 2.25, 0.147982, 64, 26, 3, 0.148027, 64, 34, 0.5, 0.148027, 64, 38, 1.5, 0.398005, 32, 39, 1.25, 0.147982, 64, 41, 0.75, 0.398005, 64, 42, 3.5, 0.148027, 64, 44, 0.25, 0.398005, 32, 46, 3.75, 0.147982, 64, 47, 1.75, 0.147982, 64, 48, 3.25, 0.398005, 32, 52, 2.75, 0.147982, 32, 53, 0, 0.148027, 64, 56, 1, 0.148027, 32, 56, 2, 0.148027, 32, 59, 2.5, 0.148027, 32],
    [24, 2.25, 0.147982, 64, 28, 3.5, 0.148027, 64, 35, 2, 0.398005, 64, 36, 1.5, 0.148027, 32, 38, 3, 0.148027, 32, 39, 1.75, 0.398005, 32, 41, 0.5, 0.148027, 64, 48, 0.75, 0.147982, 64, 50, 3.75, 0.147982, 32, 53, 0, 0.148027, 64, 56, 1, 0.398005, 64],
    [25, 2, 0.398005, 32, 28, 0.75, 0.147982, 64, 32, 0.5, 0.148027, 32, 33, 3.75, 0.147982, 32, 35, 3, 0.148027, 32, 40, 0, 0.148027, 64, 40, 2.5, 0.148027, 32, 42, 3.25, 0.398005, 32, 43, 0.25, 0.147982, 64, 44, 1.25, 0.147982, 32, 46, 1.5, 0.148027, 32, 51, 1, 0.148027, 32, 51, 2.25, 0.147982, 32, 53, 3.5, 0.148027, 32, 54, 2.75, 0.147982, 32, 55, 1.75, 0.398005, 32],
    [24, 1.25, 0.398005, 32, 24, 3.75, 0.249977, 32, 30, 2, 0.398005, 32, 36, 1.5, 0.148027, 32, 36, 2.25, 0.147982, 32, 41, 0.5, 0.148027, 64, 41, 3, 0.148027, 64, 42, 0.25, 0.147982, 64, 42, 0.75, 0.147982, 64, 42, 1.75, 0.398005, 32, 42, 2.75, 0.147982, 64, 42, 3.25, 0.147982, 64, 43, 0, 0.148027, 64, 43, 1, 0.398005, 32, 43, 2.5, 0.148027, 64, 43, 3.5, 0.398005, 32],
    [27, 1.75, 0.398005, 32, 27, 2.25, 0.147982, 32, 27, 3, 0.148027, 64, 30, 1.5, 0.398005, 32, 36, 0.25, 0.398005, 32, 39, 0.5, 0.148027, 32, 39, 1, 0.148027, 32, 39, 3.75, 0.147982, 32, 42, 0.75, 0.147982, 64, 42, 1.25, 0.147982, 32, 42, 2.75, 0.398005, 64, 42, 3.5, 0.148027, 64, 48, 2, 0.148027, 32, 54, 3.25, 0.147982, 32, 60, 0, 0.398005, 32, 60, 2.5, 0.398005, 32],
    [24, 1.25, 0.147982, 64, 24, 3.25, 0.147982, 64, 31, 1, 0.148027, 32, 31, 3, 0.148027, 32, 36, 1.75, 0.147982, 64, 36, 3.75, 0.147982, 64, 48, 0, 0.148027, 32, 48, 0.5, 0.148027, 32, 48, 1.5, 0.398005, 32, 48, 2, 0.148027, 32, 48, 2.5, 0.148027, 32, 48, 3.5, 0.398005, 32, 55, 0.75, 0.398005, 32, 55, 2.75, 0.398005, 32, 56, 0.25, 0.147982, 64, 56, 2.25, 0.147982, 64],
    [27, 2.25, 0.147982, 32, 30, 3.25, 0.147982, 64, 34, 0.25, 0.147982, 64, 34, 1.25, 0.147982, 64, 34, 3, 0.148027, 64, 34, 3.5, 0.148027, 32, 36, 1.5, 0.148027, 32, 39, 1, 0.148027, 32, 46, 2.75, 0.398005, 64, 48, 0.5, 0.148027, 32, 48, 0.75, 0.147982, 64, 48, 3.75, 0.249977, 32, 51, 0, 0.398005, 64, 51, 2, 0.398005, 32, 51, 2.5, 0.148027, 32, 60, 1.75, 0.147982, 64],
    [39, 0.25, 0.147982, 32, 39, 1.25, 0.147982, 32, 39, 2.25, 0.147982, 32, 39, 3.25, 0.147982, 32, 43, 0.5, 0.148027, 64, 43, 1.5, 0.148027, 64, 43, 2.5, 0.148027, 64, 43, 3.5, 0.148027, 64, 54, 0.75, 0.398005, 32, 54, 1.75, 0.398005, 32, 54, 2.75, 0.398005, 32, 54, 3.75, 0.249977, 32, 57, 0, 0.148027, 32, 57, 1, 0.148027, 32, 57, 2, 0.148027, 32, 57, 3, 0.148027, 32],
    [27, 0.5, 0.148027, 32, 27, 1.75, 0.147982, 32, 27, 3, 0.148027, 32, 29, 1, 0.148027, 32, 29, 2.25, 0.147982, 32, 29, 3.5, 0.148027, 32, 30, 0, 0.148027, 64, 30, 1.25, 0.147982, 64, 30, 2.5, 0.148027, 64, 30, 3.75, 0.147982, 64, 32, 0.75, 0.398005, 32, 32, 2, 0.398005, 32, 32, 3.25, 0.398005, 32, 41, 0.25, 0.147982, 32, 41, 1.5, 0.148027, 32, 41, 2.75, 0.147982, 32],
    [24, 1, 0.398005, 32, 24, 1.75, 0.147982, 32, 30, 0.75, 0.147982, 64, 30, 3.75, 0.147982, 64, 32, 0.25, 0.147982, 32, 32, 1.25, 0.147982, 32, 32, 3.25, 0.147982, 32, 43, 2.5, 0.148027, 32, 44, 1.5, 0.398005, 32, 44, 2, 0.148027, 32, 54, 2.75, 0.147982, 32, 56, 0, 0.398005, 32, 56, 3, 0.398005, 32, 60, 0.5, 0.148027, 32, 60, 2.25, 0.398005, 64, 60, 3.5, 0.148027, 32],
    [32, 0.25, 0.398005, 32, 32, 1, 0.398005, 32, 32, 1.75, 0.398005, 64, 32, 2.75, 0.147982, 32, 32, 3.25, 0.398005, 32, 34, 0.5, 0.148027, 32, 34, 3.5, 0.148027, 32, 43, 0, 0.398005, 32, 43, 0.75, 0.147982, 64, 43, 1.25, 0.147982, 32, 43, 3, 0.398005, 32, 43, 3.75, 0.147982, 64, 44, 1.5, 0.148027, 32, 44, 2, 0.148027, 32, 44, 2.25, 0.398005, 32],
    [31, 1.5, 0.148027, 32, 31, 2.25, 0.147982, 32, 34, 0, 0.148027, 32, 34, 0.25, 0.147982, 32, 34, 0.5, 0.148027, 32, 34, 0.75, 0.147982, 64, 34, 3, 0.148027, 32, 34, 3.25, 0.147982, 32, 34, 3.5, 0.148027, 32, 34, 3.75, 0.147982, 64, 44, 1, 0.148027, 32, 44, 1.25, 0.398005, 32, 44, 1.75, 0.147982, 64, 46, 2, 0.398005, 32, 46, 2.5, 0.398005, 64],
    [28, 1.5, 0.398005, 32, 28, 3.5, 0.398005, 32, 38, 1, 0.148027, 32, 38, 3, 0.148027, 32, 40, 0, 0.148027, 64, 40, 0.25, 0.147982, 32, 40, 0.5, 0.148027, 32, 40, 0.75, 0.147982, 64, 40, 2, 0.148027, 64, 40, 2.25, 0.147982, 32, 40, 2.5, 0.148027, 32, 40, 2.75, 0.147982, 64, 52, 1.75, 0.147982, 32, 52, 3.75, 0.147982, 32, 53, 1.25, 0.147982, 32, 53, 3.25, 0.147982, 32],
    [27, 2, 0.148027, 32, 28, 0.5, 0.148027, 32, 28, 1.25, 0.147982, 32, 28, 3, 0.148027, 32, 28, 3.75, 0.147982, 32, 29, 0.25, 0.147982, 32, 29, 1, 0.398005, 32, 29, 2.75, 0.147982, 32, 29, 3.5, 0.398005, 32, 32, 1.75, 0.147982, 64, 33, 0, 0.148027, 64, 33, 2.5, 0.148027, 64, 34, 0.75, 0.147982, 32, 34, 3.25, 0.147982, 32, 53, 2.25, 0.147982, 32, 58, 1.5, 0.148027, 32],
    [28, 2.25, 0.147982, 64, 32, 0.5, 0.398005, 32, 32, 1.75, 0.398005, 32, 32, 3, 0.398005, 32, 43, 0.25, 0.147982, 32, 43, 1.5, 0.148027, 32, 43, 2.75, 0.147982, 32, 44, 0, 0.148027, 32, 44, 0.75, 0.147982, 32, 44, 1.25, 0.147982, 64, 44, 2, 0.148027, 32, 44, 2.5, 0.148027, 32, 44, 3.25, 0.147982, 32, 44, 3.75, 0.147982, 64, 57, 1, 0.148027, 64, 57, 3.5, 0.148027, 64],
    [27, 2.5, 0.148027, 32, 34, 1.75, 0.147982, 32, 36, 0, 0.398005, 32, 36, 0.5, 0.148027, 32, 36, 1, 0.148027, 32, 36, 3, 0.148027, 32, 36, 3.5, 0.148027, 32, 46, 1.25, 0.147982, 32, 46, 1.5, 0.148027, 32, 46, 3.25, 0.398005, 32, 48, 0.75, 0.398005, 32, 48, 2, 0.148027, 64, 48, 3.75, 0.147982, 32, 51, 2.25, 0.147982, 32, 51, 2.75, 0.398005, 32],
    [25, 0.25, 0.147982, 32, 25, 1.75, 0.147982, 32, 25, 3.25, 0.147982, 32, 33, 1.25, 0.147982, 32, 33, 2.75, 0.147982, 32, 34, 0, 0.398005, 64, 34, 1.5, 0.398005, 64, 34, 3, 0.398005, 64, 46, 0.5, 0.148027, 32, 46, 0.75, 0.398005, 32, 46, 2, 0.148027, 32, 46, 2.25, 0.398005, 32, 46, 3.5, 0.148027, 32, 46, 3.75, 0.249977, 32, 49, 1, 0.398005, 64, 49, 2.5, 0.398005, 64],
    [30, 1.5, 0.148027, 32, 30, 1.75, 0.147982, 64, 30, 3.25, 0.147982, 32, 35, 0, 0.398005, 64, 35, 2.75, 0.147982, 64, 38, 0.5, 0.398005, 64, 45, 3.75, 0.147982, 32, 50, 0.75, 0.147982, 32, 54, 1, 0.148027, 64, 54, 3, 0.398005, 32, 57, 3.5, 0.398005, 32, 59, 0.25, 0.147982, 32, 59, 2, 0.648027, 64],
    [36, 0, 0.398005, 64, 36, 1, 0.148027, 64, 36, 1.25, 0.147982, 64, 36, 2, 0.148027, 64, 36, 2.25, 0.147982, 64, 36, 2.5, 0.148027, 64, 36, 2.75, 0.147982, 64, 36, 3.5, 0.398005, 64, 51, 1.5, 0.398005, 64, 55, 3, 0.148027, 64, 55, 3.25, 0.147982, 64, 60, 0.5, 0.148027, 64, 60, 0.75, 0.147982, 64],
    [24, 0.25, 0.147982, 32, 24, 1, 0.398005, 64, 24, 2.25, 0.147982, 32, 24, 3, 0.398005, 64, 27, 0, 0.148027, 32, 27, 2, 0.148027, 32, 34, 0.5, 0.398005, 32, 34, 2.5, 0.398005, 32, 36, 1.5, 0.148027, 32, 36, 3.5, 0.148027, 32, 58, 0.75, 0.147982, 32, 58, 1.75, 0.398005, 32, 58, 2.75, 0.147982, 32, 58, 3.75, 0.249977, 32, 60, 1.25, 0.398005, 32, 60, 3.25, 0.398005, 32],
    [24, 0.5, 0.148027, 32, 24, 1.75, 0.147982, 32, 24, 2.5, 0.148027, 32, 24, 3.75, 0.147982, 32, 28, 1, 0.148027, 32, 28, 3, 0.148027, 32, 36, 1.25, 0.147982, 32, 36, 3.25, 0.147982, 32, 48, 0, 0.148027, 32, 48, 0.25, 0.147982, 32, 48, 1.5, 0.148027, 32, 48, 2, 0.148027, 32, 48, 2.25, 0.147982, 32, 48, 3.5, 0.148027, 32, 52, 0.75, 0.398005, 32, 52, 2.75, 0.398005, 32],
    [26, 0, 0.148027, 64, 26, 0.25, 0.147982, 32, 36, 2.75, 0.398005, 64, 36, 3.5, 0.398005, 32, 38, 0.5, 0.398005, 64, 38, 1.25, 0.398005, 32, 38, 2, 0.148027, 32, 38, 2.25, 0.147982, 64, 38, 2.5, 0.148027, 64, 38, 3.25, 0.147982, 32, 48, 3.75, 0.147982, 32, 50, 1.75, 0.398005, 32],
    [34, 0, 0.398005, 32, 34, 1.5, 0.148027, 64, 34, 2, 0.398005, 32, 34, 3.5, 0.148027, 64, 46, 0.25, 0.147982, 32, 46, 0.5, 0.148027, 32, 46, 0.75, 0.147982, 32, 46, 1.25, 0.147982, 32, 46, 2.25, 0.147982, 32, 46, 2.5, 0.148027, 32, 46, 2.75, 0.147982, 32, 46, 3.25, 0.147982, 32, 47, 1.75, 0.147982, 32, 47, 3.75, 0.147982, 32, 58, 1, 0.148027, 32, 58, 3, 0.148027, 32],
    [24, 0, 0.148027, 32, 24, 0.75, 0.398005, 32, 24, 2.75, 0.147982, 32, 24, 3.5, 0.148027, 32, 36, 1.5, 0.148027, 32, 36, 1.75, 0.147982, 32, 36, 2, 0.148027, 32, 36, 2.25, 0.147982, 32, 36, 3, 0.148027, 32, 48, 1, 0.148027, 32, 48, 1.25, 0.147982, 32, 48, 3.25, 0.398005, 64, 60, 0.5, 0.148027, 32, 60, 2.5, 0.398005, 32],
    [41, 0.25, 0.147982, 32, 41, 1.25, 0.147982, 32, 41, 1.75, 0.147982, 32, 41, 2, 0.148027, 32, 41, 2.5, 0.148027, 32, 41, 2.75, 0.147982, 32, 41, 3.25, 0.147982, 32, 41, 3.75, 0.147982, 32, 53, 0.5, 0.148027, 32, 53, 3, 0.398005, 32, 56, 1, 0.398005, 32, 56, 3.5, 0.148027, 64, 58, 0, 0.148027, 32, 58, 0.75, 0.147982, 64, 58, 1.5, 0.148027, 32, 58, 2.25, 0.398005, 32],
    [33, 0.5, 0.398005, 32, 33, 2.25, 0.398005, 32, 52, 1.5, 0.148027, 32, 52, 3.25, 0.147982, 32, 57, 0, 0.148027, 64, 57, 0.25, 0.147982, 64, 57, 0.75, 0.147982, 32, 57, 1.75, 0.147982, 64, 57, 2, 0.148027, 64, 57, 2.5, 0.148027, 32, 57, 3.5, 0.148027, 64, 57, 3.75, 0.147982, 64, 60, 1, 0.398005, 32, 60, 2.75, 0.398005, 32],
    [27, 3.25, 0.147982, 32, 29, 1.25, 0.147982, 32, 30, 2.5, 0.148027, 32, 32, 2, 0.148027, 32, 34, 3.75, 0.147982, 32, 51, 0.75, 0.147982, 32, 51, 3, 0.148027, 32, 52, 2.75, 0.398005, 32, 53, 0.5, 0.148027, 32, 53, 1, 0.148027, 32, 53, 3.5, 0.148027, 32, 54, 2.25, 0.147982, 32, 55, 1.5, 0.148027, 32, 56, 1.75, 0.398005, 32, 57, 0.25, 0.147982, 32, 58, 0, 0.148027, 32],
    [34, 0.75, 0.147982, 32, 34, 1.75, 0.147982, 64, 34, 2.5, 0.648027, 64, 34, 3.25, 0.398005, 64, 34, 3.75, 0.147982, 64, 42, 0, 0.148027, 32, 42, 0.25, 0.147982, 32, 42, 1.25, 0.147982, 64, 42, 2, 0.398005, 32, 46, 0.5, 0.148027, 64, 46, 2.25, 0.147982, 32, 54, 1.5, 0.398005, 32, 54, 3.5, 0.148027, 64, 58, 1, 0.398005, 64, 58, 3, 0.398005, 32],
    [24, 3, 0.148027, 64, 27, 0, 0.398005, 64, 27, 0.75, 0.398005, 32, 27, 1.75, 0.398005, 64, 36, 1.25, 0.398005, 32, 36, 3.25, 0.398005, 32, 39, 2, 0.398005, 32, 39, 2.75, 0.398005, 64, 43, 1.5, 0.398005, 64, 43, 2.25, 0.147982, 32, 43, 3.75, 0.147982, 64, 48, 0.5, 0.398005, 64, 55, 1, 0.398005, 64, 55, 3.5, 0.148027, 64, 60, 0.25, 0.147982, 32, 60, 2.5, 0.398005, 64],
    [25, 2.75, 0.147982, 64, 29, 1, 0.398005, 32, 29, 1.75, 0.147982, 32, 29, 3, 0.148027, 64, 32, 1.5, 0.148027, 32, 32, 2.25, 0.147982, 64, 36, 3.25, 0.147982, 64, 37, 0, 0.148027, 32, 37, 2.5, 0.398005, 64, 41, 0.25, 0.647982, 64, 41, 2, 0.398005, 64, 48, 1.25, 0.398005, 32, 48, 3.75, 0.147982, 32, 56, 3.5, 0.148027, 64],
    [24, 1, 0.148027, 32, 24, 3.25, 0.398005, 64, 31, 1.25, 0.147982, 32, 36, 0, 0.148027, 32, 36, 0.25, 0.147982, 32, 36, 2, 0.148027, 64, 36, 3.5, 0.148027, 32, 48, 2.75, 0.147982, 32, 51, 0.5, 0.398005, 32, 55, 1.5, 0.148027, 64, 55, 1.75, 0.147982, 32, 55, 3, 0.148027, 32, 60, 3.75, 0.249977, 32],
    [24, 0.25, 0.147982, 32, 24, 1.5, 0.148027, 64, 24, 2.25, 0.147982, 32, 24, 3.5, 0.148027, 64, 36, 0, 0.398005, 64, 36, 1.25, 0.147982, 32, 36, 1.75, 0.147982, 32, 36, 2, 0.398005, 64, 36, 3.25, 0.147982, 32, 36, 3.75, 0.147982, 32, 39, 0.75, 0.147982, 64, 39, 2.75, 0.147982, 64, 42, 0.5, 0.148027, 32, 42, 2.5, 0.148027, 32, 48, 1, 0.398005, 64, 48, 3, 0.398005, 64],
    [30, 0, 0.398005, 64, 31, 1, 0.148027, 32, 36, 0.25, 0.147982, 32, 40, 3, 0.148027, 32, 40, 3.25, 0.147982, 32, 41, 3.5, 0.148027, 32, 43, 0.5, 0.398005, 32, 46, 1.5, 0.148027, 32, 55, 0.75, 0.398005, 64, 55, 1.75, 0.647982, 32],
    [37, 3.5, 0.398005, 32, 38, 1, 0.148027, 32, 38, 1.25, 0.398005, 32, 38, 2.5, 0.398005, 32, 38, 3, 0.148027, 32, 39, 0.75, 0.147982, 32, 39, 1.75, 0.647982, 32, 42, 0.5, 0.148027, 32],
    [31, 0.25, 0.398005, 64, 36, 0, 0.398005, 32, 37, 2.25, 0.398005, 64, 37, 2.75, 0.147982, 64, 38, 0.75, 0.147982, 64, 39, 1, 0.398005, 64, 39, 3.25, 0.147982, 32, 39, 3.75, 0.147982, 32, 41, 2.5, 0.398005, 64, 42, 1.25, 0.398005, 64, 42, 3, 0.398005, 64, 56, 0.5, 0.148027, 32, 58, 3.5, 0.148027, 64, 60, 1.75, 0.398005, 64],
    [24, 0.5, 0.148027, 32, 36, 0, 0.148027, 32, 36, 1, 0.398005, 32, 36, 1.5, 0.398005, 64, 36, 2, 0.148027, 32, 36, 2.25, 0.147982, 64, 36, 2.5, 0.398005, 64, 36, 3, 0.148027, 64, 36, 3.25, 0.147982, 32, 36, 3.5, 0.398005, 32, 48, 0.25, 0.147982, 32, 48, 1.25, 0.147982, 32, 60, 0.75, 0.147982, 32],
    [36, 0, 4, 32],
    [26, 3.25, 0.147982, 32, 30, 0.25, 0.147982, 64, 30, 0.5, 0.398005, 32, 30, 1, 0.398005, 32, 32, 1.75, 0.147982, 32, 32, 2.25, 0.147982, 64, 32, 2.75, 0.147982, 64, 42, 0, 0.148027, 32, 44, 2.5, 0.398005, 32, 50, 1.25, 0.147982, 32, 50, 3, 0.398005, 32, 51, 0.75, 0.147982, 32, 54, 1.5, 0.148027, 32, 54, 3.5, 0.148027, 32],
    [31, 0.5, 0.148027, 64, 32, 1.25, 0.398005, 64, 33, 3, 0.148027, 32, 33, 3.5, 0.148027, 64, 40, 2.25, 0.398005, 32, 41, 0.25, 0.147982, 64, 42, 1.5, 0.398005, 64, 45, 2.75, 0.398005, 64, 46, 3.25, 0.398005, 32, 46, 3.75, 0.147982, 32, 47, 0, 0.148027, 32, 47, 1.75, 0.147982, 32, 52, 1, 0.148027, 32, 56, 0.75, 0.398005, 32, 59, 2.5, 0.398005, 32, 60, 2, 0.398005, 64],
    [24, 0.75, 0.147982, 32, 28, 1.25, 0.398005, 32, 28, 3.25, 0.398005, 64, 30, 1, 0.148027, 64, 30, 3, 0.398005, 32, 32, 1.75, 0.398005, 32, 38, 2, 0.398005, 64, 40, 0.25, 0.147982, 32, 51, 0, 0.398005, 32, 51, 2.5, 0.398005, 64, 51, 3.5, 0.398005, 64, 52, 2.75, 0.147982, 32, 55, 2.25, 0.398005, 64, 57, 1.5, 0.398005, 32, 60, 0.5, 0.398005, 64],
    [25, 0.25, 0.398005, 32, 25, 1.75, 0.398005, 32, 28, 0.75, 0.398005, 32, 28, 2, 0.148027, 32, 28, 3.75, 0.147982, 32, 32, 3.5, 0.398005, 64, 34, 1.5, 0.398005, 32, 37, 1, 0.148027, 64, 37, 3.25, 0.398005, 32, 38, 0, 0.148027, 32, 40, 0.5, 0.398005, 64, 41, 2.5, 0.398005, 32, 41, 3, 0.148027, 32, 44, 2.25, 0.147982, 64, 58, 1.25, 0.398005, 64, 59, 2.75, 0.147982, 32],
    [26, 1.25, 0.147982, 32, 26, 2.5, 0.148027, 64, 34, 1.5, 0.398005, 32, 35, 2.25, 0.398005, 64, 35, 3.5, 0.398005, 32, 37, 2, 0.148027, 32, 39, 3.25, 0.398005, 64, 46, 0.25, 0.398005, 32, 46, 3.75, 0.249977, 32, 47, 3, 0.148027, 64, 50, 1.75, 0.398005, 64, 53, 0, 0.398005, 32, 53, 0.5, 0.398005, 32, 54, 2.75, 0.398005, 64, 55, 0.75, 0.147982, 32, 56, 1, 0.148027, 64],
    [31, 0, 0.398005, 32, 31, 2.75, 0.147982, 32, 43, 1, 0.398005, 32, 43, 3, 0.148027, 32, 43, 3.25, 0.147982, 32, 55, 1.25, 0.147982, 32, 55, 1.5, 0.398005, 64, 55, 2, 0.398005, 64, 55, 2.5, 0.398005, 64, 55, 3.5, 0.398005, 64, 56, 0.5, 0.398005, 64],
    [24, 0.25, 0.147982, 32, 24, 2.5, 0.148027, 32, 24, 3, 0.148027, 64, 27, 1, 0.398005, 32, 27, 2.25, 0.147982, 32, 27, 3.25, 0.147982, 32, 36, 1.25, 0.398005, 32, 36, 3.5, 0.148027, 32, 39, 0.5, 0.398005, 32, 39, 2, 0.148027, 64, 39, 3.75, 0.147982, 32, 48, 0.75, 0.147982, 32, 48, 1.75, 0.147982, 32, 51, 0, 0.148027, 32, 51, 1.5, 0.398005, 32, 51, 2.75, 0.398005, 64],
    [24, 0.25, 0.147982, 32, 24, 3.75, 0.249977, 32, 25, 0, 0.398005, 32, 25, 0.5, 0.148027, 32, 25, 2.25, 0.147982, 32, 29, 0.75, 0.147982, 32, 29, 1, 0.148027, 32, 29, 1.75, 0.398005, 32, 30, 2.5, 0.148027, 32, 30, 3.25, 0.147982, 32, 48, 2, 0.148027, 32, 48, 3.5, 0.398005, 32, 49, 1.25, 0.398005, 32, 53, 1.5, 0.148027, 32, 53, 3, 0.148027, 32, 54, 2.75, 0.398005, 32],
    [31, 0, 0.398005, 32, 34, 2.75, 0.147982, 32, 46, 1, 0.398005, 32, 46, 3, 0.398005, 64, 58, 1.25, 0.147982, 32, 58, 1.5, 0.398005, 64, 58, 2, 0.398005, 64, 58, 2.5, 0.398005, 64, 59, 0.5, 0.398005, 64, 59, 3.5, 0.398005, 64],
    [31, 3, 0.398005, 32, 31, 3.5, 0.148027, 64, 43, 0.75, 0.147982, 32, 43, 1.75, 0.147982, 32, 43, 2.25, 0.398005, 64, 43, 2.75, 0.147982, 32, 43, 3.75, 0.147982, 32, 44, 1, 0.148027, 32, 46, 1.5, 0.148027, 64, 55, 0, 0.898005, 32, 55, 1.25, 0.147982, 32, 58, 2, 0.148027, 32, 58, 2.5, 0.148027, 32],
    [24, 0.25, 0.398005, 64, 36, 0, 0.398005, 64, 36, 2, 0.398005, 32, 41, 2.5, 0.148027, 64, 43, 2.75, 0.147982, 64, 44, 3, 0.148027, 64, 46, 3.25, 0.147982, 64, 48, 0.5, 0.148027, 32, 48, 2.25, 0.147982, 32, 51, 3.5, 0.398005, 64, 53, 0.75, 0.147982, 64, 55, 1, 0.148027, 64, 58, 1.5, 0.148027, 64, 60, 1.75, 0.398005, 64],
    [48, 0, 0.398005, 64, 48, 1, 0.398005, 64, 48, 2, 0.398005, 64, 48, 3, 0.398005, 64, 52, 0.25, 0.398005, 64, 52, 1.25, 0.398005, 64, 52, 2.25, 0.398005, 64, 52, 3.25, 0.398005, 64, 55, 0.5, 0.398005, 64, 55, 1.5, 0.398005, 64, 55, 2.5, 0.398005, 64, 55, 3.5, 0.398005, 64, 59, 0.75, 0.398005, 64, 59, 1.75, 0.398005, 64, 59, 2.75, 0.398005, 64, 59, 3.75, 0.249977, 64],
    [45, 0, 0.398005, 64, 45, 1, 0.398005, 64, 45, 2, 0.398005, 64, 45, 3, 0.398005, 64, 49, 0.25, 0.398005, 64, 49, 1.25, 0.398005, 64, 49, 2.25, 0.398005, 64, 49, 3.25, 0.398005, 64, 52, 0.5, 0.398005, 64, 52, 1.5, 0.398005, 64, 52, 2.5, 0.398005, 64, 52, 3.5, 0.398005, 64, 56, 0.75, 0.398005, 64, 56, 1.75, 0.398005, 64, 56, 2.75, 0.398005, 64, 56, 3.75, 0.249977, 64],
    [36, 0.25, 0.147982, 64, 36, 0.5, 0.148027, 32, 36, 0.75, 0.147982, 32, 36, 1.5, 0.148027, 32, 36, 1.75, 0.147982, 32, 36, 2.75, 0.147982, 32, 36, 3.25, 0.147982, 32, 36, 3.5, 0.148027, 32, 36, 3.75, 0.147982, 32, 39, 1.25, 0.147982, 64, 41, 2.25, 0.147982, 32, 41, 2.5, 0.148027, 64],
    [24, 2, 0.398005, 64, 25, 1.5, 0.148027, 32, 25, 2.75, 0.398005, 32, 26, 0.25, 0.647982, 64, 26, 1, 0.398005, 32, 28, 3.75, 0.147982, 64, 30, 2.25, 0.398005, 64, 36, 0.75, 0.398005, 32, 36, 2.5, 0.398005, 64, 42, 3, 0.398005, 32, 44, 0, 0.148027, 64, 48, 1.75, 0.147982, 32, 55, 3.25, 0.147982, 64, 55, 3.5, 0.398005, 64, 56, 1.25, 0.398005, 64],
    [36, 0, 0.398005, 32, 36, 1, 0.398005, 32, 36, 3.5, 0.398005, 32, 40, 2, 0.398005, 32, 40, 2.5, 0.398005, 32, 41, 1.5, 0.398005, 32, 48, 0.5, 0.398005, 32, 48, 2.75, 0.147982, 32, 52, 2.25, 0.398005, 32],
    [26, 1, 0.898005, 32, 32, 3.25, 0.647982, 32, 38, 0, 0.898005, 32, 38, 2.25, 0.647982, 32, 44, 3, 0.398005, 32, 50, 2, 0.398005, 32],
    [36, 0, 0.148027, 64, 36, 0.5, 0.148027, 32, 36, 0.75, 0.147982, 32, 36, 2.5, 0.398005, 32, 36, 3, 0.398005, 32, 36, 3.75, 0.249977, 32, 39, 2, 0.648027, 64, 41, 0.25, 0.398005, 32, 41, 1.75, 0.147982, 64, 41, 2.75, 0.147982, 64, 41, 3.25, 0.398005, 32, 42, 1, 0.5, 32, 42, 1.5, 0.148027, 64, 42, 3.5, 0.148027, 64],
    [37, 0.25, 0.147982, 64, 37, 1, 0.148027, 32, 37, 2.25, 0.147982, 64, 37, 3, 0.148027, 32, 40, 1.25, 0.398005, 32, 40, 1.75, 0.147982, 64, 40, 3.25, 0.398005, 32, 40, 3.75, 0.147982, 64, 41, 0, 0.148027, 64, 41, 0.5, 0.148027, 32, 41, 2, 0.148027, 64, 41, 2.5, 0.148027, 32, 46, 0.75, 0.147982, 64, 46, 1.5, 0.398005, 32, 46, 2.75, 0.147982, 64, 46, 3.5, 0.398005, 32],
    [24, 0.25, 0.147982, 32, 24, 1.5, 0.148027, 32, 24, 2.75, 0.147982, 32, 36, 0, 0.148027, 64, 36, 0.75, 0.147982, 32, 36, 1.25, 0.147982, 64, 36, 2, 0.148027, 32, 36, 2.5, 0.148027, 64, 36, 3.25, 0.147982, 32, 36, 3.75, 0.147982, 64, 39, 1, 0.148027, 32, 39, 2.25, 0.147982, 32, 39, 3.5, 0.148027, 32, 60, 0.5, 0.398005, 32, 60, 1.75, 0.398005, 32, 60, 3, 0.398005, 32],
    [31, 1.5, 0.148027, 64, 31, 3.5, 0.148027, 64, 34, 1.25, 0.147982, 32, 34, 3.25, 0.147982, 32, 36, 0.25, 0.147982, 32, 36, 1.75, 0.398005, 32, 36, 2.25, 0.147982, 32, 36, 3.75, 0.249977, 32, 39, 0.75, 0.147982, 64, 39, 2.75, 0.147982, 64, 41, 1, 0.148027, 64, 41, 3, 0.148027, 64, 42, 0, 0.148027, 64, 42, 2, 0.148027, 64, 59, 0.5, 0.148027, 64, 59, 2.5, 0.148027, 64]
    ]


#    ################################################################################################
#    ##  END OF UTIL TAB

#    ################################################################################################
#    ##  LOOP TAB

    loop_midi_low_buttons = [const.MIDI_LOOP_LOW1, const.MIDI_LOOP_LOW2, const.MIDI_LOOP_LOW3, const.MIDI_LOOP_LOW4, const.MIDI_LOOP_LOW5, const.MIDI_LOOP_LOW6, const.MIDI_LOOP_LOW7, const.MIDI_LOOP_LOW8]
    loop_midi_upp_buttons = [const.MIDI_LOOP_UPP1, const.MIDI_LOOP_UPP2, const.MIDI_LOOP_UPP3, const.MIDI_LOOP_UPP4, const.MIDI_LOOP_UPP5, const.MIDI_LOOP_UPP6, const.MIDI_LOOP_UPP7, const.MIDI_LOOP_UPP8]
    loop_midi_buttons = [
    const.MIDI_LOOP_LOW1, const.MIDI_LOOP_LOW2, const.MIDI_LOOP_LOW3, const.MIDI_LOOP_LOW4, const.MIDI_LOOP_LOW5, const.MIDI_LOOP_LOW6, const.MIDI_LOOP_LOW7, const.MIDI_LOOP_LOW8,
    const.MIDI_LOOP_UPP1, const.MIDI_LOOP_UPP2, const.MIDI_LOOP_UPP3, const.MIDI_LOOP_UPP4, const.MIDI_LOOP_UPP5, const.MIDI_LOOP_UPP6, const.MIDI_LOOP_UPP7, const.MIDI_LOOP_UPP8
    ]
    loop_midi_encoders = [const.MIDI_LOOP_START_MEAS_ENCODER, const.MIDI_LOOP_START_BEAT_ENCODER, const.MIDI_LOOP_START_QBEAT_ENCODER, const.MIDI_LOOP_END_MEAS_ENCODER, const.MIDI_LOOP_END_BEAT_ENCODER, const.MIDI_LOOP_END_QBEAT_ENCODER]

    loop_register_mode = False
    loop_registered_loops = []
    loop_cur_preset = -1
    loop_morph_prev_val = -1

    def loop_update_gui(self):
        if self.lito_tab != LOOP_TAB:
            return

        self.loop_update_gui_buttons()
        self.loop_update_pitch_gui()
        return

    def loop_exit(self):

        self.loop_audio_clips_pitches.clear()
        self.oscEndpoint.send("/loop/label_track", "")
        self.oscEndpoint.send("/loop/label_clip", "")
        self.oscEndpoint.send("/loop/label_start_loop1", "")
        self.oscEndpoint.send("/loop/label_start_loop2", "")
        self.oscEndpoint.send("/loop/label_end_loop1", "")
        self.oscEndpoint.send("/loop/label_end_loop2", "")

    def loop_init(self):
        self.loop_registered_loops = [[-1 for i in range(2)] for x in range(LOOP_CNT)]
        loop_register_mode = False
        self.loop_update_gui()
        return

    def loop_get_ableton_time(self, time):
        if time >= 0:
            meas = int(time/4)
            beat = int(time - meas*4)
            qbeat = int((time - meas*4 - beat) * 4)
            return meas, beat, qbeat
        return 0,0,0


    def loop_get_clip_slot(self):
        if self.lito_tab != LOOP_TAB:
            return

        cs = None
        current_track = self.song().view.selected_track
        if current_track != None:
            cs = self.song().view.highlighted_clip_slot
            if cs != None:
                if cs.has_clip == True:
                    if cs.clip.is_audio_clip == True:
                        if cs.clip not in self.loop_audio_clips_pitches:
                            self.loop_audio_clips_pitches[cs.clip] = cs.clip.pitch_coarse
                    else:
                        cs = None
                else:
                    cs = None

        return current_track,cs

    def loop_update_tr_cl_st_en(self):
        if self.lito_tab != LOOP_TAB:
            return

        self.oscEndpoint.send("/loop/label_track","")
        self.oscEndpoint.send("/loop/label_clip","No clip")
        self.oscEndpoint.send("/loop/label_start_loop1", "")
        self.oscEndpoint.send("/loop/label_start_loop2", "")
        self.oscEndpoint.send("/loop/label_end_loop1", "")
        self.oscEndpoint.send("/loop/label_end_loop2", "")

        current_track,cs = self.loop_get_clip_slot()

        if cs == None:
            if self.loop_register_mode == False:
                self.clear_midi()
        else:

            self.oscEndpoint.send("/loop/label_track",str(current_track.name))
            idx = self.tuple_idx(current_track.clip_slots, cs)

            text = "clip: " + str(idx+1)
            self.oscEndpoint.send("/loop/label_clip", text)
            clip = cs.clip

            self.oscEndpoint.send("/loop/label_start_loop1", str(clip.loop_start))
            self.oscEndpoint.send("/loop/label_end_loop1", str(clip.loop_end))
            if clip.loop_start >= 0:
                meas, beat, qbeat = self.loop_get_ableton_time(clip.loop_start)
                text = str(meas+1) + ":" + str(beat+1) + ":" + str(qbeat+1)
                self.oscEndpoint.send("/loop/label_start_loop2", text)
                meas_end, beat_end, qbeat_end = self.loop_get_ableton_time(clip.loop_end - clip.loop_start)
                text = str(meas_end) + ":" + str(beat_end) + ":" + str(qbeat_end)
                self.oscEndpoint.send("/loop/label_end_loop2", text)
                if self.loop_register_mode == False:
                    self.loop_update_midi(meas, beat, qbeat, meas_end, beat_end, qbeat_end)

        return

    def loop_update_midi(self, meas, beat, qbeat, meas_end, beat_end, qbeat_end):
        if self.lito_tab != LOOP_TAB:
            return

        self.send_midi_ex((0xB0, const.MIDI_LOOP_START_MEAS_ENCODER, meas), LOOP_TAB)
        self.send_midi_ex((0xB0, const.MIDI_LOOP_START_BEAT_ENCODER, int(self.adaptValue(beat, 0, 3, 0, 127))), LOOP_TAB)
        self.send_midi_ex((0xB0, const.MIDI_LOOP_START_QBEAT_ENCODER, int(self.adaptValue(qbeat, 0, 3, 0, 127))), LOOP_TAB)

        self.send_midi_ex((0xB0, const.MIDI_LOOP_END_MEAS_ENCODER, meas_end), LOOP_TAB)
        self.send_midi_ex((0xB0, const.MIDI_LOOP_END_BEAT_ENCODER, int(self.adaptValue(beat_end, 0, 3, 0, 127))), LOOP_TAB)
        self.send_midi_ex((0xB0, const.MIDI_LOOP_END_QBEAT_ENCODER, int(self.adaptValue(qbeat_end, 0, 3, 0, 127))), LOOP_TAB)

        for i in self.loop_midi_buttons:
            self.send_midi_ex((0xB0, i, 0), LOOP_TAB)

        self.send_midi_ex((0xB0, const.MIDI_LOOP_UPP1 + beat, 127), LOOP_TAB)
        self.send_midi_ex((0xB0, const.MIDI_LOOP_UPP5 + qbeat, 127), LOOP_TAB)
        self.send_midi_ex((0xB0, const.MIDI_LOOP_LOW1 + beat_end, 127), LOOP_TAB)
        self.send_midi_ex((0xB0, const.MIDI_LOOP_LOW5 + qbeat_end, 127), LOOP_TAB)

        return

    def loop_set_start_end_clip(self, clip, cur_start, cur_end):
        if self.lito_tab != LOOP_TAB:
            return

        if cur_start >= clip.loop_end:
            clip.loop_end = cur_end
            clip.loop_start = cur_start
        else:
            clip.loop_start = cur_start
            clip.loop_end = cur_end

        clip.end_marker = clip.loop_end
        clip.start_marker = clip.loop_start

        return

    def loop_midi_set_pitch(self, val):
        if self.lito_tab != LOOP_TAB:
            return

        track, cs = self.loop_get_clip_slot()
        if track != None and cs != None and val < 128:
            if const.midi_relative == False:
                pitch_coarse = int(self.adaptValue(val, 0, 127, -48, 48))
            else:
                val = self.midi_get_rel_dec_inc_val(val)
                pitch_coarse = cs.clip.pitch_coarse
                pitch_coarse = pitch_coarse + val

            if pitch_coarse > 48:
                pitch_coarse = 48
            elif pitch_coarse < -48:
                pitch_coarse = -48
            cs.clip.pitch_coarse = pitch_coarse

        return

    def loop_midi_set_fly(self, encoder, val):
        if self.lito_tab != LOOP_TAB:
            return

        track, cs = self.loop_get_clip_slot()
        if track != None and cs != None and val < 128:
            clip = cs.clip
            meas, beat, qbeat = self.loop_get_ableton_time(clip.loop_start)
            meas_end, beat_end, qbeat_end = self.loop_get_ableton_time(clip.loop_end - clip.loop_start)

            if encoder >= 1 and encoder <= 3:
                delta = clip.loop_end - clip.loop_start
                if encoder == 1:
                    if const.midi_relative == False:
                        cur_start = (val) * 4 + beat + qbeat/4.0
                    else:
                        val = self.midi_get_rel_dec_inc_val(val, ACCELERATION_ON_LOOPER)
                        cur_start = (meas+val) * 4 + beat + qbeat/4.0

                elif encoder == 2:
                    if const.midi_relative == False:
                        cur_start = (meas) * 4 + (int(self.adaptValue(val, 0, 127, 0, 3, 3))) + qbeat/4.0
                    else:
                        val = self.midi_get_rel_dec_inc_val(val, ACCELERATION_ON_LOOPER)
                        cur_start = (meas) * 4 + (beat + val) + qbeat/4.0

                elif encoder == 3:
                    if const.midi_relative == False:
                        cur_start = (meas) * 4 + beat + (int(self.adaptValue(val, 0, 127, 0, 3, 3)))/4.0
                    else:
                        val = self.midi_get_rel_dec_inc_val(val, ACCELERATION_ON_LOOPER)
                        cur_start = (meas) * 4 + beat + (qbeat + val)/4.0

                if cur_start < 0:
                    cur_start = 0

                cur_end = cur_start + delta
                self.loop_set_start_end_clip(clip, cur_start, cur_end)

            else:
                if encoder == 4:
                    if const.midi_relative == False:
                        cur_end = (val) * 4 + beat_end + qbeat_end/4.0
                    else:
                        val = self.midi_get_rel_dec_inc_val(val, ACCELERATION_ON_LOOPER)
                        cur_end = (meas_end + val) * 4 + beat_end + qbeat_end/4.0

                elif encoder == 5:
                    if const.midi_relative == False:
                        cur_end = meas_end * 4 + int(self.adaptValue(val, 0, 127, 0, 3, 3)) + qbeat_end/4.0
                    else:
                        val = self.midi_get_rel_dec_inc_val(val, ACCELERATION_ON_LOOPER)
                        cur_end = meas_end * 4 + beat_end + val + qbeat_end/4.0

                elif encoder == 6:
                    if const.midi_relative == False:
                        cur_end = meas_end * 4 + beat_end + int(self.adaptValue(val, 0, 127, 0, 3, 3))/4.0
                    else:
                        val = self.midi_get_rel_dec_inc_val(val, ACCELERATION_ON_LOOPER)
                        cur_end = meas_end * 4 + beat_end + (qbeat_end + val)/4.0

                cur_end = clip.loop_start + cur_end
                if cur_end <= clip.loop_start:
                    cur_end =  clip.loop_end
                clip.loop_end = cur_end
                clip.end_marker = clip.loop_end

        return

    def loop_midi_set_beat(self, button):
        if self.lito_tab != LOOP_TAB:
            return

        track, cs = self.loop_get_clip_slot()
        if track != None and cs != None:
            clip = cs.clip
            meas, beat, qbeat = self.loop_get_ableton_time(clip.loop_start)
            meas_end, beat_end, qbeat_end = self.loop_get_ableton_time(clip.loop_end - clip.loop_start)

            if button >= 1 and button <= 8:
                delta = clip.loop_end - clip.loop_start

                if button <= 4:
                    cur_start = meas*4 + (button-1) + qbeat/4.0
                    cur_end = cur_start + delta
                else:
                    cur_start = meas*4 + beat + (button-5.0)/4.0
                    cur_end = cur_start + delta

                if clip.loop_start == cur_start:
                    if self.loop_register_mode == False:
                        self.loop_update_midi(meas, beat, qbeat, meas_end, beat_end, qbeat_end)
                else:
                    self.loop_set_start_end_clip(clip, cur_start, cur_end)

            elif button >= 9 and button <= 16:

                if button <= 12:
                    cur_end = meas_end*4 + (button - 9) + qbeat_end/4.0
                else:
                    cur_end = meas_end*4 + beat_end + (button-13.0)/4.0
                cur_end = clip.loop_start + cur_end

                if clip.loop_end == cur_end:
                    if self.loop_register_mode == False:
                        self.loop_update_midi(meas, beat, qbeat, meas_end, beat_end, qbeat_end)
                else:
                    if cur_end > clip.loop_start:
                        clip.loop_end = cur_end
                        clip.end_marker = clip.loop_end

            return

    def loop_update_gui_buttons(self):
        if self.lito_tab != LOOP_TAB:
            return
        if self.loop_register_mode == True:
            self.loop_midi_register_presets_gui()
        else:
            self.loop_update_tr_cl_st_en()

    def loop_toggle_mode(self):
        if self.lito_tab != LOOP_TAB:
            return
        self.loop_register_mode = not self.loop_register_mode
        self.loop_update_gui_buttons()
        return

    def loop_midi_register_presets_gui(self):
        if self.lito_tab != LOOP_TAB:
            return
        for i in self.loop_midi_buttons:
            self.send_midi_ex((0xB0, i, 0), LOOP_TAB)

        for i in range(8):
            if self.loop_registered_loops[i][0] != -1 and self.loop_registered_loops[i][1] != -1:
                self.send_midi_ex((0xB0, const.MIDI_LOOP_UPP1+i, 127), LOOP_TAB)

        if self.loop_cur_preset != -1:
            self.send_midi_ex((0xB0, const.MIDI_LOOP_LOW1 + self.loop_cur_preset, 127), LOOP_TAB)

        return

    def loop_midi_handle_register_ex(self, button):
        if self.lito_tab != LOOP_TAB:
            return
        if self.loop_register_mode == False:
            return
        self.loop_midi_handle_register(button)
        self.loop_midi_register_presets_gui()

    def loop_midi_handle_register(self, button):
        if self.lito_tab != LOOP_TAB:
            return

        track, cs = self.loop_get_clip_slot()
        if track != None and cs != None:
            clip = cs.clip
            if button >= 1 and button <= 8:
                if len(self.loop_registered_loops) == LOOP_CNT:
                    self.loop_registered_loops[button-1][0] = clip.loop_start
                    self.loop_registered_loops[button-1][1] = clip.loop_end

            else:
                preset = button - 9
                if len(self.loop_registered_loops) == LOOP_CNT:
                    if self.loop_registered_loops[preset][0] != -1 and self.loop_registered_loops[preset][1] != -1:
                        self.loop_cur_preset = preset
                        self.loop_set_start_end_clip(clip, self.loop_registered_loops[preset][0], self.loop_registered_loops[preset][1])

        return

    def loop_midi_rand(self):
        if self.lito_tab != LOOP_TAB:
            return
        track, cs = self.loop_get_clip_slot()
        if track != None and cs != None:
            clip = cs.clip
            if len(self.loop_registered_loops) == LOOP_CNT:
                if self.loop_registered_loops[0][0] != -1 and self.loop_registered_loops[0][1] != -1:
                    init_start = self.loop_registered_loops[0][0]
                    init_end = self.loop_registered_loops[0][1]
                    for i in range(1,8):
                        start = random.randint(int(init_start*4), int(init_end*4-1))
                        end = random.randint(int(1), int(init_end*4-start)) + start
                        self.loop_registered_loops[i][0] = float(start)/4.0
                        self.loop_registered_loops[i][1] = float(end)/4.0
                    self.loop_midi_register_presets_gui()

        return

    def loop_midi_recall_pitch(self):
        if self.lito_tab != LOOP_TAB:
            return
        track, cs = self.loop_get_clip_slot()
        if track != None and cs != None:
            clip = cs.clip
            if clip in self.loop_audio_clips_pitches:
                clip.pitch_coarse = self.loop_audio_clips_pitches[clip]
        return

    def loop_midi_set_dft_pitch(self):
        if self.lito_tab != LOOP_TAB:
            return
        track, cs = self.loop_get_clip_slot()
        if track != None and cs != None:
            if cs.clip in self.loop_audio_clips_pitches:
                self.loop_audio_clips_pitches[cs.clip] = cs.clip.pitch_coarse
        return

    def loop_update_pitch_gui(self):
        if self.lito_tab != LOOP_TAB:
            return
        track, cs = self.loop_get_clip_slot()
        if track != None and cs != None:
            val = int(self.adaptValue(cs.clip.pitch_coarse, -48, 48, 0, 127))
            self.send_midi_ex((0xB0, const.MIDI_LOOP_PITCH_ENCODER, val), LOOP_TAB)
        else:
            self.send_midi_ex((0xB0, const.MIDI_LOOP_PITCH_ENCODER, 0), LOOP_TAB)

#    ################################################################################################
#    ##  END OF LOOP TAB

#    ################################################################################################
#    ##  WIO

    wio_track_name = ''
    wio_device_name = ''
    wio_param_name = ''
    wio_param_val = ''
    wio_page = ''
    wio_info = ''
    wio_device_count = ''

    def wio_send_track_name(self, text):
        if text != self.wio_track_name:
            address = "/wio/track_name"
            self.wio_track_name = text
            self.oscEndpoint.send(address, text)

    def wio_send_device_name(self, text):
        if text != self.wio_device_name:
            address = "/wio/device_name"
            self.wio_device_name = text
            self.oscEndpoint.send(address, text)

    def wio_send_page(self, text):
        if text != self.wio_page:
            address = "/wio/page"
            self.wio_page = text
            self.oscEndpoint.send(address, text)

    def wio_send_param_name(self, text):
        if text != self.wio_param_name:
            address = "/wio/param_name"
            self.wio_param_name = text
            self.oscEndpoint.send(address, text)

    def wio_send_param_name2(self, fader, text):
        address = "/wio/param_name2"
        self.oscEndpoint.send(address, (int(fader),str(text)))

    def wio_send_param_val(self, text):
        if text != self.wio_param_val:
            address = "/wio/param_val"
            self.wio_param_val = text
            self.oscEndpoint.send(address, text)

    def wio_send_info(self, text):
        if text != self.wio_info:
            address = "/wio/info"
            self.wio_info = text
            self.oscEndpoint.send(address, text)

    def wio_send_device_count(self, text):
        if text != self.wio_device_count:
            address = "/wio/device_count"
            self.wio_device_count = text
            self.oscEndpoint.send(address, text)

    def wio_send_shutdown(self):
        address = "/wio/shutdown"
        self.oscEndpoint.send(address, "shutdown")

#    ################################################################################################
#    ##  END OF WIO

#    ################################################################################################
#    ##  DEVICE PREFERENCES
    dev_pref_loaded = False
    dev_pref_dict = {}

    def dev_pref_read_file(self):
        if self.dev_pref_loaded == False:
            dev_file_name = os.path.join(os.path.dirname(__file__), "device_preferences.txt")
            if os.path.exists(dev_file_name) == True:
                with open(dev_file_name) as dev_file:
                    ll = []
                    device_name = ''
                    while True:
                        # Get next line from file
                        line = dev_file.readline()
                        # if line is empty
                        # end of file is reached
                        if not line:
                            break

                        line = line.strip()
                        if len(line) != 0:
                            if line.startswith('#') == False:
                                if line.startswith('device') == True:
                                    if '=' in line:
                                        idx = line.index('=')
                                        line = line[idx+1:]
                                        found,idx = get_first_alnum(line)
                                        if found == True:
                                            if len(device_name) != 0 and len(ll) != 0:
                                                self.dev_pref_dict[device_name] = ll
                                                ll = []
                                            device_name = line[idx:]
                                else:
                                    ll.append(line)


                    if len(device_name) != 0 and len(ll) != 0:
                        self.dev_pref_dict[device_name] = ll
                    self.dev_pref_loaded = True
                    mylog("----") # PERMANENT
                    mylog(dev_file_name) # PERMANENT
                    mylog(self.dev_pref_dict) # PERMANENT

    '''
    user_folders = None
    current_item = None


    def db_select_item(self, name):
        if self.current_item != None:
            children = self.current_item.children
            lchild = None
            for child in children:
                if name == child.name:
                    self.current_item = child
                    break

    def db_select_placeCB(self):

        self.user_folders = None
        self.current_item = None

        browser = Live.Application.get_application().browser
        self.user_folders = browser.user_folders
        mylog("start")
        mylog(self.user_folders)
        mylog(self.current_item)
        for folder in self.user_folders:
            for folder in self.user_folders:
                if folder.name == "Kontakt":
                    self.current_item = folder
                    break

        mylog("folder selected")
        mylog(self.current_item)

        self.db_select_item("TST_LITO")
        mylog("TST_LITO selected")
        mylog(self.current_item)

        name = "ZG1 ORIENTAL.nki"
        #name = "ZG VOX 24.1.wav"
        self.db_select_item(name)
        mylog(name, "selected")
        mylog(self.current_item)

        if self.current_item != None:
            mylog("loading", name)
            browser.preview_item(self.current_item)
    '''

    #    ################################################################################################
    #    ##  END OF DEVICE PREFERENCES

#    ################################################################################################
#    ##  MISC

def get_first_alnum(text):
    L = len(text)
    vivi = 0
    found = False
    for v in range(1,L):
        if text[vivi].isalnum():
            found = True
            break
        vivi = vivi + 1
    return found, vivi

def generate_strip_string(display_string):

    u""" Hack: Shamelessly stolen from the MainDisplayController of the Mackie Control.
    Should share this in future in a 'Common' package!

    returns a n char string for of the passed string, trying to remove not so important
    letters (and signs first...)
    """

    NUM_CHARS_PER_DISPLAY_STRIP = 9
    if not display_string:
        return ' ' * NUM_CHARS_PER_DISPLAY_STRIP

    if len(display_string) > NUM_CHARS_PER_DISPLAY_STRIP - 1:
        for um in [' ', 'Y', 'y', 'I', 'i', 'O', 'o', 'U', 'u', 'E', 'e', 'A', 'a']:
            while len(display_string) > NUM_CHARS_PER_DISPLAY_STRIP - 1 and display_string.rfind(um, 1) != -1:
                um_pos = display_string.rfind(um, 1)
                display_string = display_string[:um_pos] + display_string[um_pos + 1:]

    ret = display_string.lstrip()
    if len(ret) > NUM_CHARS_PER_DISPLAY_STRIP:
        ret = ret[len(ret)-NUM_CHARS_PER_DISPLAY_STRIP:]

    return ret

#    ################################################################################################
#    ##  END OF MISC


