# -*- coding: utf-8 -*-
import vk
import requests
import logging

from .ibot import *
from random import randint

class VK_Bot(IBot):
	
	#Минимальное и максимальное значения для long int. Нужны для выбора случайного числа при отправке сообщений через vkapi
	MIN = -9223372036854775808
	MAX = 9223372036854775807
	
	#JSON-строки, представляющие клавиатуры.
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
		IBot.__init__(self, token, settings_wrapper, managers_answers_wrapper)
		#Версия vkapi нужна при каждом к нему обращении. 
		self.version = version
		#Эти поля нужны для создания и обращения к vkapi соответственно.
		self.session = vk.Session(access_token = self.token)
		self.vk_api = vk.API(self.session)
		#data содержит ответы от LongPoll-сервера
		self.data = self.vk_api.groups.getLongPollServer(group_id = group_id, v = version)
		self.is_polling = False
	
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
	
	def send_error_message(self, user_id, msg):
		self.send_message(user_id, msg, keyboard = VK_Bot.error_keyboard)
	
	def send(self, manager_id, notification, settings_wrapper):
		self.send_message(int(manager_id), notification, keyboard = VK_Bot.notification_keyboard)
		#type = notification
		settings_wrapper.lock.acquire()
		settings_wrapper.payload['managers'][str(manager_id)]['latest_msg_type'] = 'notification'
		settings_wrapper.lock.release()