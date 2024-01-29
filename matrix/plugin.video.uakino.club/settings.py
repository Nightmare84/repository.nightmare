import os
import xbmcaddon

class settings:
    def __init__(self):
        return

    @staticmethod
    def load():
        settings.id = "plugin.video.uakino.club"
        settings.addon = xbmcaddon.Addon(settings.id)
        settings.addondir = settings.addon.getAddonInfo("path")
        settings.icon = settings.addon.getAddonInfo("icon")
        settings.icon_next = os.path.join(settings.addondir, "resources/icons/next.png")
        settings.language = settings.addon.getLocalizedString

        settings.quality = settings.addon.getSetting("quality")
        settings.domain = settings.addon.getSetting("domain")
        settings.translit = settings.addon.getSettingBool("translit")
        settings.debug = settings.addon.getSettingBool("debug")

        settings.url = f"https://{settings.domain}"
