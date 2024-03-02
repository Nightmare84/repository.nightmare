import re
import os
import xbmc
import xbmcgui


def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"uakino: {msg}", level)


def show_message(message):
    dialog = xbmcgui.Dialog()
    dialog.ok("UAKino", message)

def show_notification(header: str, message: str, time: int = 1000, sound: bool = False):
    xbmcgui.Dialog().notification(header, message, None, time, sound)

def write_to_file(text):
    with open(os.path.expanduser("~/uakino_tmp.txt"), "w", encoding="utf-8") as file:
        file.write(str(text))

def merge_lists(*args, fill_value=""):
    max_length = max([len(lst) for lst in args])
    result = []
    for i in range(max_length):
        result.append([args[k][i] if i < len(args[k]) else fill_value for k in range(len(args))])
    return result

def insertString(string, position, stringToInsert):
    return string[:position] + stringToInsert + string[position:]

def repairImageTag(html):
    result = html
    b = 0
    while True:
        b = result.find("<img ", b)
        if b == -1:
            return result
        e = result.find(">", b)
        if result[e - 1] != "/":
            result = insertString(result, e, "/")
        b = e

