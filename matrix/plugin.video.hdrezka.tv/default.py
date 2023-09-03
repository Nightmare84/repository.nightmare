#!/usr/bin/python
# -*- coding: utf-8 -*-

# Writer (c) 2012-2021, MrStealth, dandy

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

import requests

import helpers
import router
from voidboost import parse_streams
from helpers import log, get_media_attributes, color_rating, show_message

import dbhelper

#import ptvsd
#try:
#    ptvsd.enable_attach()
#    ptvsd.wait_for_attach()
#except:
#    print(f'Can`t start debugging')



print(f'User Current Version:-{sys.version}')

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

#USER_AGENT = "Mozilla/5.0 (Windows NT 6.2; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0"
USER_AGENT = "AppleWebKit/535.19 (KHTML, like Gecko)"

class HdrezkaTV:
    def __init__(self):

        self.id = 'plugin.video.hdrezka.tv'
        self.addon = xbmcaddon.Addon(self.id)
        self.addondir = self.addon.getAddonInfo('path')
        self.icon = self.addon.getAddonInfo('icon')
        self.icon_next = os.path.join(self.addondir, 'resources/icons/next.png')
        self.language = self.addon.getLocalizedString
        self.handle = int(sys.argv[1])
        
        # settings
        self.use_transliteration = self.addon.getSettingBool('use_transliteration')
        self.only_ua = self.addon.getSetting('only_ua')
        self.quality = self.addon.getSetting('quality')
        self.translator = self.addon.getSetting('translator')
        self.domain = self.addon.getSetting('domain')
        self.show_description = self.addon.getSettingBool('show_description')

        self.url = self.addon.getSetting('dom_protocol') + '://' + self.domain
        self.proxies = self._load_proxy_settings()
        self.session = self._load_session()

        self.sql = dbhelper.sql(os.path.join(self.addondir, 'hdrezka.db'))

    def _load_session(self):
        session = requests.Session()
        session.headers = {
                'Host': self.domain,
                'Referer': self.domain,
                'User-Agent': USER_AGENT,
            }
        return session

    def _load_proxy_settings(self):
        if self.addon.getSetting('use_proxy') == 'false':
            return False
        proxy_protocol = self.addon.getSetting('protocol')
        proxy_url = self.addon.getSetting('proxy_url')
        return {
            'http': proxy_protocol + '://' + proxy_url,
            'https': proxy_protocol + '://' + proxy_url
        }

    def make_response(self, method, uri, params=None, data=None, cookies=None, headers=None):
        return self.session.request(method, self.url + uri, params=params, data=data, headers=headers, cookies=cookies)

    def main(self):
        params = router.parse_uri(sys.argv[2])
        #helpers.show_message(params['mode'])
        log(f'*** main params: {params}')
        mode = params.get('mode')
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
            item = xbmcgui.ListItem(f'[COLOR={color}]{self.language(translation_id)}[/COLOR]')
            item.setArt({'thumb': self.icon})
            xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

        xbmcplugin.setContent(self.handle, 'movies')
        xbmcplugin.endOfDirectory(self.handle, True)

    def categories(self):
        response = self.make_response('GET', '/')
        genres = common.parseDOM(response.text, "ul", attrs={"id": "topnav-menu"})

        titles = common.parseDOM(genres, "a", attrs={"class": "b-topnav__item-link"})
        links = common.parseDOM(genres, "a", attrs={"class": "b-topnav__item-link"}, ret='href')
        for i, title in enumerate(titles):
            title = common.stripTags(title)
            item_uri = router.build_uri('sub_categories', uri=links[i])
            item = xbmcgui.ListItem(title)
            item.setArt({'thumb': self.icon})
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        item_uri = router.build_uri('collections')
        item = xbmcgui.ListItem('Подборки')
        item.setArt({'thumb': self.icon})
        xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        xbmcplugin.setContent(self.handle, 'files')
        xbmcplugin.endOfDirectory(self.handle, True)

    def sub_categories(self, uri):
        response = self.make_response('GET', '/')
        genres = common.parseDOM(response.text, "ul", attrs={"class": "left"})

        titles = common.parseDOM(genres, "a")
        links = common.parseDOM(genres, "a", ret='href')

        item_uri = router.build_uri('index', uri=uri)
        item = xbmcgui.ListItem(f'[COLOR=FF00FFF0]{self.language(30007)}[/COLOR]')
        item.setArt({'thumb': self.icon})
        xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        for i, title in enumerate(titles):
            if not links[i].startswith(uri):
                continue
            item_uri = router.build_uri('index', uri=links[i])
            item = xbmcgui.ListItem(title)
            item.setArt({'thumb': self.icon})
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        xbmcplugin.setContent(self.handle, 'files')
        xbmcplugin.endOfDirectory(self.handle, True)

    def collections(self, page):
        uri = '/collections/'
        if page != 1:
            uri = f'/collections/page/{page}/'

        response = self.make_response('GET', uri)
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
            item = xbmcgui.ListItem("[COLOR=orange]" + self.language(30004) + "[/COLOR]")
            item.setArt({'icon': self.icon_next})
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        xbmcplugin.setContent(self.handle, 'files')
        xbmcplugin.endOfDirectory(self.handle, True)

    def index(self, uri=None, page=None, query_filter=None):
        if not page: page = 1
        page_info = self.get_page(uri, page, query_filter)
        while page and len(page_info['titles']) < 36:
            page = int(page) + 1
            p = self.get_page(uri, page, query_filter)
            page_info = dict((k, page_info.get(k, []) + p.get(k, [])) for k in page_info)
            #page_info['post_ids'] = page_info['post_ids'] + p['post_ids']
            #page_info['links'] = page_info['links'] + p['links']
            #page_info['titles'] = page_info['titles'] + p['titles']
            #page_info['div_covers'] = page_info['div_covers'] + p['div_covers']
            #page_info['country_years'] = page_info['country_years'] + p['country_years']
            if len(p['titles']) < 36: break
        #ttt = list(filter(lambda p: '\u0423\u043A\u0440\u0430\u0438\u043D\u0441\u043A\u0438\u0439' in [d.get('img_title') for d in p['translations']], page_info))
        #log(f"#########################: {ttt}")
        
        #for i, p in enumerate(page_info):
        #    log(f"#########################: {str(p)}")

        items = self.get_items(page_info)
        for item , item_uri, is_folder in items:
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, is_folder)

        if not len(page_info['titles']) < 16:
            params = {'page': 2, 'uri': uri}
            if page:
                params['page'] = int(page) + 1
            if query_filter:
                params['query_filter'] = query_filter
            item_uri = router.build_uri('index', **params)
            item = xbmcgui.ListItem("[COLOR=orange]" + self.language(30004) + "[/COLOR]")
            item.setArt({'icon': self.icon_next})
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        xbmcplugin.setContent(self.handle, 'movies')
        xbmcplugin.endOfDirectory(self.handle, True)

    def get_page(self, uri=None, page=None, query_filter=None):
        url = uri
        if not url:
            url = '/'
        if page:
            url += f'page/{page}/'
        if query_filter:
            url += f'?filter={query_filter}'

        response = self.make_response('GET', url)
        content = common.parseDOM(response.text, "div", attrs={"class": "b-content__inline_items"})
        items = common.parseDOM(content, "div", attrs={"class": "b-content__inline_item"})
        info = {}
        info['post_ids'] = common.parseDOM(content, "div", attrs={"class": "b-content__inline_item"}, ret="data-id")
        link_containers = common.parseDOM(items, "div", attrs={"class": "b-content__inline_item-link"})
        info['links'] = common.parseDOM(link_containers, "a", ret='href')
        info['titles'] = common.parseDOM(link_containers, "a")
        info['div_covers'] = common.parseDOM(items, "div", attrs={"class": "b-content__inline_item-cover"})
        info['country_years'] = common.parseDOM(link_containers, "div")
        return info

    def get_items(self, page_info):
        items = []
        for i, name in enumerate(page_info['titles']):
            #info = self.get_item_additional_info(page_info['post_ids'][i])
            info = self.get_item_full_info(page_info['links'][i])
            title = helpers.built_title(name, page_info['country_years'][i], **info)
            image = self._normalize_url(common.parseDOM(page_info['div_covers'][i], "img", ret='src')[0])
            item_uri = router.build_uri('show', uri=router.normalize_uri(page_info['links'][i]))
            year, country, genre = get_media_attributes(page_info['country_years'][i])
            item = xbmcgui.ListItem(title)
            item.setArt({'thumb': image, 'icon': image, 'banner': image, 'fanart': image})
            item.setInfo(
                type='video',
                infoLabels={
                    'title': title,
                    'genre': genre,
                    'year': year,
                    'country': country,
                    'plot': info['description'],
                    'rating': info['rating']['imdb'],
                    'duration': info.get('duration', None)
                }
            )
            is_serial = common.parseDOM(page_info['div_covers'][i], 'span', attrs={"class": "info"})
            is_folder = True
            if (self.quality != 'select') and not is_serial:
                item.setProperty('IsPlayable', 'true')
                is_folder = False
            items.append([item, item_uri, is_folder])
        return items

    def select_quality(self, streams, title, image, subtitles=None):
        for name, quality, url in streams:
            if self.quality != 'select':
                if (name == self.quality) or (int(self.quality.split('p')[0]) >= quality):
                    log(f'selected quality name: {name}')
                    self.play(url, subtitles)
                    break
            else:
                film_title = f"{title} - [COLOR=orange]{name}[/COLOR]"
                item_uri = router.build_uri('play', url=url)
                item = xbmcgui.ListItem(film_title)
                item.setArt({'icon': image})
                item.setInfo(
                    type='Video',
                    infoLabels={'title': film_title, 'overlay': xbmcgui.ICON_OVERLAY_WATCHED, 'playCount': 0}
                )
                item.setProperty('IsPlayable', 'true')
                if subtitles:
                    item.setSubtitles([subtitles])
                xbmcplugin.addDirectoryItem(self.handle, item_uri, item, False)

    def select_translator(self, content, tv_show, post_id, url, idt, action):
        try:
            div = common.parseDOM(content, 'ul', attrs={'id': 'translators-list'})[0]
        except Exception as ex:
            log(f'select_translator fault parse dom ex: {ex}')
            return tv_show, idt, None
        titles = common.parseDOM(div, 'li', ret='title')
        ids = common.parseDOM(div, 'li', ret="data-translator_id")

        # transform flag image into title suffix
        title_items = common.parseDOM(div, 'li')
        for index, title in enumerate(title_items):
            images = common.parseDOM(title, 'img', ret='title')
            for img in images:
                titles[index] += f' ({img})'

        if len(titles) > 1:
            dialog = xbmcgui.Dialog()
            index_ = dialog.select(self.language(30006), titles)
            log(f'*** language index: {index_}')
            if int(index_) < 0:
                index_ = 0
        else:
            index_ = 0
        idt = ids[index_]
        log(f'*** ids: {ids}')

        data = {
            "id": post_id,
            "translator_id": idt,
            "action": action
        }
        log(f'*** director div: {div}')
        is_director = common.parseDOM(div, 'li', ret='data-director')

        if is_director:
            data['is_director'] = is_director[index_]
            log(f'*** is_director[index_]: {is_director[index_]}')
        headers = {
            "Host": self.domain,
            "Origin": self.url,
            "Referer": url,
            "User-Agent": USER_AGENT,
            "X-Requested-With": "XMLHttpRequest"
        }
        log(f'*** request data: {data}')
        response = self.make_response('POST', "/ajax/get_cdn_series/", data=data, headers=headers).json()
        log(f'*** response: {response}')
        subtitles = None
        if action == "get_movie":
            playlist = [response["url"]]
            try:
                subtitles = response["subtitle"].split(']')[1].split(',')[0].replace(r"\/", "/")
            except Exception as ex:
                log(f'fault decode subtitles ex: {ex}')
        else:
            episodes = response["episodes"]
            playlist = common.parseDOM(episodes, "ul", attrs={"class": "b-simple_episodes__list clearfix"})
        
        log(f'*** select_translator result playlist: {playlist}')
        log(f'*** select_translator result idt: {idt}')
        log(f'*** select_translator result subtitles: {subtitles}')
        return playlist, idt, subtitles

    def show(self, uri):
        response = self.make_response('GET', uri)

        #helpers.write_to_file(response.text)

        content = common.parseDOM(response.text, "div", attrs={"class": "b-content__main"})[0]
        image = common.parseDOM(content, "img", attrs={"itemprop": "image"}, ret="src")[0]
        title = common.parseDOM(content, "h1")[0]
        post_id = common.parseDOM(response.text, "input", attrs={"id": "post_id"}, ret="value")[0]
        idt = "0"
        try:
            idt = common.parseDOM(content, "li", attrs={"class": "b-translator__item active"}, ret="data-translator_id")[0]
        except Exception as ex:
            log(f'fault parseDOM ex: {ex}')
            try:
                idt = response.text.split("sof.tv.initCDNSeriesEvents")[-1].split("{")[0]
                idt = idt.split(",")[1].strip()
            except Exception as ex:
                log(f'fault search CDN ex: {ex}')
        subtitles = None
        tv_show = common.parseDOM(response.text, "div", attrs={"id": "simple-episodes-tabs"})
        if tv_show:
            if self.translator == "select":
                tv_show, idt, subtitles = self.select_translator(content, tv_show, post_id, uri, idt, "get_episodes")
            titles = common.parseDOM(tv_show, "li")
            ids = common.parseDOM(tv_show, "li", ret='data-id')
            seasons = common.parseDOM(tv_show, "li", ret='data-season_id')
            episodes = common.parseDOM(tv_show, "li", ret='data-episode_id')

            for i, title_ in enumerate(titles):
                title_ = f"{title_} ({self.language(30005)} {seasons[i]})"
                url_episode = uri
                item_uri = router.build_uri(
                    'play_episode',
                    url=url_episode,
                    urlm=uri,
                    post_id=ids[i],
                    season_id=seasons[i],
                    episode_id=episodes[i],
                    title=title_,
                    image=image,
                    idt=idt,
                )
                item = xbmcgui.ListItem(title_)
                item.setArt({'thumb': image, 'icon': image})
                item.setInfo(type='Video', infoLabels={'title': title_})
                if self.quality != 'select':
                    item.setProperty('IsPlayable', 'true')
                xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True if self.quality == 'select' else False)
        else:
            content = [response.text]
            if self.translator == "select":
                content, idt, subtitles = self.select_translator(content[0], content, post_id, uri, idt, "get_movie")
                log(f'*** content: {content}')
                #helpers.write_to_file(content[0])
                if subtitles is None and content[0].startswith('<!'):
                    log(f'*** subtitles is None')
                    # when action == get_movie, None is returned only when some exception occurs,
                    # so we set the streams_block to default
                    streams_block = re.search(r'"streams":"([^"]+)', response.text).group(1)
                    #streams_block = content[0]
                else:
                    log(f'*** subtitles is not None')
                    # success, get selected translator streams
                    streams_block = content[0]
            else:
                # use default streams_block if translator is not in "select"
                streams_block = re.search(r'"streams":"([^"]+)', response.text).group(1)
            links = parse_streams(streams_block)
            self.select_quality(links, title, image, subtitles)

        xbmcplugin.setContent(self.handle, 'episodes')
        xbmcplugin.endOfDirectory(self.handle, True)

    def get_item_additional_info(self, post_id):
        additional = {
            'rating': {
                'site': '',
                'imdb': '',
                'kp': ''
            },
            'age_limit': '',
            'description': ''
        }
        if not self.show_description:
            return additional

        response = self.make_response('POST', '/engine/ajax/quick_content.php', data={
            "id": post_id,
            "is_touch": 1
        })

        try:
            additional['description'] = common.parseDOM(response.text, 'div', attrs={'class': 'b-content__bubble_text'})[0]
        except IndexError:
            log(f'fault parse site description post_id: {post_id}')

        try:
            additional['age_limit'] = re.search(r'<b style="color: #333;">(\d+\+)</b>', response.text).group(1)
        except AttributeError:
            log(f'fault parse age_limit post_id: "{post_id}"')

        try:
            site_rating = common.parseDOM(response.text, 'div', attrs={'class': 'b-content__bubble_rating'})[0]
            additional['rating']['site'] = common.parseDOM(site_rating, 'b')[0]
        except IndexError:
            log(f'fault parse site rating post_id: {post_id}')

        try:
            imdb_rating_block = common.parseDOM(response.text, 'span', attrs={'class': 'imdb'})[0]
            imdb_rating = common.parseDOM(imdb_rating_block, 'b')[0]
            additional['rating']['imdb'] = imdb_rating
            additional['description'] = f'IMDb: {helpers.color_rating(imdb_rating)}\n{additional["description"]}'
        except IndexError:
            log(f'fault parse imdb rating post_id: {post_id}')

        try:
            kp_rating_block = common.parseDOM(response.text, 'span', attrs={'class': 'kp'})[0]
            kp_rating = common.parseDOM(kp_rating_block, 'b')[0]
            additional['rating']['kp'] = kp_rating
            additional['description'] = f' Кинопоиск: {helpers.color_rating(kp_rating)}\n{additional["description"]}'
        except IndexError:
            log(f'fault parse kp rating post_id: {post_id}')

        return additional

    def get_item_full_info(self, link):
        full = {
            'rating': {
                'site': '',
                'imdb': '',
                'kp': ''
            },
            'age_limit': '',
            'description': '',
            'duration': 0,
            'translations': []#{'id': 0, 'title': '', 'img_title': ''}
        }
        if not self.show_description:
            return full

        response_text = self.sql.get(router.normalize_uri(link))
        if not response_text:
            response_text = self.make_response('GET', router.normalize_uri(link)).text
            self.sql.put(router.normalize_uri(link), response_text)
        #log(f"#########################: {response_text}")
        try:
            full['description'] = common.parseDOM(response_text, 'div', attrs={'class': 'b-post__description_text'})[0]
        except IndexError:
            log(f'fault parse site description link: {link}')

        try:
            full['age_limit'] = re.search(r'<span class="bold" style="color: #666;">(\d+\+)</span>', response_text).group(1)
        except AttributeError:
            log(f'fault parse age_limit link: "{link}"')

        try:
            site_rating = common.parseDOM(response_text, 'div', attrs={'class': 'b-post__rating'})[0]
            full['rating']['site'] = common.parseDOM(site_rating, 'span', attrs={'itemprop': 'average'})[0]
        except IndexError:
            log(f'fault parse site rating link: {link}')

        try:
            imdb_rating_block = common.parseDOM(response_text, 'span', attrs={'class': 'b-post__info_rates imdb'})[0]
            full['rating']['imdb'] = common.parseDOM(imdb_rating_block, 'span')[0]
        except IndexError:
            log(f'fault parse imdb rating link: {link}')

        try:
            kp_rating_block = common.parseDOM(response_text, 'span', attrs={'class': 'b-post__info_rates kp'})[0]
            full['rating']['kp'] = common.parseDOM(kp_rating_block, 'span')[0]
        except IndexError:
            log(f'fault parse kp rating link: {link}')

        
            
        try:
            translations_block = common.parseDOM(response_text, 'ul', attrs={'class': 'b-translators__list'})[0]
            title_items = common.parseDOM(translations_block, 'li')
            titles = common.parseDOM(translations_block, 'li', ret='title')
            ids = common.parseDOM(translations_block, 'li', ret="data-translator_id")
            img_title = ''
            for index, title in enumerate(title_items):
                images = common.parseDOM(title, 'img', ret='title')
                img_title = images[0] if images else ''
                full['translations'].append({'id': ids[index], 'title': titles[index], 'img_title': img_title})

            #full['translations'] = common.parseDOM(translations_block, 'li')
            #for i, val in enumerate(full['translations']):
            #    full['translations'][i] = re.sub(r'<[^)]*>', '', val).strip()
        except IndexError:
            log(f'fault parse translations: {link}')

        try:
            duration_text = common.parseDOM(response_text, 'td', attrs={'itemprop': 'duration'})[0]
            full['duration'] = int(re.findall('[0-9]+', duration_text)[0]) * 60
        except IndexError:
            log(f'fault parse duration: {link}')

        return full

    def history(self):
        words = history.get_history()
        for word in reversed(words):
            uri = router.build_uri('search', keyword=word, main=1)
            item = xbmcgui.ListItem(word)
            item.setArt({'thumb': self.icon, 'icon': self.icon})
            xbmcplugin.addDirectoryItem(self.handle, uri, item, True)
        xbmcplugin.endOfDirectory(self.handle, True)

    def get_user_input(self):
        kbd = xbmc.Keyboard()
        kbd.setDefault('')
        kbd.setHeading(self.language(30000))
        kbd.doModal()
        keyword = None

        if kbd.isConfirmed():
            if self.use_transliteration:
                keyword = transliterate.rus(kbd.getText())
            else:
                keyword = kbd.getText()

            history.add_to_history(keyword)

        return keyword

    def search(self, keyword, external):
        log(f'*** search keyword: {keyword} external: {external}')
        keyword = urllib.parse.unquote_plus(keyword) if (external is not None) else self.get_user_input()
        if not keyword:
            return self.menu()

        params = {
            "do": "search",
            "subaction": "search",
            "q": str(keyword)
        }
        response = self.make_response('GET', '/search/', params=params, cookies={"dle_user_taken": '1'})

        #helpers.show_message(response.text)

        content = common.parseDOM(response.text, "div", attrs={"class": "b-content__inline_items"})
        items = common.parseDOM(content, "div", attrs={"class": "b-content__inline_item"})
        post_ids = common.parseDOM(content, "div", attrs={"class": "b-content__inline_item"}, ret="data-id")
        link_containers = common.parseDOM(items, "div", attrs={"class": "b-content__inline_item-link"})
        links = common.parseDOM(link_containers, "a", ret='href')
        titles = common.parseDOM(link_containers, "a")
        country_years = common.parseDOM(link_containers, "div")

        for i, name in enumerate(titles):
            #info = self.get_item_additional_info(post_ids[i])
            info = self.get_item_full_info(links[i])
            title = helpers.built_title(name, country_years[i], **info)
            image = self._normalize_url(common.parseDOM(items[i], "img", ret='src')[0])
            item_uri = router.build_uri('show', uri=router.normalize_uri(links[i]))
            year, country, genre = get_media_attributes(country_years[i])
            item = xbmcgui.ListItem(title)
            item.setArt({'thumb': image, 'icon': image})
            item.setInfo(
                type='video',
                infoLabels={
                    'title': title,
                    'genre': genre,
                    'year': year,
                    'country': country,
                    'plot': info['description'],
                    'rating': info['rating']['imdb']
                }
            )
            is_serial = common.parseDOM(items[i], 'span', attrs={"class": "info"})
            is_folder = True
            if (self.quality != 'select') and not is_serial:
                item.setProperty('IsPlayable', 'true')
                is_folder = False
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, is_folder)

        xbmcplugin.setContent(self.handle, 'movies')
        xbmcplugin.endOfDirectory(self.handle, True)

    def play(self, url, subtitles=None):
        log(f'*** play url: {url} subtitles: {subtitles}')
        item = xbmcgui.ListItem(path=url)
        if subtitles:
            item.setSubtitles([subtitles])
        xbmcplugin.setResolvedUrl(self.handle, True, item)

    def play_episode(self, url, post_id, season_id, episode_id, title, image, idt):
        data = {
            "id": post_id,
            "translator_id": idt,
            "season": season_id,
            "episode": episode_id,
            "action": "get_stream"
        }
        headers = {
            "Host": self.domain,
            "Origin": self.url,
            "Referer": url,
            "User-Agent": USER_AGENT,
            "X-Requested-With": "XMLHttpRequest"
        }
        response = self.make_response('POST', "/ajax/get_cdn_series/", data=data, headers=headers).json()
        data = response["url"]

        links = parse_streams(data)
        self.select_quality(links, title, image, None)
        xbmcplugin.setContent(self.handle, 'episodes')
        xbmcplugin.endOfDirectory(self.handle, True)

    def _normalize_url(self, item):
        if not item.startswith("http"):
            item = self.url + item
        return item


plugin = HdrezkaTV()
plugin.main()
