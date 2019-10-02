# -*- coding: utf-8 -*-
import threading
import sys
import logging

from time import sleep
from loader import Loader
from db_manager import DatabaseManager
from classes.ibot import *
from classes.vk_bot import *

TOKEN = 'a714dbee700ea3d57d80a4715e89bed2a2e4d084822483f096bb742f802d81819c59720d33d8ad4bf4379'
ID = '186543615'
VERSION = 5.101

if len(sys.argv) > 3:
	logging.basicConfig(filename = sys.argv[3], level = logging.DEBUG)

def send_notification(bot, settings_wrapper, manager_id, tasks, selection_function, *selection_function_args):
	'''Отправляет менеджеру уведомление о задаче, на которую указала функция выбора.'''
	selected_task = selection_function(tasks, selection_function_args)
	if selected_task == None:
		return
	notification = f'''Кол-во задач: {len(tasks)} штук
Заказ от {selected_task['name']}
Сумма: {selected_task['price']} ₽
Описание: {selected_task['text']}
'''
	bot.send(int(manager_id), notification, settings_wrapper)
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

def send_notifications(bot, settings_wrapper, managers, unanswered_requests, prev_unanswered_requests_count):
	'''Отправляет уведомления манагерам. Вернет, было ли послано хоть одно уведомление.'''
	result = False
	for manager_id in managers:
		send = notification_should_be_sent(unanswered_requests, len(unanswered_requests), prev_unanswered_requests_count)
		if send:
			send_notification(bot, settings_wrapper, manager_id, unanswered_requests, get_latest_task)
		result = result or send
	return result

def notification_should_be_sent(tasks, *condition_function_args):
	'''Определяет, должно ли быть отправлено уведомление.'''
	unanswered_requests_count = condition_function_args[0]
	prev_unanswered_requests_count = condition_function_args[1]
	return (unanswered_requests_count > 0 and prev_unanswered_requests_count == 0) or (unanswered_requests_count - prev_unanswered_requests_count > 30) or (unanswered_requests_count - prev_unanswered_requests_count < 0)

class Program:

	def __init__(self):
		self.running = False
		self.prev_unanswered_requests_count = 0
		
	def mainloop(self, bot, dbm, settings_wrapper, managers_answers_wrapper, l):
		self.running = True
		while self.running:
			managers_answers_wrapper.lock.acquire()
			logging.debug('Ответы менеджеров: ' + str(managers_answers_wrapper.payload))
			dbm.answer(managers_answers_wrapper.payload)
			managers_answers_wrapper.payload = {1 : [], 2 : [], 3 : []}
			managers_answers_wrapper.lock.release()
			logging.debug('Ответы зваписаны.')
			
			settings_wrapper.lock.acquire()
			l.save()
			settings_wrapper.lock.release()
			logging.debug('Настройки сохранены.')
			
			unanswered_requests = dbm.get_unanswered_requests()
			send = send_notifications(bot, settings_wrapper, settings_wrapper.payload['managers'].keys(), unanswered_requests, self.prev_unanswered_requests_count)
			logging.debug('Сейча - ' + str(unanswered_requests) + '. Тогда - ' + str(self.prev_unanswered_requests_count) + '. send = ' + str(send))
			if send:
				self.prev_unanswered_requests_count = len(unanswered_requests)
			logging.debug('Уведомления посланы.')
			
			sleep(5)
	
	def stop(self):
		self.running = False

if __name__ == '__main__':
	
	#settings = None
	#settings_lock = threading.Lock()
	settings_wrapper = Wrapper(None)
	
	managers_answers = {1 : [], 2 : [], 3 : []}
	#managers_answers_lock = threading.Lock()
	managers_answers_wrapper = Wrapper(managers_answers)
	
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
	main_thread = threading.Thread(target = prog.mainloop, args = (bot, dbm, settings_wrapper, managers_answers_wrapper, l), daemon = True)
	main_thread.start()
	
	input()
	bot.stop()
	prog.stop()