# -*- coding: utf-8 -*-
import vk
import requests
import threading
import sys
import logging

from time import sleep
from random import randint
from loader import Loader
from db_manager import DatabaseManager

TOKEN = 'a714dbee700ea3d57d80a4715e89bed2a2e4d084822483f096bb742f802d81819c59720d33d8ad4bf4379'
ID = '186543615'
VERSION = 5.101

class Wrapper:
	def __init__(self, payload):
		self.payload = payload
		self.lock = threading.Lock()

class VK_Bot:
	
	MIN = -9223372036854775808
	MAX = 9223372036854775807
	
	notification_keyboard = '''{
	"one_time" : true,
	"buttons" : [
	  [
	    {
				"action":{
					"type": "text",
					"label": "Decline",
					"payload": ""
				},
				"color": "negative"
			},
			{
				"action":{
					"type": "text",
					"label": "Decline Old",
					"payload": ""
				},
				"color": "negative"
			}
    ]
  ]
}'''
	error_keyboard = '''{
	"one_time" : true,
	"buttons" : [
		[
			{
				"action":{
					"type": "text",
					"label": "Ввести отклик повторно.",
					"payload": ""
				},
				"color": "positive"
			}
		]
	]
}'''
	
	def __init__(self, token, group_id, version, settings_wrapper, managers_answers_wrapper):
		self.version = version
		self.session = vk.Session(access_token = token)
		self.vk_api = vk.API(self.session)
		self.data = self.vk_api.groups.getLongPollServer(group_id = group_id, v = version)
		self.is_polling = False
		self.settings_wrapper = settings_wrapper
		self.managers_answers_wrapper = managers_answers_wrapper
	
	def polling(self):
		self.is_polling = True
		while self.is_polling:
			try:
				response = requests.get('{server}?act=a_check&key={key}&ts={ts}&wait=20'.format(server=self.data['server'], key=self.data['key'], ts=self.data['ts'])).json()
				updates = response['updates']
				if updates:
					for element in updates:
						if element['type'] == 'message_new':
							self.process_message(element['object'])
				self.data['ts'] = response['ts']
			except requests.exceptions.Timeout:
				logging.error("Timeout occurred")
	
	def stop(self):
		self.is_polling = False
	
	def send_message(self, user_id, msg, keyboard = None):
		try:
			if not keyboard:
				self.vk_api.messages.send(user_id = user_id, random_id = randint(VK_Bot.MIN, VK_Bot.MAX), peer_id = user_id, message = msg, v = self.version)
			else:
				self.vk_api.messages.send(user_id = user_id, random_id = randint(VK_Bot.MIN, VK_Bot.MAX), peer_id = user_id, message = msg, keyboard = keyboard, v = self.version)
		except requests.exceptions.Timeout:
			logging.error("Timeout occurred")
	
	def process_message(self, message):
		if self.settings_wrapper.payload == None:
			self.send_message(message['user_id'], message['body'])
			return
		user_id = str(message['user_id'])
		if not user_id in self.settings_wrapper.payload['managers'].keys():
			if message['body'] in self.settings_wrapper.payload['new_managers']:
				self.send_message(message['user_id'], 'Вы успешно зарегистрировались.')
				self.settings_wrapper.lock.acquire()
				self.settings_wrapper.payload['managers'][user_id] = self.settings_wrapper.payload['new_managers'].pop(message['body'], None)
				#type = None
				self.settings_wrapper.payload['managers'][user_id]['latest_msg_type'] = None
				self.settings_wrapper.lock.release()
			else:
				self.send_message(message['user_id'], 'Пароль неверный.')
		else:
			if self.settings_wrapper.payload['managers'][user_id]['latest_msg_type'] == 'notification':
				if message['body'] == 'Decline':
					self.managers_answers_wrapper.lock.acquire()
					self.managers_answers_wrapper.payload[2].append({'task_id' : self.settings_wrapper.payload['managers'][user_id]['latest_task'],})
					self.managers_answers_wrapper.lock.release()
					#type = None
					self.settings_wrapper.lock.acquire()
					self.settings_wrapper.payload['managers'][user_id]['latest_msg_type'] = None
					self.settings_wrapper.lock.release()
				elif message['body'] == 'Decline Old':
					self.send_message(message['user_id'], 'Вы уверены, что хотите удалить старые заявки? (Да/Нет)')
					#type = confirmation
					self.settings_wrapper.lock.acquire()
					self.settings_wrapper.payload['managers'][user_id]['latest_msg_type'] = 'confirmation'
					self.settings_wrapper.lock.release()
				else:
					err, text, price, duration = parse_manager_answer(message['body'])
					if err != None:
						msg = f'Ошибка ввода! {err}'
						self.send_message(message['user_id'], msg, keyboard = VK_Bot.error_keyboard)
						#type = error
						self.settings_wrapper.lock.acquire()
						self.settings_wrapper.payload['managers'][user_id]['latest_msg_type'] = 'error'
						self.settings_wrapper.lock.release()
					else:
						self.managers_answers_wrapper.lock.acquire()
						self.managers_answers_wrapper.payload[1].append({'task_id' : self.settings_wrapper.payload['managers'][user_id]['latest_task'], 'text' : text, 'price' : price, 'duration' : duration})
						self.managers_answers_wrapper.lock.release()
						#type = None
						self.settings_wrapper.lock.acquire()
						self.settings_wrapper.payload['managers'][user_id]['latest_msg_type'] = None
						self.settings_wrapper.lock.release()
			elif self.settings_wrapper.payload['managers'][user_id]['latest_msg_type'] == 'confirmation':
				if message['body'] == 'Да':
					self.managers_answers_wrapper.lock.acquire()
					self.managers_answers_wrapper.payload[3].append({'task_id' : self.settings_wrapper.payload['managers'][user_id]['latest_task'],})
					self.managers_answers_wrapper.lock.release()
					#type = None
					self.settings_wrapper.lock.acquire()
					self.settings_wrapper.payload['managers'][user_id]['latest_msg_type'] = None
					self.settings_wrapper.lock.release()
				else:
					#type = notification
					self.settings_wrapper.lock.acquire()
					self.settings_wrapper.payload['managers'][user_id]['latest_msg_type'] = 'notification'
					self.settings_wrapper.lock.release()
			elif self.settings_wrapper.payload['managers'][user_id]['latest_msg_type'] == 'error':
				send(user_id, self.settings_wrapper.payload['managers'][user_id]['latest_notification'], self.settings_wrapper)
				#type = notification

def send(manager_id, notification, settings_wrapper):
	'''Отправляет уведомление.'''
	bot.send_message(int(manager_id), notification, keyboard = VK_Bot.notification_keyboard)
	#type = notification
	settings_wrapper.lock.acquire()
	settings_wrapper.payload['managers'][str(manager_id)]['latest_msg_type'] = 'notification'
	settings_wrapper.lock.release()

def send_notification(settings_wrapper, manager_id, tasks, selection_function, *selection_function_args):
	'''Отправляет менеджеру уведомление о задаче, на которую указала функция выбора.'''
	selected_task = selection_function(tasks, selection_function_args)
	if selected_task == None:
		return
	notification = f'''Кол-во задач: {len(tasks)} штук
Заказ от {selected_task['name']}
Сумма: {selected_task['price']} ₽
Описание: {selected_task['text']}
'''
	send(int(manager_id), notification, settings_wrapper)
	settings_wrapper.lock.acquire()
	settings_wrapper.payload['managers'][manager_id]['latest_task'] = selected_task['id']
	settings_wrapper.payload['managers'][manager_id]['latest_notification'] = notification
	settings_wrapper.lock.release()

def get_latest_task(tasks, *selection_function_args):
	'''Возвращает последнюю из известных задач.'''
	result = None
	for task in tasks:
		if result == None or result['dt_created'] > task['dt_created']:
			result = task
	return result

def send_notifications(settings_wrapper, managers, unanswered_requests):
	'''Отправляет уведомления манагерам.'''
	for manager_id in managers:
		if notification_should_be_sent(unanswered_requests, len(unanswered_requests)):
			send_notification(settings_wrapper, manager_id, unanswered_requests, get_latest_task)

def notification_should_be_sent(tasks, condition_function = None, *condition_function_args):
	'''ОпределяетЮ должно ли быть отправлено уведомление.'''
	return True
	unanswered_requests_count = condition_function_args[0]
	new_count = len(tasks)
	return (new_count > 0 and unanswered_requests_count == 0) or (new_count - unanswered_requests_count > 30)

def parse_manager_answer(text):
	'''Возвращает ошибку в отклике менеджера, текст ответа, цену и продолжительность.'''
	splitted = text.split('\n')
	
	empty = []
	for s in splitted: 
		l = len(s)
		if l == s.count(' ') or l == 0:
			empty.append(s)
	for s in empty:
		splitted.remove(s)
	del empty
	
	if len(splitted) < 3:
		return ('Не введены текст отклика, сумма или срок.', None, None, None)
	
	price = None
	duration = None
	try:
		price = int(splitted[-2])
		duration = int(splitted[-1])
	except ValueError:
		return ('Неверный ввод суммы/срока.', None, None, None)
	
	if price < 5000:
		return ('Слишком маленькая сумма для отклика.', None, None, None)
	
	if duration > 366:
		return ('Срок не может быть больше года.', None, None, None)
	elif duration < 3:
		return ('Срок не может быть менее 3 дней.', None, None, None)
	
	return (None, text, price, duration)

class Program:

	def __init__(self):
		self.running = False
		
	def mainloop(self, dbm, settings_wrapper, managers_answers_wrapper, l):
		self.running = True
		while self.running:
			unanswered_requests = dbm.get_unanswered_requests()
			send_notifications(settings_wrapper, settings_wrapper.payload['managers'].keys(), unanswered_requests)
			unanswered_requests_count = len(unanswered_requests)
			logging.debug('Уведомления посланы.')
			sleep(60) #ждем, пока манеджеры пообщаются с ботом
			
			managers_answers_wrapper.lock.acquire()
			dbm.answer(managers_answers_wrapper.payload)
			managers_answers_wrapper.payload = {1 : [], 2 : [], 3 : []}
			managers_answers_wrapper.lock.release()
			logging.debug('Ответы зваписаны.')
			
			settings_wrapper.lock.acquire()
			l.save()
			settings_wrapper.lock.release()
			logging.debug('Настройки сохранены.')
			
			sleep(60)
	
	def stop(self):
		self.running = False

if __name__ == '__main__':
	
	#settings = None
	#settings_lock = threading.Lock()
	settings_wrapper = Wrapper(None)
	
	managers_answers = {1 : [], 2 : [], 3 : []}
	#managers_answers_lock = threading.Lock()
	managers_answers_wrapper = Wrapper(managers_answers)
	
	unanswered_requests_count = 0
	
	bot = VK_Bot(TOKEN, ID, VERSION, settings_wrapper, managers_answers_wrapper)
	
	l = Loader(sys.argv[1])
	l.dump_file_name = sys.argv[2]
	#settings = l.settings
	#settings_wrapper.payload = settings
	settings_wrapper.payload = l.settings
	logging.debug('Загружены настройки.')
	
	dbm = DatabaseManager(settings_wrapper.payload['connection_settings']['host'], settings_wrapper.payload['connection_settings']['username'], settings_wrapper.payload['connection_settings']['passwd'], settings_wrapper.payload['connection_settings']['database'])
	
	bot_thread = threading.Thread(target = bot.polling, daemon = True)
	bot_thread.start()
	logging.debug('Бот включен.')
	
	#dbm, settings_wrapper, managers_answers_wrapper, l
	prog = Program()
	main_thread = threading.Thread(target = prog.mainloop, args = (dbm, settings_wrapper, managers_answers_wrapper, l), daemon = True)
	main_thread.start()
	
	input()
	bot.stop()
	prog.stop()