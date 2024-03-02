import os
import xbmcaddon

class Settings:
    def __init__(self):
        return

    @staticmethod
    def load():
        Settings.id = "plugin.video.uakino.club"
        Settings.addon = xbmcaddon.Addon(Settings.id)
        Settings.addondir = Settings.addon.getAddonInfo("path")
        Settings.icon = Settings.addon.getAddonInfo("icon")
        Settings.icon_next = os.path.join(Settings.addondir, "resources/icons/next.png")
        Settings.language = Settings.addon.getLocalizedString

        Settings.quality = Settings.addon.getSetting("quality")
        Settings.domain = Settings.addon.getSetting("domain")
        Settings.translit = Settings.addon.getSettingBool("translit")
        Settings.debug = Settings.addon.getSettingBool("debug")

        Settings.url = f"https://{Settings.domain}"
