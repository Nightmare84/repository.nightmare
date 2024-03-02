import xbmc, xbmcplugin, xbmcgui, xbmcaddon
import os, urllib, sys, socket, re
from ast import Try
import json
#import router
import time
from typing import List

#import voidboost
#import web_helper
import XbmcHelpers

import db_helper
import web_helper
import gzip
from helpers import log, show_message, write_to_file, merge_lists, insertString, repairImageTag
from settings import Settings as settings
from mem_storage import MemStorage
from video_info import VideoInfo

common = XbmcHelpers

class SiteParser:
    def __init__(self):
        self.storage = MemStorage()
        self.web = web_helper.Web()
        self.sql = db_helper.Sql(os.path.join(settings.addondir, "cache.db"))

    def getCategories(self) -> list:
        log("getCategories")
        categories = self.storage["subCategories"]
        if categories is not None:
            log("\nLoaded from cache\n")
            return categories

        categories = [
            ["Фільми", "/filmy", []],
            ["Серіали", "/seriesss", []],
            ["Мультфільми", "/cartoon", []],
        ]

        response = common.fetchPage({"link": settings.url})
        content = response["content"].decode("utf-8").replace("\t", "").replace("\n", "")

        if response["status"] == 200:
            nav = common.parseDOM(content, "nav")
            links = common.parseDOM(nav[0], "a", ret="href")
            titles = common.parseDOM(nav[0], "a")
            subs = merge_lists(links, titles)
            # write_to_file(subs)

            for i, category in enumerate(categories):
                categories[i][2] = list(filter(lambda sub:
                                               category[1] in sub[0]
                                               and len(sub[0]) - len(category[1]) > 1
                                               and "best" not in sub[0]
                                               and "colections" not in sub[0],
                subs))
            # write_to_file(categories)
            self.storage["subCategories"] = categories
            log("\nLoaded from site\n")
            return categories

    def getSubCategoryItems(self, url: str, page: int) -> List[VideoInfo]:
        uri = f"{url}page/{page}"
        log(f"uri: {uri}")
        response = common.fetchPage({"link": uri})

        if response["status"] == 200:
            content = response["content"].decode("utf-8").replace("\t", "").replace("\n", "").replace("&#039;", "'")

        videos = self.__parsePage(content)
        return videos

    def getMovieURL(self, url: str) -> str:
        video = VideoInfo()
        video.link = settings.url + "/" + url
        video.id = re.findall(r"\/(\d+?)-", video.link)[0]
        log(f"video.id: {video.id}")
        log(f"URL: {url}")
        page = self.web.make_request("GET", url).text
        # write_to_file(page)
        ashdiLink = common.parseDOM(page, "link", attrs={"itemprop": "video"}, ret="value")[0]
        log(f"ashdiLink: {ashdiLink}")
        if len(ashdiLink) == 0:
            playerUrl = f"/engine/ajax/playlists.php?news_id={video.id}&xfield=playlist"
            log(f"playerUrl: {playerUrl}")
            playlistJson = self.web.make_request("GET", playerUrl).text
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
        return link

    def search(self, keyword: str) -> List[VideoInfo]:
        videos = []
        page = 1
        while True:
            responseText = self.__getSearchPage(keyword, page)
            v = self.__parsePage(responseText)
            if len(v) == 0: break
            videos.extend(v)
            page += 1
        write_to_file(videos)
        return videos

    def searchShort(self, keyword: str) -> List[VideoInfo]:
        url = f"{settings.url}/engine/lazydev/dle_search/ajax.php"
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": settings.domain,
            "Referer": settings.url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        }
        values = {"story": keyword}

        data = urllib.parse.urlencode(values).encode("utf-8")
        req = urllib.request.Request(url, data, headers)
        html = None

        try:
            response = urllib.request.urlopen(req)
            responseText = gzip.decompress(response.read()).decode("utf-8")
            responseJson = json.loads(responseText)
            html = responseJson["content"]
            html = repairImageTag(html).replace("\r\n", "").replace("&#039;", "'")
            html = re.sub(r"\s{2,}", " ", html)
            #write_to_file(html)
        except Exception as e:
            log(f"Exception: {e}")
            pass
        videos = self.__parseSearchShortJson(html)
        return videos

    def __getSearchPage(self, keyword: str, page: int = 1) -> str:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": settings.domain,
            "Referer": settings.url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        }
        values = {"do": "search", "subaction": "search", "from_page": page, "story": keyword}

        url = f"{settings.url}?{urllib.parse.urlencode(values)}"
        req = urllib.request.Request(url, None, headers)

        response = urllib.request.urlopen(req)
        responseText = gzip.decompress(response.read()).decode("utf-8").replace("&#039;", "'")
        return responseText

    def __parsePage(self, html: str) -> List[VideoInfo]:
        dleContent = common.parseDOM(html, "div", attrs={"id": "dle-content"})[0]
        dleContent = repairImageTag(dleContent)

        movies = common.parseDOM(dleContent, "div", attrs={"class": "movie-item short-item"})
        # write_to_file(movies)
        log(f"movies count {len(movies)}")
        videos = []
        for movieHtml in movies:
            video = VideoInfo()
            video.title = common.parseDOM(movieHtml, "div", attrs={"class": "deck-title"})[0]
            video.link = common.parseDOM(movieHtml, "a", attrs={"class": "movie-title"}, ret="href")[0]
            video.cover = settings.url + common.parseDOM(movieHtml, "img", ret="src")[0]
            video.description = common.parseDOM(movieHtml, "span", attrs={"class": "desc-about-text"})[0]
            # log(f"video.description: {video.description}")
            clearfixes = common.parseDOM(movieHtml, "div", attrs={"class": "movie-desk-item clearfix"})
            # write_to_file(movieHtml)
            for clearfix in clearfixes:
                label = common.parseDOM(clearfix, "div", attrs={"class": "fi-label"})[0]
                value = common.parseDOM(clearfix, "div", attrs={"class": "deck-value"})[0]
                # log(f"{label}: {value}")

                if "imdb" in label:
                    video.rating = float(value)
                if "Жанр:" in label:
                    video.genre = value
                if "Рік виходу:" in label:
                    yearStr = common.parseDOM(value, "a")[0] if "<a" in value else ""
                    video.year = int(yearStr) if yearStr.isdecimal() else 0
            # log(f"\r\ntitle: {video.title}\r\ncover: {video.cover}\r\nrating: {video.rating}\r\ngenre: {video.genre}\r\nyear: {video.year}\r\n\r\n\r\n\r\n")
            videos.append(video)
        return videos

    def __parseSearchShortJson(self, html: str) -> List[VideoInfo]:
        #write_to_file(html)
        videos = []

        links = common.parseDOM(html, "a", ret = "href")
        nodes = common.parseDOM(html, "a")

        for i, node in enumerate(nodes):
            if "<img" not in node: continue
            video = VideoInfo()
            video.link = links[i]
            video.cover = common.parseDOM(node, "img", ret="src")[0]
            video.title = common.parseDOM(node, "span", attrs={"class": "searchheading"})[0]
            extendInfo = common.parseDOM(node, "div", attrs={"class": "search-extend-info"})[0]
            video.year = common.parseDOM(extendInfo, "span")[0]
            ratingSpan = common.parseDOM(extendInfo, "span")[1]
            video.rating = re.sub("<.*>", "", ratingSpan).replace(":&nbsp;", "")

            videos.append(video)
        write_to_file(nodes)
        #write_to_file(videos[0].toJson())
        return videos

