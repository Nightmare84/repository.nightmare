import os
import xbmcaddon

class settings(object):
	def __init__(self):
		return

	@staticmethod
	def load():
		settings.id = 'plugin.video.hdrezka.tv'
		settings.addon = xbmcaddon.Addon(settings.id)
		settings.addondir = settings.addon.getAddonInfo('path')
		settings.icon = settings.addon.getAddonInfo('icon')
		settings.icon_next = os.path.join(settings.addondir, 'resources/icons/next.png')
		settings.language = settings.addon.getLocalizedString

		settings.use_transliteration = settings.addon.getSettingBool('use_transliteration')
		settings.only_ua = settings.addon.getSetting('only_ua') == 'true'
		settings.quality = settings.addon.getSetting('quality')
		settings.translator = settings.addon.getSetting('translator')
		settings.domain = settings.addon.getSetting('domain')
		settings.show_description = settings.addon.getSettingBool('show_description')
		settings.url = settings.addon.getSetting('dom_protocol') + '://' + settings.domain