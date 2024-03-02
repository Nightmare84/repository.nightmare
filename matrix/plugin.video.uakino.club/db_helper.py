# from gettext import translation
from helpers import log

import re
import video_info
import sqlite3


class Sql:
    def __init__(self, path_to_file):
        self.__path_to_file = path_to_file
        self.__connection = sqlite3.connect(path_to_file)
        self.create_table_requests()

    def create_table_requests(self):
        if self.table_exists("requests"):
            return
        cur = self.__connection.cursor()
        cur.execute("CREATE TABLE requests (request, response)")
        cur.execute(
            """CREATE TABLE "video_info" (
    "id"    INTEGER NOT NULL UNIQUE,
    "title"    TEXT NOT NULL,
    "link"    TEXT NOT NULL UNIQUE,
    "cover"    TEXT,
    "rating"    INTEGER NOT NULL DEFAULT 0,
    "description"    TEXT,
    "age_limit"    TEXT,
    "duration"    INTEGER NOT NULL DEFAULT 0,
    "default_translation_id"	INTEGER NOT NULL DEFAULT 0,
    "year"    TEXT,
    "country"    TEXT,
    "genre"    TEXT,
    "is_series"    TEXT,
    PRIMARY KEY("id")
)"""
        )
        cur.execute(
            """CREATE TABLE "translators" (
    "id"    INTEGER NOT NULL UNIQUE,
    "title"    TEXT,
    "img_title"    INTEGER,
    PRIMARY KEY("id")
)"""
        )
        cur.execute(
            """CREATE TABLE "video_translators" (
    "video_id"    INTEGER NOT NULL,
    "translator_id"    INTEGER NOT NULL,
    UNIQUE("video_id","translator_id")
)"""
        )
        self.__connection.commit()
        cur.close()
        # self.__connection.close()

    def table_exists(self, table_name):
        cur = self.__connection.cursor()
        res = cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
        response = res.fetchone()
        exists = True if response else False
        cur.close
        # self.__connection.close
        return exists

    def put(self, request, response):
        data = [(request, response)]
        cur = self.__connection.cursor()
        cur.executemany("INSERT INTO requests VALUES(?, ?)", data)
        self.__connection.commit()
        cur.close()
        # self.__connection.close()

    def get(self, request):
        cur = self.__connection.cursor()
        res = cur.execute(f"SELECT response FROM requests WHERE request = '{request}'")
        row = res.fetchone()
        response = row[0] if row else None
        cur.close
        # self.__connection.close()
        return response

    def save_video(self, video):
        cur = self.__connection.cursor()
        ids = ",".join([str(translation.id) for translation in video.translations])
        # log(f'ids: {ids}')
        res = cur.execute(f"SELECT id FROM translators WHERE id in ({ids})").fetchall()
        saved_ids = [t[0] for t in res]
        # log(f'saved_ids: {saved_ids}')
        missed_translations = [translation for translation in video.translations if translation.id not in saved_ids]
        # log(f'missed_translations: {missed_translations}')
        if len(missed_translations) > 0:
            cur.executemany("INSERT OR IGNORE INTO translators VALUES (?,?,?)", [[t.id, t.title, t.img_title] for t in video.translations])
        # log([video.id, video.title, video.link, video.cover, video.description, video.age_limit, video.duration, video.default_translation_id, video.default_stream_url, video.year, video.country, video.genre, video.is_series])
        cur.execute("INSERT OR IGNORE INTO video_info VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", [video.id, video.title, video.link, video.cover, video.description, video.age_limit, video.duration, video.default_translation_id, str(video.default_stream_url), video.year, video.country, video.genre, video.is_series])
        cur.executemany("INSERT OR IGNORE INTO video_translators VALUES (?,?)", [[video.id, t.id] for t in video.translations])
        cur.execute("INSERT OR IGNORE INTO video_ratings VALUES (?,?,?,?)", [video.id, video.rating.site, video.rating.imdb, video.rating.kp])
        self.__connection.commit()

    def get_video(self, video_id):
        video = video_info.video_info()
        cur = self.__connection.cursor()
        res = cur.execute(
            f"""    select t.id, t.title, t.img_title
                                from video_translators vt
                                left join translators t on t.id = vt.translator_id
                                where vt.video_id = {video_id}"""
        )
        video.translations = [video_info.translation(row[0], row[1], row[2]) for row in res]

        res = cur.execute(
            f"""    select vi.id, vi.title, vi.link, vi.cover, vi.rating, vi.description, vi.age_limit, vi.duration, vi.default_translation_id, vi.default_stream_url, vi.year, vi.country, vi.genre, vi.is_series
                    from video_info vi
                    where vi.id = {video_id}"""
        )
        for row in res:
            video.id = row[0]
            video.title = row[1]
            video.link = row[2]
            video.cover = row[3]
            video.rating = row[4]
            video.description = row[5]
            video.age_limit = row[6]
            video.duration = row[7]
            video.default_translation_id = row[8]
            video.default_stream_url = list(map(eval, re.findall(r"(\([\s\S]+?\))", row[9])))
            video.year = row[10]
            video.country = row[11]
            video.genre = row[12]
            video.is_series = row[13] != "0"
            video.country_year = f"{video.year}, {video.country}, {video.genre}"
        self.__connection.commit()
        cur.close
        return video if video.id > 0 else None
