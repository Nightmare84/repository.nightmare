import os
import xbmc
import xbmcgui


def get_media_attributes(source):
    items = source.split(',')
    if len(items) == 3:
        year, country, genre = items
    else:
        year, genre = items
        country = 'Unknown'
    return year, country, genre


def color_rating(rating):
    if not rating:
        return ''
    rating = float(rating)
    if 0 <= rating < 5:
        return '[COLOR=red][%s][/COLOR]' % rating
    elif 5 <= rating < 7:
        return '[COLOR=yellow][%s][/COLOR]' % rating
    elif rating >= 7:
        return '[COLOR=green][%s][/COLOR]' % rating


def built_title(name, country_years, **kwargs):
    has_ukrainian = '\u0423\u043A\u0440\u0430\u0438\u043D\u0441\u043A\u0438\u0439' in [d.get('img_title') for d in kwargs['translations']]
    log(f"#########################: {[d.get('img_title') for d in kwargs['translations']]}")
    colored_name = f'[COLOR=green]{name}[/COLOR]' if has_ukrainian else name
    colored_rating = color_rating(kwargs["rating"]["imdb"])
    colored_info = f'[COLOR=55FFFFFF]{kwargs["age_limit"]} ({country_years})[/COLOR]'
    return f'{colored_name} {colored_rating} {colored_info}'


def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f'hdrezka: {msg}', level)

def show_message(message):
    dialog = xbmcgui.Dialog()
    ok = dialog.ok('HdrezkaTV', message)

def write_to_file(text):
    with open(os.path.expanduser('~/HDrezka_tmp.txt'), 'w', encoding = "utf-8") as file:
        file.write(str(text))
