from ast import Try
#import db_helper
import json
import os
import re
#import router
#from settings import settings
import time
#import voidboost
#import web_helper
#import XbmcHelpers

from helpers import log, write_to_file


#common = XbmcHelpers

class VideoInfo:
    def __init__(self):
        self.id = 0
        self.title = ""
        self.link = ""
        self.cover = ""
        self.rating = 0
        self.description = ""
        self.age_limit = ""
        self.duration = 0
        self.translations = []
        self.default_translation_id = 0
        self.default_stream_url = ""
        self.year = ""
        self.country = ""
        self.genre = ""
        self.is_series = False
        self.__country_year = ""

        #self.__sql = db_helper.sql(os.path.join(settings.addondir, "uakino.db"))
        #self.__web = web_helper.web()

    @property
    def formatted_title(self):
        return self.build_title()

    def build_title(self):
        #colored_name = f"[COLOR=green]{self.title}[/COLOR]" if self.has_ukrainian else self.title
        colored_name = self.title
        colored_rating = self.color_rating(self.rating)
        #colored_info = f"[COLOR=55FFFFFF]{self.age_limit} ({self.country_year})[/COLOR]"
        colored_info = f"[COLOR=55FFFFFF] ({self.year})[/COLOR]"
        return f"{colored_name} {colored_rating} {colored_info}"

    def color_rating(self, rating):
        if not rating:
            return ""
        rating = float(rating)
        if 0 <= rating < 5:
            return f"[COLOR=red][{rating}][/COLOR]"
        elif 5 <= rating < 7:
            return f"[COLOR=yellow][{rating}][/COLOR]"
        elif rating >= 7:
            return f"[COLOR=green][{rating}][/COLOR]"
        return f"[{rating}]"
