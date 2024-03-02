#!/usr/bin/python

import os, urllib, sys, socket, re
import xbmc, xbmcplugin, xbmcgui, xbmcaddon
import uppod
from helpers import log, show_message, write_to_file, merge_lists, insertString, repairImageTag
from video_info import VideoInfo
from settings import Settings as settings
import json
import router
#import web_helper
import XbmcHelpers
import SearchHistory as history
import Translit as translit
from mem_storage import MemStorage
from site_parser import SiteParser
import gzip


common = XbmcHelpers
translit = translit.Translit(encoding="cp1251")

class URLParser:
    def parse(self, string):
        links = re.findall(r'(?:http://|www.).*?["]', string)
        return list(set(self.filter(links)))

    def filter(self, links):
        links = self.strip(links)
        return [link for link in links if link.endswith(".mp4") or link.endswith(".mp4") or link.endswith(".txt")]

    def strip(self, links):
        return [link.replace('"', "") for link in links]


class Uakino:
    def __init__(self):
        settings.load()
        self.id = "plugin.video.uakino.club"
        self.addon = xbmcaddon.Addon(self.id)
        self.icon = self.addon.getAddonInfo("icon")
        self.path = self.addon.getAddonInfo("path")
        self.profile = self.addon.getAddonInfo("profile")

        self.handle = int(sys.argv[1])
        self.url = settings.url

        self.inext = os.path.join(self.path, "resources/icons/next.png")
        self.debug = self.addon.getSetting("debug") == "true"

        self.site = SiteParser()

    def main(self):
        params = router.parse_uri(sys.argv[2])
        mode = params.get("mode")
        url = params.get("url")
        offset = params.get("offset")
        page = params.get("page")
        keyword = params.get("keyword")

        log(f"mode: {mode}, url: {url}, offset: {offset}, page: {page}, keyword: {keyword}")
        if mode == "play":
            self.play(url)
        elif mode == "movie" or mode == "show":
            self.getMovieURL(url)
        elif mode == "subcategory":
            self.getSubCategoryItems(url, page)
        elif mode == "category":
            self.getCategoryItems(url)
        elif mode == "search":
            external = "main" if "main" in params else None
            if not external:
                external = "usearch" if "usearch" in params else None
            self.search(params.get("keyword"), external)
        elif mode == "history":
            self.history()
        elif mode is None:
            self.menu()

    def menu(self):
        uri = sys.argv[0] + "?mode={}&url={}".format("search", self.url)
        item = xbmcgui.ListItem(f"[COLOR=FF00FF00]{settings.language(30001)}[/COLOR]")
        item.setArt({self.icon})
        xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

        uri = sys.argv[0] + "?mode={}&url={}".format("history", self.url)
        item = xbmcgui.ListItem(f"[COLOR=FF00FF00]{settings.language(30004)}[/COLOR]")
        item.setArt({self.icon})
        xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

        self.getCategories()
        xbmcplugin.endOfDirectory(self.handle, True)

    def getCategories(self):
        log("getCategories")
        categories = self.site.getCategories()

        for title, link, subcategories in categories:
            url = self.url + link
            uri = f"{sys.argv[0]}?mode=category&url={url}"
            item = xbmcgui.ListItem(title)
            # item.setArt({"thumb": self.icon})
            xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

        xbmc.executebuiltin("Container.SetViewMode(50)")
        xbmcplugin.endOfDirectory(self.handle, True)

    def getCategoryItems(self, url):
        log(f"getCategoryItems url: {url}")

        storage = MemStorage()
        allSubCategories = storage["subCategories"]
        subCategories = list(filter(lambda sub: sub[1] == url.replace(self.url, ""), allSubCategories))[0][2]
        #write_to_file(subCategories)

        for link, title in subCategories:
            url = f"{self.url}{link}"
            uri = f"{sys.argv[0]}?mode=subcategory&url={url}&page=1"
            #log(f"uri: {uri}")
            item = xbmcgui.ListItem(title)
            item.setArt({"thumb": self.icon})
            xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

        xbmcplugin.endOfDirectory(self.handle, True)

    def getSubCategoryItems(self, url, page):
        log(f"getSubCategoryItems url: {url} page: {page}")

        videos = self.site.getSubCategoryItems(url, page)
        for video in videos:
            item = video.ListItem
            item_uri = router.build_uri("show", url=router.normalize_uri(video.link))
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, False)

        params = {"page": 2, "url": url}
        if page:
            params["page"] = int(page) + 1
        item_uri = router.build_uri("subcategory", **params)
        log(f"url: {url}, item_uri: {item_uri}")
        item = xbmcgui.ListItem("[COLOR=orange]" + settings.language(30003) + "[/COLOR]")
        item.setArt({"icon": settings.icon_next})
        xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        xbmcplugin.setContent(self.handle, "movies")
        xbmc.executebuiltin("Container.SetViewMode(504)")
        xbmcplugin.endOfDirectory(self.handle, True)

    def getMovieURL(self, url):
        log(f"getMovieURL url: {url}")
        link = self.site.getMovieURL(url)

        item = xbmcgui.ListItem(path=link)
        # if subtitles: item.setSubtitles(subtitles)
        xbmcplugin.setResolvedUrl(self.handle, True, item)

        # playerUrl = f"/engine/ajax/playlists.php?news_id={video.id}&xfield=playlist"
        # log(f"playerUrl: {playerUrl}")
        # #player = common.fetchPage({"link": f"{self.url}playerUrl"})
        # player = self.web.make_request("GET", playerUrl).text
        # write_to_file(player)
        # page = common.fetchPage({"link": video.link})["content"].decode("utf-8")  # .replace("\t", "").replace("\n", "")

    def play(self, url):
        log(f"play url: {url}")

        item = xbmcgui.ListItem(path=url)
        xbmcplugin.setResolvedUrl(self.handle, True, item)

    def history(self):
        log("history()")
        words = history.get_history()
        for word in reversed(words):
            uri = router.build_uri("search", keyword=word, main=1)
            item = xbmcgui.ListItem(word)
            item.setArt({"thumb": settings.icon, "icon": settings.icon})
            xbmcplugin.addDirectoryItem(self.handle, uri, item, True)
        xbmcplugin.endOfDirectory(self.handle, True)

    def search(self, keyword, external):
        keyword = urllib.parse.unquote_plus(keyword) if (external is not None) else self.getUserInput("bones")
        if not keyword:
            return self.menu()
        history.add_to_history(keyword)
        videos = self.site.search(keyword)

        if not videos or len(videos) == 0:
            item = xbmcgui.ListItem("[COLOR=orange]" + "Нічого не знайдено" + "[/COLOR]")
            item.setArt({"icon": settings.icon_next})
            xbmcplugin.addDirectoryItem(self.handle, "", item, False)

        for video in videos:
            item = video.ListItem
            item_uri = router.build_uri("show", url=router.normalize_uri(video.link))
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, video.is_series)

        xbmcplugin.setContent(self.handle, "movies")
        xbmc.executebuiltin("Container.SetViewMode(504)")
        xbmcplugin.endOfDirectory(self.handle, True)

    def getUserInput(self, default: str = ""):
        kbd = xbmc.Keyboard()
        kbd.setDefault(default)
        kbd.setHeading(settings.language(1000))
        kbd.doModal()
        keyword = None

        if kbd.isConfirmed():
            if self.addon.getSetting("translit") == "true":
                keyword = translit.rus(kbd.getText())
            else:
                keyword = kbd.getText()
        return keyword

uakino = Uakino()
uakino.main()
