# This Python file uses the following encoding: utf-8

USE_HOOK = False

def _hook_set_PC(c_instance, cookie):
    if cookie == False:
        c_instance.send_midi((0xCF, 0))
    else:
        c_instance.send_midi((0xCF, 1))

def hook_switch_util_tab(c_instance, cookie):
    if USE_HOOK == False:
        return
    _hook_set_PC(c_instance, cookie)

def hook_switch_lad_tab(c_instance, cookie):
    if USE_HOOK == False:
        return
    _hook_set_PC(c_instance, cookie)

def hook_switch_morph_tab(c_instance, cookie):
    if USE_HOOK == False:
        return
    _hook_set_PC(c_instance, cookie)

def hook_switch_euc_tab(c_instance, cookie):
    if USE_HOOK == False:
        return
    _hook_set_PC(c_instance, cookie)

def hook_switch_loop_tab(c_instance, cookie):
    if USE_HOOK == False:
        return
    _hook_set_PC(c_instance, cookie)
