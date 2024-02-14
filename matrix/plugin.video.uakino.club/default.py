#!/usr/bin/python

import os, urllib, sys, socket, re
import xbmc, xbmcplugin, xbmcgui, xbmcaddon
import uppod
from helpers import log, show_message, write_to_file, merge_lists, insertString, repairImageTag
from video_info import VideoInfo
from settings import settings
import json
import router
import web_helper
import XbmcHelpers
import Translit as translit
from mem_storage import MemStorage

common = XbmcHelpers
translit = translit.Translit(encoding="cp1251")

# try:
#     sys.path.append(os.path.dirname(__file__) + "/../plugin.video.unified.search")
#     from unified_search import UnifiedSearch
# except BaseException:
#     # show_message("UnifiedSearch not found")
#     log("\r\n\r\nUnifiedSearch not found")
#     pass


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

        self.web = web_helper.web()

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
        if mode == "movie" or mode == "show":
            self.getMovieURL(url)
        if mode == "subcategory":
            self.getSubCategoryItems(url, page)
        if mode == "category":
            self.getCategoryItems(url)
        if mode == "search":
            self.search(keyword)
        elif mode is None:
            self.menu()

    def menu(self):
        uri = sys.argv[0] + "?mode={}&url={}".format("search", self.url)
        item = xbmcgui.ListItem(f"[COLOR=FF00FF00]{settings.language(30001)}[/COLOR]")
        log(f"SSSSSSSSS: '{settings.language(32001)}'")
        item.setArt({self.icon})
        xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

        self.getCategories()
        xbmcplugin.endOfDirectory(self.handle, True)

    def getCategories(self):
        log("getCategories")
        categories = [
            ["Фільми", "/filmy", []],
            ["Серіали", "/seriesss", []],
            ["Мультфільми", "/cartoon", []],
        ]

        url = self.url
        response = common.fetchPage({"link": url})
        content = response["content"].decode("utf-8").replace("\t", "").replace("\n", "")

        if response["status"] == 200:
            nav = common.parseDOM(content, "nav")
            links = common.parseDOM(nav[0], "a", ret="href")
            titles = common.parseDOM(nav[0], "a")
            subs = merge_lists(links, titles)
            #write_to_file(subs)
            log(f"links length: {len(links)}")

            for i, category in enumerate(categories):
                categories[i][2] = list(filter(lambda sub: category[1] in sub[0] and len(sub[0]) - len(category[1]) > 1 and "best" not in sub[0] and "colections" not in sub[0], subs))
            # write_to_file(categories)

            storage = MemStorage()
            storage["subCategories"] = categories

            for title, link, subcategories in categories:
                url = self.url + link
                uri = f"{sys.argv[0]}?mode=category&url={url}"
                item = xbmcgui.ListItem(title)
                # item.setArt({"thumb": self.icon})
                xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

        else:
            self.showErrorMessage("getCategories(): Bad response status %s" % response["status"])

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
            log(f"uri: {uri}")
            item = xbmcgui.ListItem(title)
            item.setArt({"thumb": self.icon})
            xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

        xbmcplugin.endOfDirectory(self.handle, True)

    def getSubCategoryItems(self, url, page):
        log(f"getSubCategoryItems url: {url} page: {page}")

        uri = f"{url}page/{page}"
        log(f"uri: {uri}")
        response = common.fetchPage({"link": uri})

        if response["status"] == 200:
            content = response["content"].decode("utf-8").replace("\t", "").replace("\n", "")

            dleContent = common.parseDOM(content, "div", attrs={"id": "dle-content"})[0]
            dleContent = repairImageTag(dleContent)

            movies = common.parseDOM(dleContent, "div", attrs={"class": "movie-item short-item"})
            #write_to_file(movies)
            log(f"movies count {len(movies)}")
            video = VideoInfo()
            for movieHtml in movies:
                video.title = common.parseDOM(movieHtml, "div", attrs={"class": "deck-title"})[0]
                video.link = common.parseDOM(movieHtml, "a", attrs={"class": "movie-title"}, ret="href")[0]
                video.cover = self.url + common.parseDOM(movieHtml, "img", ret="src")[0]
                video.description = common.parseDOM(movieHtml, "span", attrs={"class": "desc-about-text"})[0]
                #log(f"video.description: {video.description}")
                clearfixes = common.parseDOM(movieHtml, "div", attrs={"class": "movie-desk-item clearfix"})
                #write_to_file(movieHtml)
                for clearfix in clearfixes:
                    label = common.parseDOM(clearfix, "div", attrs={"class": "fi-label"})[0]
                    value = common.parseDOM(clearfix, "div", attrs={"class": "deck-value"})[0]
                    #log(f"{label}: {value}")

                    if "imdb" in label:
                        video.rating = float(value)
                    if "Жанр:" in label:
                        video.genre = value
                    if "Рік виходу:" in label:
                        video.year = common.parseDOM(value, "a")[0] if len(value) > 4 else "----"
                        
                # log(f"\r\ntitle: {video.title}\r\ncover: {video.cover}\r\nrating: {video.rating}\r\ngenre: {video.genre}\r\nyear: {video.year}\r\n\r\n\r\n\r\n")

                item = xbmcgui.ListItem(video.formatted_title)
                item.setProperty("IsPlayable", "true")
                item.setInfo(
                    type="video",
                    infoLabels={
                        "title": video.title,
                        "genre": video.genre,
                        "year": video.year,
                        # "country": country,
                        "plot": video.description,
                        "rating": video.rating,
                        # "duration": video.duration
                    },
                )
                item_uri = router.build_uri("show", url=router.normalize_uri(video.link))
                item.setArt({"thumb": video.cover, "icon": video.cover, "banner": video.cover, "fanart": video.cover})
                xbmcplugin.addDirectoryItem(self.handle, item_uri, item, False)

            """
            media_line = ""
            titlesA = common.parseDOM(media_line, "a", ret="title")
            pathsA = common.parseDOM(media_line, "a", attrs={"class": "fleft thumb"}, ret="href")

            titlesB = common.parseDOM(media_line, "a", attrs={"class": "heading"})
            pathsB = common.parseDOM(media_line, "a", attrs={"class": "heading"}, ret="href")

            images = common.parseDOM(media_line, "img", ret="src")

            # print "Found A: %d"%len(titlesA)
            # print "Found B: %d"%len(titlesB)
            # print "Found images %d"%len(images)

            if titlesA and titlesB:
                self.log("*** This is a mix of seasons and movies")

                for i, title in enumerate(titlesA):
                    items_counter += 1

                    link = f"{self.url}/{pathsA[i]}"
                    image = self.url + images[i] if images[i].find("http") == -1 else images[i]

                    uri = sys.argv[0] + "?mode=subcategory&url=%s" % link
                    item = xbmcgui.ListItem(title, thumbnailImage=image, iconImage=self.icon)
                    xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

                for i, title in enumerate(titlesB):
                    items_counter += 1

                    link = f"{self.url}/{pathsB[i]}"
                    image = self.url + images[len(titlesA) + i] if images[len(titlesA) + i].find("http") == -1 else images[len(titlesA) + i]

                    uri = sys.argv[0] + "?mode=movie&url=%s" % link
                    item = xbmcgui.ListItem(title, thumbnailImage=image, iconImage=self.icon)
                    item.setProperty("IsPlayable", "true")
                    xbmcplugin.addDirectoryItem(self.handle, uri, item, False)

            elif titlesA:
                self.log("*** This is a season")

                for i, title in enumerate(titlesA):
                    items_counter += 1

                    link = f"{self.url}/{pathsA[i]}"
                    image = self.url + images[i] if images[i].find("http") == -1 else images[i]

                    uri = sys.argv[0] + "?mode=subcategory&url=%s" % link
                    item = xbmcgui.ListItem(title, thumbnailImage=image, iconImage=self.icon)
                    xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

            elif titlesB:
                self.log("*** This is a movie")

                ul = common.parseDOM(media_line, "ul")

                for i, title in enumerate(titlesB):
                    genres = common.stripTags(common.parseDOM(ul[i], "li")[0])

                    try:
                        description = common.stripTags(common.parseDOM(ul[i], "li")[2])
                    except IndexError:
                        description = common.stripTags(common.parseDOM(ul[i], "li")[1])

                    items_counter += 1

                    link = f"{self.url}/{pathsA[i]}"
                    image = self.url + images[i] if images[i].find("http") == -1 else images[i]
                    info = {"title": title, "genre": genres, "plot": description}

                    uri = sys.argv[0] + "?mode=movie&url=%s" % link
                    item = xbmcgui.ListItem(title, thumbnailImage=image, iconImage=self.icon)

                    item.setInfo(type="Video", infoLabels=info)
                    item.setProperty("IsPlayable", "true")
                    xbmcplugin.addDirectoryItem(self.handle, uri, item, False)
            else:
                log("Exception")

        else:
            self.showErrorMessage("getSubCategoryItems(): Bad response status %s" % response["status"])

        if items_counter == 16:
            self.nextPage(url, page)
        """

            params = {"page": 2, "url": url}
            if page:
                params["page"] = int(page) + 1
            item_uri = router.build_uri("subcategory", **params)
            log(f"url: {url}, item_uri: {item_uri}")
            item = xbmcgui.ListItem("[COLOR=orange]" + settings.language(30003) + "[/COLOR]")
            item.setArt({"icon": settings.icon_next})
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        xbmcplugin.setContent(self.handle, "movies")
        xbmcplugin.endOfDirectory(self.handle, True)

    def getMovieURL(self, url):
        log(f"getMovieURL url: {url}")
        video = VideoInfo()
        video.link = settings.url + "/" + url
        video.id = re.findall(r"\/(\d+?)-", video.link)[0]
        log(f"video.id: {video.id}")

        page = self.web.make_response("GET", url).text
        # write_to_file(page)
        ashdiLink = common.parseDOM(page, "link", attrs={"itemprop": "video"}, ret="value")[0]
        log(f"ashdiLink: {ashdiLink}")
        if len(ashdiLink) == 0:
            playerUrl = f"/engine/ajax/playlists.php?news_id={video.id}&xfield=playlist"
            log(f"playerUrl: {playerUrl}")
            playlistJson = self.web.make_response("GET", playerUrl).text
            playlistHtml = json.loads(playlistJson)["response"]
            #write_to_file(playlistHtml)
            ashdiLink = common.parseDOM(playlistHtml, "li", ret="data-file")[0]
            log(f"ashdiLink: {ashdiLink}")

        playlistHtml = common.fetchPage({"link": ashdiLink})["content"].decode("utf-8")
        b = playlistHtml.find('file:"')
        e = playlistHtml.find('"', b + 6)
        playlistLink = playlistHtml[b + 6 : e]
        # write_to_file(playlistLink)

        m3u = common.fetchPage({"link": playlistLink})["content"].decode("utf-8")
        # write_to_file(m3u)

        links = sorted([[int(link.split("/")[-2]), link] for link in m3u.splitlines() if "http" in link], key=lambda link: link[0], reverse=True)
        log(f"links: {links}")

        link = links[0][1]
        for lnk in links:
            if lnk[0] <= int("".join(c for c in settings.quality if c.isdigit())):
                link = lnk[1]
                break
        log(f"link: {link}")

        item = xbmcgui.ListItem(path=link)
        # if subtitles: item.setSubtitles(subtitles)
        xbmcplugin.setResolvedUrl(self.handle, True, item)

        # playerUrl = f"/engine/ajax/playlists.php?news_id={video.id}&xfield=playlist"
        # log(f"playerUrl: {playerUrl}")
        # #player = common.fetchPage({"link": f"{self.url}playerUrl"})
        # player = self.web.make_response("GET", playerUrl).text
        # write_to_file(player)
        # page = common.fetchPage({"link": video.link})["content"].decode("utf-8")  # .replace("\t", "").replace("\n", "")

    def play(self, url):
        log(f"play url: {url}")

        item = xbmcgui.ListItem(path=url)
        xbmcplugin.setResolvedUrl(self.handle, True, item)

    def getUserInput(self):
        kbd = xbmc.Keyboard()
        kbd.setDefault("")
        kbd.setHeading(settings.language(1000))
        kbd.doModal()
        keyword = None

        if kbd.isConfirmed():
            if self.addon.getSetting("translit") == "true":
                keyword = translit.rus(kbd.getText())
            else:
                keyword = kbd.getText()
        return keyword

    def search(self, keyword):
        log(f"search keyword: {keyword}")
        keyword = self.getUserInput()

        if keyword:
            keyword = self.encode(keyword)

            url = "http://uakino.club/search_result.php"

            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "gzip,deflate",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "	uakino.club",
                "Referer": url,
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:17.0) Gecko/17.0 Firefox/17.0",
            }

            values = {"search_id": keyword, "send": "%D0%9F%D0%BE%D0%B8%D1%81%D0%BA"}

            data = urllib.urlencode(values)
            req = urllib.Request(url, data, headers)
            html = None

            try:
                response = urllib.urlopen(req)
                html = response.read()
            except Exception:
                pass

            self.log(keyword)

            us_titles = []
            us_links = []
            us_images = []

            if html:
                media_line = common.parseDOM(html, "div", attrs={"class": "media_line"})

                titlesA = common.parseDOM(media_line, "a", ret="title")
                pathsA = common.parseDOM(media_line, "a", attrs={"class": "fleft thumb"}, ret="href")

                titlesB = common.parseDOM(media_line, "a", attrs={"class": "heading"})
                pathsB = common.parseDOM(media_line, "a", attrs={"class": "heading"}, ret="href")

                images = common.parseDOM(media_line, "img", ret="src")

                items_counter = 0

                # print "Found A: %d"%len(pathsA)
                # print "Found B: %d"%len(pathsB)
                # print "Found images %d"%len(images)

                if titlesA and titlesB:
                    # print "*** This is a mix of seasons and movies"
                    log("*** This is a mix of seasons and movies")
                    for i, title in enumerate(titlesA):
                        items_counter += 1

                        link = f"{self.url}/{pathsA[i]}"
                        image = self.url + images[i] if "http" not in images[i] else images[i]

                        # INFO: Collect search results
                        us_titles.append(title)
                        us_links.append(link)
                        us_images.append(image)

                        uri = sys.argv[0] + "?mode=subcategory&url=%s" % link
                        item = xbmcgui.ListItem(title, thumbnailImage=image, iconImage=self.icon)
                        xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

                    for i, title in enumerate(titlesB):
                        items_counter += 1

                        link = f"{self.url}/{pathsB[i]}"
                        image = self.url + images[len(pathsB) + i] if "http" not in images[len(pathsB) + i] else images[len(pathsB) + i]

                        # INFO: Collect search results
                        us_titles.append(title)
                        us_links.append(link)
                        us_images.append(image)

                        uri = sys.argv[0] + "?mode=movie&url=%s" % link
                        item = xbmcgui.ListItem(title, thumbnailImage=image, iconImage=self.icon)
                        item.setProperty("IsPlayable", "true")
                        xbmcplugin.addDirectoryItem(self.handle, uri, item, False)

                elif titlesA:
                    # print "*** This is a season"
                    log("*** This is a season")

                    for i, title in enumerate(titlesA):
                        items_counter += 1

                        link = f"{self.url}/{pathsA[i]}"
                        image = self.url + images[i] if "http" not in images[i] else images[i]

                        # INFO: Collect search results
                        us_titles.append(title)
                        us_links.append(link)
                        us_images.append(image)

                        uri = sys.argv[0] + "?mode=subcategory&url=%s" % link
                        item = xbmcgui.ListItem(title, thumbnailImage=image, iconImage=self.icon)
                        xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

                elif titlesB:
                    # print "*** This is a movie"
                    log("*** This is a movie")

                    ul = common.parseDOM(media_line, "ul")

                    for i, title in enumerate(titlesB):
                        genres = common.stripTags(common.parseDOM(ul[i], "li")[0])

                        try:
                            description = common.stripTags(common.parseDOM(ul[i], "li")[2])
                        except IndexError:
                            description = common.stripTags(common.parseDOM(ul[i], "li")[1])

                        items_counter += 1

                        link = f"{self.url}/{pathsA[i]}"
                        image = self.url + images[i] if "http" not in images[i] else images[i]
                        info = {"title": title, "genre": genres, "plot": description}

                        # INFO: Collect search results
                        us_titles.append(title)
                        us_links.append(link)
                        us_images.append(image)

                        uri = sys.argv[0] + "?mode=movie&url=%s" % link
                        item = xbmcgui.ListItem(title, thumbnailImage=image, iconImage=self.icon)

                        item.setInfo(type="Video", infoLabels=info)
                        item.setProperty("IsPlayable", "true")
                        xbmcplugin.addDirectoryItem(self.handle, uri, item, False)
                else:
                    item = xbmcgui.ListItem(settings.language(9001), thumbnailImage=self.icon)
                    xbmcplugin.addDirectoryItem(self.handle, "", item, False)
            else:
                self.showErrorMessage("%s: Request timeout" % self.id)

            xbmc.executebuiltin("Container.SetViewMode(50)")
            xbmcplugin.endOfDirectory(self.handle, True)

        else:
            self.menu()


uakino = Uakino()
uakino.main()
