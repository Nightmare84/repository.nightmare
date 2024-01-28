
from ast import Try
import db_helper
import json
import os
import re
import router
from settings import settings
import time
import voidboost
import web_helper
import XbmcHelpers

from helpers import log, write_to_file


common = XbmcHelpers

class video_info(object):
    def __init__(self):
        self.id = 0
        self.title = ''
        self.link = ''
        self.cover = ''
        self.rating = rating()
        self.description = ''
        self.age_limit = ''
        self.duration = 0
        self.translations = []
        self.default_translation_id = 0
        self.default_stream_url = ''
        self.year = ''
        self.country = ''
        self.genre = ''
        self.is_series = False
        self.__country_year = ''

        self.__sql = db_helper.sql(os.path.join(settings.addondir, 'hdrezka.db'))
        self.__web = web_helper.web()
    
    @property
    def formatted_title(self):
        return self.build_title()

    @property
    def has_ukrainian(self):
        return '\u0423\u043A\u0440\u0430\u0438\u043D\u0441\u043A\u0438\u0439' in [d.img_title for d in self.translations]

    @property
    def country_year(self):
        return self.__country_year

    @country_year.setter
    def country_year(self, value):
        self.__country_year = value
        items = self.__country_year.split(', ')
        if len(items) == 3:
            self.year, self.country, self.genre = items
        else:
            self.year, self.genre = items
            self.country = 'Unknown'

    def get_full_info_(self):
        response_text = self.__sql.get(router.normalize_uri(self.link))
        if not response_text:
            response_text = self.__web.make_response('GET', router.normalize_uri(self.link)).text
            self.__sql.put(router.normalize_uri(self.link), response_text)
        self.parse_full_info_page(response_text)
        self.__sql.save_video(self)

    def get_full_info(self):
        response_text = self.__web.make_response('GET', router.normalize_uri(self.link)).text
        self.parse_full_info_page(response_text)
        self.__sql.save_video(self)

    def get_full_info___(self):
        vid = self.__sql.get_video(self.id)
        #log(f'loaded video: {vid.__dict__}')
        self.translations = vid.translations
        self = vid
        #log(f'video: {self.__dict__}')

    def parse_full_info_page(self, html):
        try:
            self.id = int(common.parseDOM(html, "input", attrs={"id": "post_id"}, ret="value")[0])
        except IndexError: log(f'fault parse id')

        try:
            self.title = common.parseDOM(html, "h1")[0]
            #log(f'"######################### parsing id {self.id} {self.title}')
        except IndexError: log(f'fault parse title')
        
        try:
            self.cover = common.parseDOM(html, "img", attrs={"itemprop": "image"}, ret="src")[0]
        except IndexError: log(f'fault parse cover')

        try:
            self.description = common.parseDOM(html, 'div', attrs={'class': 'b-post__description_text'})[0]
        except IndexError: log(f'fault parse site description')

        self.is_series = True if common.parseDOM(html, "div", attrs={"id": "simple-episodes-tabs"}) else False

        try:
            self.age_limit = re.search(r'<span class="bold" style="color: #666;">(\d+\+)</span>', html).group(1)
        except AttributeError: log(f'fault parse age_limit')    
           
        self.rating = rating()

        try:
            site_rating = common.parseDOM(html, 'div', attrs={'class': 'b-post__rating'})[0]
            self.rating.site = common.parseDOM(site_rating, 'span', attrs={'itemprop': 'average'})[0]
        except IndexError: log(f'fault parse site rating')

        try:
            imdb_rating_block = common.parseDOM(html, 'span', attrs={'class': 'b-post__info_rates imdb'})[0]
            self.rating.imdb = common.parseDOM(imdb_rating_block, 'span')[0]
        except IndexError: log(f'fault parse imdb rating')

        try:
            kp_rating_block = common.parseDOM(html, 'span', attrs={'class': 'b-post__info_rates kp'})[0]
            self.rating.kp = common.parseDOM(kp_rating_block, 'span')[0]
        except IndexError: log(f'fault parse kp rating')

        try:
            try:
                self.default_translation_id = int(common.parseDOM(html, 'li', attrs={'class': 'b-translator__item active'}, ret="data-translator_id")[0])
            except Exception as ex:
                self.default_translation_id = int(html.split("sof.tv.initCDNSeriesEvents")[-1].split("{")[0].split(",")[1].strip())
        except : log(f'fault parse default translation')

        try:
            translations_block = common.parseDOM(html, 'ul', attrs={'class': 'b-translators__list'})[0]
            #log(f'"######################### translations_block: {translations_block}')
            title_items = common.parseDOM(translations_block, 'li')
            titles = common.parseDOM(translations_block, 'li', ret='title')
            ids = common.parseDOM(translations_block, 'li', ret="data-translator_id")
            img_title = ''
            for index, title in enumerate(title_items):
                images = common.parseDOM(title, 'img', ret='title')
                img_title = images[0] if images else ''
                _translation = translation()
                _translation.id = int(ids[index])
                _translation.title = titles[index]
                _translation.img_title = img_title
                self.translations.append(_translation)
                #log(f'Translation: {_translation.id}\t{_translation.title}\t{_translation.img_title}')
        except IndexError: log(f'fault parse translations')

        try:
            duration_text = common.parseDOM(html, 'td', attrs={'itemprop': 'duration'})[0]
            self.duration = int(re.findall('[0-9]+', duration_text)[0]) * 60
        except IndexError: log(f'fault parse duration')
        
        try:
            stream_url_text = html.split('"streams":"')[-1].split('"')[0]
            streams = voidboost.parse_streams(stream_url_text)
            self.default_stream_url = streams#[0][2]
        except : log(f'fault parse default_stream_url {self.title}')

    #not used
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

        response = self.web.make_response('POST', '/engine/ajax/quick_content.php', data={
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
            #additional['description'] = f'IMDb: {helpers.color_rating(imdb_rating)}\n{additional["description"]}'
        except IndexError:
            log(f'fault parse imdb rating post_id: {post_id}')

        try:
            kp_rating_block = common.parseDOM(response.text, 'span', attrs={'class': 'kp'})[0]
            kp_rating = common.parseDOM(kp_rating_block, 'b')[0]
            additional['rating']['kp'] = kp_rating
            #additional['description'] = f' Кинопоиск: {helpers.color_rating(kp_rating)}\n{additional["description"]}'
        except IndexError:
            log(f'fault parse kp rating post_id: {post_id}')

        return additional

    @staticmethod
    def get_page_videos(uri = None, page = None, query_filter = None):
        log(f'get_page_videos(uri = {uri}, page = {page}, query_filter = {query_filter})')
        startTime = time.time()
        url = uri
        if not url:
            url = '/'
        if page:
            url += f'page/{page}/'
        if query_filter:
            url += f'?filter={query_filter}'

        response = web_helper.web().make_response('GET', url)
        videos = video_info.parse_page(response.text)
        log(f'url: {url}\r\nresponse: {response.text}\r\nvideos count: {len(videos)}')
        log(f'get_page_videos() time: {int((time.time() - startTime) * 1000)}')
        return videos

    @staticmethod
    def parse_page(html):
        log(f'parse_page()')
        startTime = time.time()
        content = common.parseDOM(html, "div", attrs={"class": "b-content__inline_items"})
        items = common.parseDOM(content, "div", attrs={"class": "b-content__inline_item"})
        ids = common.parseDOM(content, "div", attrs={"class": "b-content__inline_item"}, ret = 'data-id')
        videos = []

        for i, item in enumerate(items):
            info = video_info()
            info.id = int(ids[i]);
            info.cover = common.parseDOM(item, "img", ret = 'src')[0]
            link_containers = common.parseDOM(item, "div", attrs={"class": "b-content__inline_item-link"})[0]
            info.link = common.parseDOM(link_containers, "a", ret='href')[0]
            info.title = common.parseDOM(link_containers, "a")[0]
            info.country_year = common.parseDOM(link_containers, "div")[0]
            info.is_series = True if common.parseDOM(item, 'span', attrs={"class": "info"}) else False
            videos.append(info)
        log(f'parse_page() time: {int((time.time() - startTime) * 1000)}')
        return videos

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)

    def build_title(self):
        colored_name = f'[COLOR=green]{self.title}[/COLOR]' if self.has_ukrainian else self.title
        #colored_name = f'[COLOR=red  ]{self.title}[/COLOR]' if self.default_stream_url == '' and len(self.translations) == 0 else colored_name
        colored_rating = self.color_rating(self.rating.imdb)
        colored_info = f'[COLOR=55FFFFFF]{self.age_limit} ({self.country_year})[/COLOR]'
        return f'{colored_name} {colored_rating} {colored_info}'

    def color_rating(self, rating):
        if not rating:
            return ''
        rating = float(rating)
        if 0 <= rating < 5:
            return '[COLOR=red][%s][/COLOR]' % rating
        elif 5 <= rating < 7:
            return '[COLOR=yellow][%s][/COLOR]' % rating
        elif rating >= 7:
            return '[COLOR=green][%s][/COLOR]' % rating

"""
    @staticmethod
    def fromJson(json_str):
        res = video_info()
        dct = json.loads(json_str)
        res.rating.site = dct['rating']['site']
        res.rating.imdb = dct['rating']['imdb']
        res.rating.kp = dct['rating']['kp']
        res.description = dct['description']
        res.age_limit = dct['age_limit']
        res.duration = dct['duration']
        res.translations = []
        for tr in dct['translations']:
            dct_translation = translation()
            dct_translation.id = tr['id']
            dct_translation.title = tr['title']
            dct_translation.img_title = tr['img_title']
            res.translations.append(dct_translation)
        return res

    def asDictionary(self):
        res = {
            'id': 0,
            'title': '',
            'link': '',
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
        res['description'] = self.description
        res['age_limit'] = self.age_limit
        res['rating']['site'] = self.rating.site
        res['rating']['imdb'] = self.rating.imdb
        res['rating']['kp'] = self.rating.kp
        for translation in self.translations:
            res['translations'].append({'id': translation.id, 'title': translation.title, 'img_title': translation.img_title})
        res['duration'] = self.duration

        return res
"""

class rating(object):
    def __init__(self):
        self.site = 0
        self.imdb = 0
        self.kp = 0

class translation(object):
    def __init__(self, *args):
        if len(args) == 3:
            self.id = args[0]
            self.title = args[1]
            self.img_title = args[2]
        else:
            self.id = 0
            self.title = ''
            self.img_title = None

    @property
    def formatted_title(self):
        if not self.img_title: return self.title
        return f'{self.title} ({self.img_title})'

class episode(object):
    def __init__(self):
        self.season_number = 0
        self.number = 0
        self.title = ''

    @property
    def formatted_title(self):
        return f"{self.title} ({settings.language(30005)} {self.season_number})"
    