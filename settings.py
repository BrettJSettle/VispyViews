import pickle
import os

class Settings():
	def __init__(self, empty=False):
		if not empty:
			self.reload()

	def __setattr__(self, k, v):
		self.__dict__[k] = v

	def save(self):
		with open('settings.p', 'wb') as outf:
			p = pickle.dump(self.__dict__, outf)

	def reload(self):
		try:
			if os.path.isfile('settings.p'):
				with open('settings.p', 'rb') as inf:
					self.__dict__.update(pickle.load(inf))
		except:
			print('Settings file is corrupted. Removing...')
			os.path.remove('settings.p')

settings = Settings()