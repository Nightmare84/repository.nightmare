# Copyright (C) 2023, Roman Miroshnychenko aka Roman V.M.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""In-memory storage"""

import json

import xbmcgui


class MemStorage:
    ADDON_ID = "plugin.video.uakino.club"
    CACHE_KEY = f"__{ADDON_ID}_cache__"

    """
    Stores a JSON-serializable Python object in a shared memory within Kodi

    It can be used to exchange data between different Python scripts running inside Kodi.
    """
    def __init__(self, window_id=10000):
        self._window = xbmcgui.Window(window_id)

    def __getitem__(self, key):
        try:
            json_string = self._window.getProperty(f"{self.CACHE_KEY}{key}")
            return json.loads(json_string)
        except ValueError:
            #raise KeyError(f"Item '{key}' cannot be retrieved from MemStorage") from exc
            return None

    def __setitem__(self, key, value):
        try:
            json_string = json.dumps(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Item {key}:{value} cannot be stored in MemStorage") from exc
        self._window.setProperty(f"{self.CACHE_KEY}{key}", json_string)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default
