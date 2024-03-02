import helpers
import re
import requests
import time
import video_info

from voidboost import parse_streams
from settings import Settings as settings
import XbmcHelpers

class Web:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
    #USER_AGENT = "AppleWebKit/530.20 (KHTML, like Gecko)"

    def __init__(self):
        self.domain = settings.domain
        self.url = settings.url
        self.session = self._load_session()
        self.proxies = self._load_proxy_settings()

    def _load_proxy_settings(self):
        if settings.addon.getSetting("use_proxy") == "false":
            return False
        proxy_protocol = settings.addon.getSetting("protocol")
        proxy_url = settings.addon.getSetting("proxy_url")
        return {
            "http": proxy_protocol + "://" + proxy_url,
            "https": proxy_protocol + "://" + proxy_url
        }

    def _load_session(self):
        session = requests.Session()
        session.headers = {
                "Host": self.domain,
                "Referer": self.domain,
                "User-Agent": self.USER_AGENT,
            }
        return session

    def make_request(self, method, uri, params=None, data=None, cookies=None, headers=None):
        url = f"{self.url}{uri}" if uri[:4] != "http" else uri
        helpers.log(f"make_request() method: {method}, url: {url}")
        startTime = time.time()
        result = self.session.request(method, url, params=params, data=data, headers=headers, cookies=cookies)
        helpers.log(f"make_request() execution time: {int((time.time() - startTime) * 1000)}ms")
        return result

    def get_episodes(self, id, url, translator_id):
        response = self.get_cdn_series(id, url, translator_id, "get_episodes").json()
        html = response["episodes"]
        season_ids = XbmcHelpers.parseDOM(html, "li", ret = "data-season_id")
        episode_ids = XbmcHelpers.parseDOM(html, "li", ret = "data-episode_id")
        titles = XbmcHelpers.parseDOM(html, "li")
        episodes = []
        for i in range(len(season_ids)):
            episode = video_info.episode()
            episode.season_number = season_ids[i]
            episode.number = episode_ids[i]
            episode.title = titles[i]
            episodes.append(episode)
        return episodes

    def get_stream(self, id, url, translator_id, season = None, episode = None):
        response = self.get_cdn_series(id, url, translator_id, "get_stream", season, episode).json()
        helpers.log(f"response: {response}")
        links = parse_streams(response["url"])
        subtitles = re.findall(r"(https?:\/\/[^\s,]+)", response["subtitle"]) if response["subtitle"] else None
        return links, subtitles

    def get_movie(self, id, url, translator_id):
        response = self.get_cdn_series(id, url, translator_id, "get_movie").json()
        helpers.log(f"response: {response}")
        if response["success"] is False: return None, None
        links = parse_streams(response["url"])
        subtitles = re.findall(r"(https?:\/\/[^\s,]+)", response["subtitle"]) if response["subtitle"] else None
        return links, subtitles

    def get_cdn_series(self, id, url, translator_id, action, season = None, episode = None):
        data = {
            "id": id,
            "translator_id": translator_id,
            "action": action
        }
        if season: data["season"] = season
        if season: data["episode"] = episode

        headers = {
            "Host": settings.domain,
            "Origin": settings.url,
            "Referer": url,
            "User-Agent": self.USER_AGENT,
            "X-Requested-With": "XMLHttpRequest"
        }
        response = self.make_request("POST", "/ajax/get_cdn_series/", data=data, headers=headers)
        return response
