import xbmc
import xbmcaddon
import sqlite3

from helpers import log

class sql:
	def __init__(self, path_to_file):
		self.__path_to_file__ = path_to_file
		self.__table_name__ = 'requests'
		self.try_create_table(self.__table_name__)

	def try_create_table(self, table_name):
		if not self.table_exists(table_name):
			self.create_table(table_name)

	def create_table(self, table_name):
		con = sqlite3.connect(self.__path_to_file__)
		cur = con.cursor()
		cur.execute(f"CREATE TABLE {table_name}(request, response)")
		con.commit()
		cur.close()
		con.close()

	def table_exists(self, table_name):
		con = sqlite3.connect(self.__path_to_file__)
		cur = con.cursor()
		res = cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
		response = res.fetchone()
		exists = True if response else False
		cur.close
		con.close
		return exists

	def put(self, request, response):
		data = [(request, response)]
		con = sqlite3.connect(self.__path_to_file__)
		cur = con.cursor()
		cur.executemany(f"INSERT INTO {self.__table_name__} VALUES(?, ?)", data)
		con.commit()
		cur.close()
		con.close()


	def get(self, request):
		con = sqlite3.connect(self.__path_to_file__)
		cur = con.cursor()
		res = cur.execute(f"SELECT response FROM {self.__table_name__} WHERE request = '{request}'")
		row = res.fetchone()
		response = row[0] if row else None
		cur.close
		con.close
		return response
