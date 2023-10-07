#!/usr/bin/python
# -*- coding: utf-8 -*-

# Writer (c) 2012-2021, MrStealth, dandy

import json
import os
from pydoc import Helper
import re
import sys
import socket
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import XbmcHelpers
import SearchHistory as history
from Translit import Translit

import helpers
import router
from voidboost import parse_streams
from helpers import log, show_message

import db_helper
import web_helper
from settings import settings
from video_info import video_info

#import ptvsd
#try:
#    ptvsd.enable_attach()
#    ptvsd.wait_for_attach()
#except:
#    print(f'Can`t start debugging')

#import debugpy
#debugpy.log_to(r"C:\Logs")
#debugpy.configure(python=r'c:\Program Files\Python38\python.exe')
#log(f'debugpy Current Version: {debugpy.__version__}')
#with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#    portInUse = s.connect_ex(('localhost', 5678)) == 0
#if portInUse == False:
#    debugpy.listen(('0.0.0.0', 5678))
#    debugpy.wait_for_client()
##debugpy.breakpoint()

log(f'User Current Version: {sys.version}')

common = XbmcHelpers
transliterate = Translit()

socket.setdefaulttimeout(120)

class HdrezkaTV:
    def __init__(self):
        log(f'__init__()')
        self.handle = int(sys.argv[1])
        settings.load()
        self.web = web_helper.web()
        self.sql = db_helper.sql(os.path.join(settings.addondir, 'hdrezka.db'))

    def main(self):
        params = router.parse_uri(sys.argv[2])
        #helpers.show_message(params['mode'])
        log(f'*** main params: {params}')
        mode = params.get('mode')
        
        if xbmcgui.Window(xbmcgui.getCurrentWindowId()).getProperty('prev_mode') != 'play_episode' and mode != 'play_episode': 
            xbmcgui.Window(xbmcgui.getCurrentWindowId()).setProperty('translator_id', None)
        xbmcgui.Window(xbmcgui.getCurrentWindowId()).setProperty('prev_mode', mode)
        
        if mode == 'play':
            self.play(params.get('url'))
        elif mode == 'play_episode':
            self.play_episode(
                params.get('url'),
                params.get('post_id'),
                params.get('season_id'),
                params.get('episode_id'),
                urllib.parse.unquote_plus(params['title']),
                params.get('image'),
                params.get('idt')
            )
        elif mode == 'show':
            self.show(params.get('uri'))
        elif mode == 'index':
            self.index(params.get('uri'), params.get('page'), params.get('query_filter'))
        elif mode == 'categories':
            self.categories()
        elif mode == 'sub_categories':
            self.sub_categories(params.get('uri'))
        elif mode == 'search':
            external = 'main' if 'main' in params else None
            if not external:
                external = 'usearch' if 'usearch' in params else None
            self.search(params.get('keyword'), external)
        elif mode == 'history':
            self.history()
        elif mode == 'collections':
            self.collections(int(params.get('page', 1)))
        else:
            self.menu()

    def menu(self):
        log(f'menu()')
        menu_items = (
            ('search', 'FF00FF00', 30000),
            ('history', 'FF00FF00', 30008),
            ('categories', 'FF00FF00', 30003),
            ('index', 'FFDDD2CC', 30009),
            ('index_popular', 'FFDDD2CC', 30010),
            ('index_soon', 'FFDDD2CC', 30011),
            ('index_watching', 'FFDDD2CC', 30012),
        )
        for mode, color, translation_id in menu_items:
            uri = router.build_uri(mode)
            if '_' in mode:
                mode, query_filter = mode.split('_')
                uri = router.build_uri(mode, query_filter=query_filter)
            item = xbmcgui.ListItem(f'[COLOR={color}]{settings.language(translation_id)}[/COLOR]')
            item.setArt({'thumb': settings.icon})
            xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

        xbmcplugin.setContent(self.handle, 'movies')
        xbmcplugin.endOfDirectory(self.handle, True)

    def categories(self):
        log(f'categories()')
        response = self.web.make_response('GET', '/')
        genres = common.parseDOM(response.text, "ul", attrs={"id": "topnav-menu"})

        titles = common.parseDOM(genres, "a", attrs={"class": "b-topnav__item-link"})
        links = common.parseDOM(genres, "a", attrs={"class": "b-topnav__item-link"}, ret='href')
        for i, title in enumerate(titles):
            title = common.stripTags(title)
            item_uri = router.build_uri('sub_categories', uri=links[i])
            item = xbmcgui.ListItem(title)
            item.setArt({'thumb': settings.icon})
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        item_uri = router.build_uri('collections')
        item = xbmcgui.ListItem('Подборки')
        item.setArt({'thumb': settings.icon})
        xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        xbmcplugin.setContent(self.handle, 'files')
        xbmcplugin.endOfDirectory(self.handle, True)

    def sub_categories(self, uri):
        log(f'sub_categories(uri = {uri})')
        response = self.web.make_response('GET', '/')
        genres = common.parseDOM(response.text, "ul", attrs={"class": "left"})

        titles = common.parseDOM(genres, "a")
        links = common.parseDOM(genres, "a", ret='href')

        item_uri = router.build_uri('index', uri=uri)
        item = xbmcgui.ListItem(f'[COLOR=FF00FFF0]{settings.language(30007)}[/COLOR]')
        item.setArt({'thumb': settings.icon})
        xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        for i, title in enumerate(titles):
            if not links[i].startswith(uri):
                continue
            item_uri = router.build_uri('index', uri=links[i])
            item = xbmcgui.ListItem(title)
            item.setArt({'thumb': settings.icon})
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        xbmcplugin.setContent(self.handle, 'files')
        xbmcplugin.endOfDirectory(self.handle, True)

    def collections(self, page):
        log(f'collections(page = {page})')
        uri = '/collections/'
        if page != 1:
            uri = f'/collections/page/{page}/'

        response = self.web.make_response('GET', uri)
        content = common.parseDOM(response.text, 'div', attrs={'class': 'b-content__collections_list clearfix'})
        titles = common.parseDOM(content, "a", attrs={"class": "title"})
        counts = common.parseDOM(content, 'div', attrs={"class": ".num"})
        links = common.parseDOM(content, "div", attrs={"class": "b-content__collections_item"}, ret="data-url")
        icons = common.parseDOM(content, "img", attrs={"class": "cover"}, ret="src")

        for i, name in enumerate(titles):
            item_uri = router.build_uri('index', uri=router.normalize_uri(links[i]))
            item = xbmcgui.ListItem(f'{name} [COLOR=55FFFFFF]({counts[i]})[/COLOR]')
            item.setArt({'thumb': icons[i]})
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        if not len(titles) < 32:
            item_uri = router.build_uri('collections', page=page + 1)
            item = xbmcgui.ListItem("[COLOR=orange]" + settings.language(30004) + "[/COLOR]")
            item.setArt({'icon': settings.icon_next})
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        xbmcplugin.setContent(self.handle, 'files')
        xbmcplugin.endOfDirectory(self.handle, True)

    def index(self, uri = None, page = None, query_filter = None):
        log(f'index(uri = {uri}, page = {page}, query_filter = {query_filter})')
        log(f'settings.only_ua: {settings.only_ua}')
        if not page: page = 0
        videos = []
        while len(videos) < 36:
            page = int(page) + 1
            page_videos = video_info.get_page_videos(uri, page, query_filter)
            for i, video in enumerate(page_videos):
                v = self.sql.get_video(video.id)
                if v: page_videos[i] = v 
                else: video.get_full_info()
            p = [video for video in page_videos if video.has_ukrainian] if settings.only_ua == True else page_videos
            videos.extend(p)
            if len(page_videos) < 36: break
        items = self.get_items(videos)
        for item , item_uri, is_folder in items:
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, is_folder)

        if not len(videos) < 36:
            params = {'page': 2, 'uri': uri}
            if page: params['page'] = int(page) + 1
            if query_filter: params['query_filter'] = query_filter
            item_uri = router.build_uri('index', **params)
            item = xbmcgui.ListItem("[COLOR=orange]" + settings.language(30004) + "[/COLOR]")
            item.setArt({'icon': settings.icon_next})
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        xbmcplugin.setContent(self.handle, 'movies')
        xbmcplugin.endOfDirectory(self.handle, True)

    def get_items(self, video_infos):
        log(f'get_items() items count: {len(video_infos)}')
        items = []

        for video in video_infos:
            #log(f'video: \r\n{video.__dict__}')
            title = video.formatted_title
            image = self._normalize_url(video.cover)
            item_uri = router.build_uri('show', uri=router.normalize_uri(video.link))
            year = video.year
            country = video.country
            genre = video.genre

            item = xbmcgui.ListItem(title)
            item.setArt({'thumb': image, 'icon': image, 'banner': image, 'fanart': image})
            item.setInfo(
                type='video',
                infoLabels={
                    'title': title,
                    'genre': genre,
                    'year': year,
                    'country': country,
                    'plot': video.description,
                    'rating': video.rating.imdb,
                    'duration': video.duration
                }
            )
            is_series = video.is_series
            is_folder = True
            if not is_series:
                item.setProperty('IsPlayable', 'true')
                is_folder = False
            items.append([item, item_uri, is_folder])
        return items

    def select_stream(self, streams):
        log(f'select_stream() \r\nstreams = {streams}')
        if settings.quality != 'select':
            for name, quality, url in streams:
                if (name == settings.quality) or (int(settings.quality.split('p')[0]) >= quality):
                    log(f'selected quality name: {name}')
                    return url
        else:
            dialog = xbmcgui.Dialog()
            items = [name for name, _, _ in streams]
            log(f'items: {items}')
            index = dialog.select('', items)
            if index < 0: return streams[0][2]
            log(f'result: {streams[index][2]}')
            return streams[index][2]

    def select_translator(self, video):
        log(f'select_translator')
        dialog = xbmcgui.Dialog()
        items = [translation.formatted_title for translation in video.translations]
        index = dialog.select(settings.language(30006), items)
        if index < 0: return video.default_translation_id
        return video.translations[index].id

    def show(self, uri):
        log(f'show(uri = {uri})')
        video = video_info()
        video.link = settings.url + '/' + uri
        video.id = re.findall('\/(\d+?)-', video.link)[0]
        v = self.sql.get_video(video.id)
        if v: video = v 
        else: video.get_full_info()
        #log(f'translation: {video.translations}')
        #log(f'default translations: {video.default_translation_id}')
        
        saved_translator_id = xbmcgui.Window(xbmcgui.getCurrentWindowId()).getProperty('translator_id')
        translator_id = saved_translator_id if not saved_translator_id == ''else video.default_translation_id
        if settings.translator == "select" and len(video.translations) > 1 and saved_translator_id == '':
            translator_id = self.select_translator(video)
            xbmcgui.Window(xbmcgui.getCurrentWindowId()).setProperty('translator_id', str(translator_id))
            saved_translator_id = xbmcgui.Window(xbmcgui.getCurrentWindowId()).getProperty('translator_id')

        if video.is_series:
            self.show_series(video, translator_id)
        else:
            self.show_video(video, translator_id)

    def show_series(self, video, translator_id):
        log(f'show_series')
        episodes = self.web.get_episodes(video.id, video.link, translator_id)
        for episode in episodes:
            item_uri = router.build_uri(
                'play_episode',
                url = video.link,
                urlm = video.link,
                post_id = video.id,
                season_id = episode.season_number,
                episode_id = episode.number,
                title = episode.formatted_title,
                image = video.cover,
                idt = translator_id
            )
            item = xbmcgui.ListItem(episode.formatted_title)
            item.setArt({'thumb': video.cover, 'icon': video.cover})
            item.setInfo(type='Video', infoLabels={'title': episode.formatted_title})
            item.setProperty('IsPlayable', 'true')
            log(f'item_uri: {item_uri}')
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, False)
        xbmcplugin.setContent(self.handle, 'episodes')
        xbmcplugin.endOfDirectory(self.handle, True)

    def show_video(self, video, translator_id):
        log(f'show_video()')
        links, subtitles = self.web.get_movie(video.id, video.link, translator_id)
        if not links: 
            video.get_full_info()
            links = video.default_stream_url
        url = self.select_stream(links)
        self.play(url, subtitles)

    def history(self):
        log(f'history()')
        words = history.get_history()
        for word in reversed(words):
            uri = router.build_uri('search', keyword=word, main=1)
            item = xbmcgui.ListItem(word)
            item.setArt({'thumb': settings.icon, 'icon': settings.icon})
            xbmcplugin.addDirectoryItem(self.handle, uri, item, True)
        xbmcplugin.endOfDirectory(self.handle, True)

    def get_user_input(self):
        kbd = xbmc.Keyboard()
        kbd.setDefault('')
        kbd.setHeading(settings.language(30000))
        kbd.doModal()
        keyword = None

        if kbd.isConfirmed():
            if settings.use_transliteration:
                keyword = transliterate.rus(kbd.getText())
            else:
                keyword = kbd.getText()

            history.add_to_history(keyword)

        return keyword

    def search(self, keyword, external):
        log(f'search(keyword = {keyword}, external = {external})')
        keyword = urllib.parse.unquote_plus(keyword) if (external is not None) else self.get_user_input()
        if not keyword:
            return self.menu()

        params = {
            "do": "search",
            "subaction": "search",
            "q": str(keyword)
        }
        response = self.web.make_response('GET', '/search/', params=params, cookies={"dle_user_taken": '1'})
        helpers.write_to_file(response.text)

        videos = video_info.parse_page(response.text)
        for i, video in enumerate(videos):
            v = self.sql.get_video(video.id)
            if v: videos[i] = v  
            else: video.get_full_info()
        items = self.get_items(videos)
        for item , item_uri, is_folder in items:
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, is_folder)

        xbmcplugin.setContent(self.handle, 'movies')
        xbmcplugin.endOfDirectory(self.handle, True)

    def play(self, url, subtitles = None):
        log(f'play() \r\nurl = {url} \r\nsubtitles = {subtitles}')
        item = xbmcgui.ListItem(path=url)
        if subtitles: item.setSubtitles(subtitles)
        xbmcplugin.setResolvedUrl(self.handle, True, item)

    def play_episode(self, url, post_id, season_id, episode_id, title, image, idt):
        log(f'play_episode() \r\nurl = {url} \r\npost_id = {post_id} \r\nseason_id = {season_id} \r\nepisode_id = {episode_id} \r\ntitle = {title} \r\nimage = {image} \r\nidt = {idt} \r\n')
        links, subtitles = self.web.get_stream(post_id, url, idt, season_id, episode_id)

        url = self.select_stream(links)
        self.play(url, subtitles)

    def _normalize_url(self, item):
        if not item.startswith("http"):
            item = self.url + item
        return item


plugin = HdrezkaTV()
plugin.main()
