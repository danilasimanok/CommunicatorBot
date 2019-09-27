import mysql.connector
from datetime import datetime
from datetime import timedelta

class DatabaseManager:
	'''Общается с базой данных (далее - БД)'''
	
	def __init__(self, host, username, password, database):
		self.database = mysql.connector.connect(host = host, username = username, passwd = password, database = database)
	
	def get_unanswered_requests(self):
		'''Возвращает список необработанных заявок.'''
		c = self.database.cursor()
		c.execute('SELECT task_id, task_dt_created, task_dt_added, exchange_id, task_category_id, task_link, task_text, task_price, task_name, task_status, task_dt_done FROM tasks WHERE task_status = 0')
		result = []
		task_fields = ['id', 'dt_created', 'dt_added', 'exchange_id', 'category_id', 'link', 'text', 'price', 'name', 'status', 'dt_done']
		for task in c.fetchall():
			result.append(dict(zip(task_fields, task)))
		c.close()
		return result
	
	#Возможно, если один откажется, а второй не срезу согласится, возникнет проблема.
	def answer(self, managers_answer):
		'''Изменяет записи в БД согласно ответам манагеров.'''
		c = self.database.cursor()
		
		insert_sql = 'INSERT INTO responses (response_dt_creation, task_id, response_text, response_price, response_duration) VALUES (%s, %s, %s, %s, %s)'
		update_sql = 'UPDATE tasks SET task_status = %s, task_dt_done = %s WHERE task_id = %s'
		
		accepted = []
		if 1 in managers_answer.keys():
			accepted = managers_answer[1]
		declined = []
		if 2 in managers_answer.keys():
			declined = managers_answer[2]
		outdated = []
		if 3 in managers_answer.keys():
			outdated = managers_answer[3]
		
		for answer in accepted:
			t = (1, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), answer['task_id'])
			c.execute(update_sql, t)
			t = (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), answer['task_id'], answer['text'], answer['price'], answer['duration'])
			c.execute(insert_sql, t)
		self.database.commit()
		
		for answer in declined:
			t = (2, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), answer['task_id'])
			c.execute(update_sql, t)
		self.database.commit()
		
		#Возможно, здесь будет в последствии более сложная логика
		if len(outdated) > 0:
			sql = 'UPDATE tasks SET task_status = 3, task_dt_done = %s WHERE task_status = 0 AND task_dt_created < %s'
			now = datetime.now()
			time = (now - timedelta(hours = 6)).strftime('%Y-%m-%d %H:%M:%S')
			c.execute(sql, (now.strftime('%Y-%m-%d %H:%M:%S'), time))
		self.database.commit()
		c.close()
	
	def __del__(self):
		self.database.close()

if __name__ == '__main__':
	dbm = DatabaseManager('somechars', 'somechars', 'somechars', 'somechars')
	
	accepted = [{'task_id' : 10, 'text' : 'И это тоже сделаем.', 'price' : 800, 'duration' : 12}]
	declined = [{'task_id' : 11}]
	managers_answer = {1:accepted, 2:declined}
	
	dbm.answer(managers_answer)
	
	outdated = [{'task_id' : 9},]
	managers_answer = {3: outdated}
	
	dbm.answer(managers_answer)
	
	c = dbm.database.cursor()
	c.execute('SELECT * FROM tasks')
	for x in c.fetchall():
		print(x)
	
	print('resp')
	
	c.execute('SELECT * FROM responses')
	for x in c.fetchall():
		print(x)
	
	print('----------')