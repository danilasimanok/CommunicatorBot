import json

class Loader:
	'''Работает с настройками программы.'''
	
	def __init__(self, settings_file_name):
		self.settings = None
		self.dump_file_name = None
		if settings_file_name == None:
			return
		settings = open(settings_file_name, 'r')
		self.settings = json.load(settings)
		settings.close()
	
	def create_settings(self, new_managers, managers, connection_settings):
		if self.settings != None:
			return
		self.settings = {'new_managers' : new_managers, 'managers' : managers, 'connection_settings' : connection_settings}
	
	def save(self):
		if self.dump_file_name == None or self.settings == None:
			return
		dump_file = open(self.dump_file_name, 'w')
		json.dump(self.settings, dump_file)
		dump_file.close()

if __name__ == '__main__':
	
	loader = Loader('settings.json')
	
	nmanager1 = {'name' : 'Петя',}
	nmanager2 = {'name' : 'Борис',}
	nmanager3 = {'name' : 'Вова',}
	new_managers = {'pw1' : nmanager1, 'pw2' : nmanager2, 'pw3' : nmanager3,}
	
	manager = {'name' : 'Василий',}
	managers = {1488228 : manager,}
	
	connection_settings = {'host' : 'somechars', 'username' : 'somechars', 'passwd' : 'somechars', 'database' : 'somechars'}
	
	loader.create_settings(new_managers, managers, connection_settings)
	loader.dump_file_name = 'settings.json'
	
	print(loader.settings)