# *-* coidng:utf-8 *-*

from hashlib import sha1
import json
from tornado import web,httpclient,gen

from base import Base
from business import Business
from base import Configer
from exception import DBException,CKException
from gl import LOG
from http import Http
from mysql import Mysql
import urllib

class CreateGroup(web.RequestHandler):

	@web.asynchronous
	@gen.engine
	def post(self):
		
		for i in range(1):

			LOG.info('API IN[%s]' % (self.__class__.__name__))
                        LOG.info('PARAMETER IN[%s]' % self.request.arguments)

                        ret = {'code':'','message':''}

                        essential_keys = set(['name','timestamp','secret'])

                        if Base.check_parameter(set(self.request.arguments.keys()),essential_keys):
                                ret['code'] = 1
                                ret['message'] = 'invalid parameter'
				LOG.error('ERROR[in parameter invalid]')
                                break
			
			group_name = ''.join(self.request.arguments['name'])
			timestamp = ''.join(self.request.arguments['timestamp'])
			secret = ''.join(self.request.arguments['secret'])

			if Base.empty(group_name) or Base.empty(timestamp) or Base.empty(secret):
				ret['code'] = 1
				ret['message'] = 'invalid parameter'
				LOG.error('ERROR[parameter empty]')
				break

			key = group_name + timestamp;
			secret_key = sha1(key).hexdigest()

			if secret == secret_key:
				configer = Configer()
				remote_host = configer.get_configer('REMOTE','host')
				remote_port = configer.get_configer('REMOTE','port')
				remote_uri = configer.get_configer('REMOTE','uri')

				remote_url = "http://%s:%s/%s" % (remote_host,remote_port,remote_uri)
				
				token = self.get_cookie("teacher_id")
				LOG.info('TOKEN[%s]' % token)

				if token is None:
					ret['code'] = 6
					ret['message'] = 'invalid token'
					LOG.error('ERROR[token empty]')
					break

				post_data = {'token' : token}
				
				client = httpclient.AsyncHTTPClient()
				response = yield gen.Task(client.fetch,remote_url,method = 'POST',body = urllib.urlencode(post_data))
				#response = Http.post(remote_url,post_data)

				LOG.info('REMOTE RES CODE[%d]' % response.code)

				if 200 == response.code:
					encode_body = json.loads(response.body)

					if 0 == encode_body['code'] or 2 == encode_body['code']:
						ret['code'] = 7
						ret['message'] = 'invalid token'
						LOG.error('ERROR[token not exist]')
						break

					if 1 == encode_body['code']:
						subject_id = encode_body['subject_id']
						grade_id = encode_body['grade_id']
						system_id = encode_body['system_id']
						org_type = encode_body['org_type']				
						
						if Business.group_name_exist(group_name,system_id):
							ret['code'] = 6
							ret['message'] = 'key exsit'
							LOG.error('ERROR[group exist]')
							break

						db = Mysql()
				
						group_sql = "insert into entity_group (name,system_id) values ('%(group_name)s',%(system_id)d);"

						try:
							db.connect_master()
							group_res = db.query(group_sql,group_name = group_name,system_id = system_id)

							group_sql = db.get_last_sql()
							group_id = db.get_last_id()
							LOG.info('SQL[%s] - RES[%s] - INS[%d]' % (group_sql,group_res,group_id))
						
						except DBException as e:
							ret['code'] = 3
							ret['message'] = 'server error'
							LOG.error('ERROR[mysql error]')
							break


					else:
						ret['code'] = 3 
						ret['message'] = 'server error'
						LOG.error('ERROR[remote error]')
						break

				else:
					ret['code'] = 3 
					ret['message'] = 'server error'
					LOG.error('ERROR[remote error]')
					break

				ret['code'] = 0
				ret['message'] = 'success'
				break				
			else:
				ret['code'] = 4
				ret['message'] = 'secure key error'
				LOG.error('ERR[secure key error]') 
				break

		self.write(json.dumps(ret))
		self.finish()
		LOG.info('PARAMETER OUT[%s]' % ret)
		LOG.info('API OUT[%s]' % (self.__class__.__name__))

class GetGroupList(web.RequestHandler):

	@web.asynchronous
	@gen.engine
	def get(self):

		for i in range(1):
			
			LOG.info('API IN[%s]' % (self.__class__.__name__))
                        LOG.info('PARAMETER IN[%s]' % self.request.arguments)

                        ret = {'code':'','message':'','group_list' : []}

                        essential_keys = set(['timestamp','secret'])

                        if Base.check_parameter(set(self.request.arguments.keys()),essential_keys):
                                ret['code'] = 1
                                ret['message'] = 'invalid parameter'
				LOG.error('ERR[in parameter invalid]') 
                                break
			
			timestamp = ''.join(self.request.arguments['timestamp'])
			secret = ''.join(self.request.arguments['secret'])

			if Base.empty(timestamp):
				ret['code'] = 1
				ret['message'] = 'invalid parameter'
				LOG.error('ERROR[parameter empty]')
				break

			key = timestamp;
			secret_key = sha1(key).hexdigest()

			if secret == secret_key:
				configer = Configer()
				remote_host = configer.get_configer('REMOTE','host')
				remote_port = configer.get_configer('REMOTE','port')
				remote_uri = configer.get_configer('REMOTE','uri')

				remote_url = "http://%s:%s/%s" % (remote_host,remote_port,remote_uri)
				
				token = self.get_cookie("teacher_id")
				LOG.info('TOKEN[%s]' % token)

				if token is None:
					ret['code'] = 6
					ret['message'] = 'invalid token'
					LOG.error('ERROR[token empty]')
					break

				post_data = {'token' : token}
				
				client = httpclient.AsyncHTTPClient()
				response = yield gen.Task(client.fetch,remote_url,method = 'POST',body = urllib.urlencode(post_data))
				#response = Http.post(remote_url,post_data)
				LOG.info('REMOTE RES CODE[%d]' % response.code)

				if 200 == response.code:
					encode_body = json.loads(response.body)

					if 0 == encode_body['code'] or 2 == encode_body['code']:
						ret['code'] = 7
						ret['message'] = 'invalid token'
						LOG.error('ERR[token not exist]') 
						break

					if 1 == encode_body['code']:
						#subject_id = encode_body['subject_id']
						#grade_id = encode_body['grade_id']
						system_id = encode_body['system_id']
						#org_type = encode_body['org_type']				
					
						try:
							group_list = Business.get_group_list(system_id)
							
							if group_list is not False:
								ret['group_list'] = group_list				

						except DBException as e:
							ret['code'] = 3
							ret['message'] = 'server error'
							LOG.error('ERR[mysql error]') 
							break

					else:
						ret['code'] = 3 
						ret['message'] = 'server error'
						LOG.error('ERROR[remote error]')
						break
					
				else:
					ret['code'] = 3 
					ret['message'] = 'server error'
					LOG.error('ERROR[remote error]')
					break

				ret['code'] = 0
				ret['message'] = 'success'
				break
			else:
				ret['code'] = 4
				ret['message'] = 'secure key error'
				LOG.error('ERR[secure key error]') 
				break
		LOG.info(ret)
		self.write(ret)
		self.finish()
		LOG.info('PARAMETER OUT[%s]' % ret)
		LOG.info('API OUT[%s]' % (self.__class__.__name__))

class UpdateGroup(web.RequestHandler):

	@web.asynchronous
	@gen.engine
	def post(self):
		
		for i in range(1):

			LOG.info('API IN[%s]' % (self.__class__.__name__))
                        LOG.info('PARAMETER IN[%s]' % self.request.arguments)

                        ret = {'code':'','message':''}

                        essential_keys = set(['id','name','timestamp','secret'])

                        if Base.check_parameter(set(self.request.arguments.keys()),essential_keys):
                                ret['code'] = 1
                                ret['message'] = 'invalid parameter'
				LOG.error('ERROR[in parameter invalid]')
                                break

			group_id = ''.join(self.request.arguments['id'])
			group_name = ''.join(self.request.arguments['name'])
			timestamp = ''.join(self.request.arguments['timestamp'])
			secret = ''.join(self.request.arguments['secret'])

			if Base.empty(group_id) or Base.empty(group_name) or Base.empty(timestamp) or Base.empty(secret):
				ret['code'] = 1
				ret['message'] = 'invalid parameter'
				LOG.error('ERROR[parameter empty]')
				break

			key = group_id + group_name + timestamp;
			secret_key = sha1(key).hexdigest()

			if secret == secret_key:
				configer = Configer()
				remote_host = configer.get_configer('REMOTE','host')
				remote_port = configer.get_configer('REMOTE','port')
				remote_uri = configer.get_configer('REMOTE','uri')

				remote_url = "http://%s:%s/%s" % (remote_host,remote_port,remote_uri)
				
				token = self.get_cookie("teacher_id")
				LOG.info('TOKEN[%s]' % token)

				if token is None:
					ret['code'] = 6
					ret['message'] = 'invalid token'
					LOG.error('ERROR[token empty]')
					break

				post_data = {'token' : token}
				
				client = httpclient.AsyncHTTPClient()
				response = yield gen.Task(client.fetch,remote_url,method = 'POST',body = urllib.urlencode(post_data))
				#response = Http.post(remote_url,post_data)

				LOG.info('REMOTE RES CODE[%d]' % response.code)

				if 200 == response.code:
					encode_body = json.loads(response.body)

					if 0 == encode_body['code'] or 2 == encode_body['code']:
						ret['code'] = 7
						ret['message'] = 'invalid token'
						LOG.error('ERROR[token not exist]')
						break

					if 1 == encode_body['code']:
						subject_id = encode_body['subject_id']
						grade_id = encode_body['grade_id']
						system_id = encode_body['system_id']
						org_type = encode_body['org_type']				
						
						if Business.group_name_exist(group_name,system_id):
							ret['code'] = 6
							ret['message'] = 'key exsit'
							LOG.error('ERROR[group exist]')
							break

						db = Mysql()
				
						group_sql = "update entity_group set name='%(group_name)s' where id=%(group_id)d and system_id=%(system_id)d;"

						try:
							db.connect_master()
							group_res = db.query(group_sql,group_name = group_name,group_id = int(group_id),system_id = int(system_id))

							if group_res is False:
								ret['code'] = 7 
								ret['message'] = 'key not exist'
								LOG.error('ERROR[group not exist]')
								break	

							group_sql = db.get_last_sql()
							group_id = db.get_last_id()
							LOG.info('SQL[%s] - RES[%s] - INS[%d]' % (group_sql,group_res,group_id))
						
						except DBException as e:
							ret['code'] = 3
							ret['message'] = 'server error'
							LOG.error('ERROR[mysql error]')
							break

					else:
						ret['code'] = 3 
						ret['message'] = 'server error'
						LOG.error('ERROR[remote error]')
						break

				else:
					ret['code'] = 3 
					ret['message'] = 'server error'
					LOG.error('ERROR[remote error]')
					break

				ret['code'] = 0
				ret['message'] = 'success'
				break				
			else:
				ret['code'] = 4
				ret['message'] = 'secure key error'
				LOG.error('ERR[secure key error]') 
				break

		self.write(json.dumps(ret))
		self.finish()
		LOG.info('PARAMETER OUT[%s]' % ret)
		LOG.info('API OUT[%s]' % (self.__class__.__name__))

class DeleteGroup(web.RequestHandler):

	@web.asynchronous
	@gen.engine
	def post(self):
		
		for i in range(1):

			LOG.info('API IN[%s]' % (self.__class__.__name__))
                        LOG.info('PARAMETER IN[%s]' % self.request.arguments)

                        ret = {'code':'','message':''}

                        essential_keys = set(['id','timestamp','secret'])

                        if Base.check_parameter(set(self.request.arguments.keys()),essential_keys):
                                ret['code'] = 1
                                ret['message'] = 'invalid parameter'
				LOG.error('ERROR[in parameter invalid]')
                                break
			
			group_id = ''.join(self.request.arguments['id'])
			timestamp = ''.join(self.request.arguments['timestamp'])
			secret = ''.join(self.request.arguments['secret'])

			if Base.empty(group_id) or Base.empty(timestamp) or Base.empty(secret):
				ret['code'] = 1
				ret['message'] = 'invalid parameter'
				LOG.error('ERROR[parameter empty]')
				break

			key = group_id + timestamp;
			secret_key = sha1(key).hexdigest()

			if secret == secret_key:
				configer = Configer()
				remote_host = configer.get_configer('REMOTE','host')
				remote_port = configer.get_configer('REMOTE','port')
				remote_uri = configer.get_configer('REMOTE','uri')

				remote_url = "http://%s:%s/%s" % (remote_host,remote_port,remote_uri)
				
				token = self.get_cookie("teacher_id")
				LOG.info('TOKEN[%s]' % token)

				if token is None:
					ret['code'] = 6
					ret['message'] = 'invalid token'
					LOG.error('ERROR[token empty]')
					break

				post_data = {'token' : token}
				
				client = httpclient.AsyncHTTPClient()
				response = yield gen.Task(client.fetch,remote_url,method = 'POST',body = urllib.urlencode(post_data))
				#response = Http.post(remote_url,post_data)

				LOG.info('REMOTE RES CODE[%d]' % response.code)

				if 200 == response.code:
					encode_body = json.loads(response.body)

					if 0 == encode_body['code'] or 2 == encode_body['code']:
						ret['code'] = 7
						ret['message'] = 'invalid token'
						LOG.error('ERROR[token not exist]')
						break

					if 1 == encode_body['code']:
						subject_id = encode_body['subject_id']
						grade_id = encode_body['grade_id']
						system_id = encode_body['system_id']
						org_type = encode_body['org_type']				

						db = Mysql()
				
						group_sql = "delete from entity_group where id=%(group_id)d and system_id=%(system_id)d);"
						question_sql = "update entity_question set question_group=0 where question_group=%(group_id)d and system_id=%(system_id)d;"

						try:
							db.connect_master()
							db.start_event()

							group_res = db.exec_event(group_sql,group_id = int(group_id),system_id = int(system_id))
							if group_res is False:
								ret['code'] = 7 
								ret['message'] = 'key not exist'
								LOG.error('ERROR[group not exist]')
								break

							group_sql = db.get_last_sql()
							group_id = db.get_last_id()
							LOG.info('SQL[%s] - RES[%s] - INS[%d]' % (group_sql,group_res,group_id))
							question_res = db.exec_event(question_sql,group_id = int(group_id),system_id = int(system_id))
							if question_res is False:
								ret['code'] = 7 
								ret['message'] = 'key not exist'
								LOG.error('ERROR[group not exist]')
								break

							question_sql = db.get_last_sql()
							LOG.info('SQL[%s] - RES[%s]' % (question_sql,question_res))

						except DBException as e:
							ret['code'] = 3
							ret['message'] = 'server error'
							LOG.error('ERROR[mysql error]')
							break


					else:
						ret['code'] = 3 
						ret['message'] = 'server error'
						LOG.error('ERROR[remote error]')
						break

				else:
					ret['code'] = 3 
					ret['message'] = 'server error'
					LOG.error('ERROR[remote error]')
					break

				db.end_event()

				ret['code'] = 0
				ret['message'] = 'success'
				break				
			else:
				ret['code'] = 4
				ret['message'] = 'secure key error'
				LOG.error('ERR[secure key error]') 
				break

		self.write(json.dumps(ret))
		self.finish()
		LOG.info('PARAMETER OUT[%s]' % ret)
		LOG.info('API OUT[%s]' % (self.__class__.__name__))


