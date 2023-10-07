import os
import xbmc
import xbmcgui



def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f'hdrezka: {msg}', level)

def show_message(message):
    dialog = xbmcgui.Dialog()
    ok = dialog.ok('HdrezkaTV', message)

def write_to_file(text):
    with open(os.path.expanduser('~/HDrezka_tmp.txt'), 'w', encoding = "utf-8") as file:
        file.write(str(text))
