# -*- coding: utf-8 -*-
import threading

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

class Wrapper:
	'''Класс-оболочка для блокировки данных при изменении их потоками.'''
	def __init__(self, payload):
		self.payload = payload
		self.lock = threading.Lock()

class IBot:
	
	def __init__(self, token, settings_wrapper, managers_answers_wrapper):
		#Пока что токены были везде нужны: с их помощью получаем доступ к api
		self.token = token
		#wrapper-ы нужны для потокобезопасного изменения настроек и ответов менеджеров
		self.settings_wrapper = settings_wrapper
		self.managers_answers_wrapper = managers_answers_wrapper
	
	def polling(self):
		'''После вызова этой функции бот начинает слушать входящие сообщения.'''
		pass
		
	def stop(self):
		'''Останавливает бота.'''
		pass
	
	def send_message(self, user_id, msg, keyboard = None):
		'''Посылает сообщение.'''
		pass
	
	def process_message(self, message):
		'''Работает с входящими сообщениями.'''
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
				self.send(user_id, self.settings_wrapper.payload['managers'][user_id]['latest_notification'], self.settings_wrapper)
				#type = notification
		
		def send(self, manager_id, notification, settings_wrapper):
			'''Отправляет уведомление.'''
			pass