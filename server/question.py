# *-* coding:utf-8 *-*

import json
import urllib
import MySQLdb
import traceback

from hashlib import sha1
from tornado import web,httpclient,gen
from base import Base,Configer
from business import Business
from exception import DBException,CKException
from http import Http
from gl import LOG
from mysql import Mysql
from mongo import Mongo
from qiniu_wrap import QiniuWrap

def error_process(index):
    msg = [ { "error_code" : 0, "error_msg" : "success" }, { "error_code" : 1, "error_msg" : "invalid parameters" }, { "error_code" : 2, "error_msg" : "resources nonexistent" } ] 
    if index >= len(msg):
        return { "error_code" : 100, "error_msg" : "unknown error" }
    return msg[index]

class UploadQuestion(web.RequestHandler):

	@web.asynchronous
	@gen.engine
	def post(self):
		
		for i in range(1):

			self.set_header("Access-Control-Allow-Origin", "*")

			LOG.info('API IN[%s]' % (self.__class__.__name__))
			LOG.info('PARAMETER IN[%s]' % self.request.arguments)
			
			ret = {'code':'','message':'','id':-9999}

			essential_keys = set(['json','html','topic','seriess','level','type','group','timestamp','secret'])

			if Base.check_parameter(set(self.request.arguments.keys()),essential_keys):
				ret['code'] = 1
				ret['message'] = 'invalid parameters'
				LOG.error('ERR[in parameter invalid]') 
				break

			question_json = ''.join(self.request.arguments['json'])
			question_html = ''.join(self.request.arguments['html'])
			question_topic = ''.join(self.request.arguments['topic'])
			question_seriess = ''.join(self.request.arguments['seriess'])
			question_level = ''.join(self.request.arguments['level'])
			question_type = ''.join(self.request.arguments['type'])
			question_group = ''.join(self.request.arguments['group'])
			timestamp = ''.join(self.request.arguments['timestamp'])
			secret = ''.join(self.request.arguments['secret'])

			if Business.is_level(question_level) is False:
				ret['code'] = 1
				ret['message'] = 'invalid parameters'
				LOG.error('ERR[level is invalid]') 
				break

			if Base.empty(timestamp):
				ret['code'] = 1
				ret['message'] = 'invalid parameters'
				LOG.error('ERR[timestamp empty]') 
				break
			
			try:
				question_json = urllib.unquote(question_json)
				encode_json = json.loads(question_json,encoding = 'utf-8')
				question_html = urllib.unquote(question_html)
				encode_html = json.loads(question_html,encoding = 'utf-8')

				if Base.empty(question_topic) and Base.empty(question_seriess):
					ret['code'] = 1
					ret['message'] = 'invalid parameters'
					LOG.error('ERR[topic and seriess empty]') 
					break

				if Base.empty(question_group):
					ret['code'] = 1
					ret['message'] = 'invalid parameters'
					LOG.error('ERR[group empty]') 
					break


				if Base.empty(question_topic) is False:
					topic_list = question_topic.split(',')

					for question_theme in topic_list:
						if Business.is_topic(question_theme) is False:
							ret['code'] = 1
							ret['message'] = 'invalid parameters'
							LOG.error('ERR[topic %s invalid]' % question_theme) 
							break

				if Base.empty(question_seriess) is False:
					seriess_list = question_seriess.split(',')

					for question_special in seriess_list:
						if Business.is_seriess(question_special) is False:
							ret['code'] = 1
							ret['message'] = 'invalid parameters'
							LOG.error('ERR[seriess %s invalid]' % question_theme) 
							break

				type_name =  Business.is_type(question_type)

				if type_name is False:
					ret['code'] = 1
					ret['message'] = 'invalid parameters'
					LOG.error('ERR[type is invalid]') 
					break

				if 0 != int(question_group):
					if Business.group_id_exist(question_group) is False:
						ret['code'] = 8
						ret['message'] = 'key not exsit'
						LOG.error('ERROR[group not exist]')
						break	

			except (ValueError,KeyError,TypeError):
				ret['code'] = 1
				ret['message'] = 'invalid parameters'
				LOG.error('ERR[json format invalid]') 
				break
			
			except CKException: 
				ret['code'] = 3
				ret['message'] = 'server error'
				LOG.error('ERR[mysql exception]') 
				break

			key = question_topic + question_seriess + question_level + question_type + question_group + timestamp
			secret_key = sha1(key).hexdigest()
				
			if secret == secret_key:
				
				qiniu = QiniuWrap()

				json_key = 'tmp_' + secret_key + '.json'
				if qiniu.upload_data("temp",json_key,question_json) is not None:
					ret['code'] = 4
					ret['message'] = 'qiniu error'
					LOG.error('ERR[json upload  qiniu exception]') 
					break
				
				html_key = 'tmp_' + secret_key + '.html'
				if qiniu.upload_data("temp",html_key,question_html) is not None:
					ret['code'] = 4
					ret['message'] = 'qiniu error'
					LOG.error('ERR[html upload  qiniu exception]') 
					break

 				configer = Configer()
                                remote_host = configer.get_configer('REMOTE','host')
                                remote_port = configer.get_configer('REMOTE','port')
                                remote_uri = configer.get_configer('REMOTE','uri')
				remote_timeout = configer.get_configer('REMOTE','timeout')
                                
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
                                response = yield gen.Task(client.fetch,remote_url,request_timeout = int(remote_timeout),method = 'POST',body = urllib.urlencode(post_data
))
                                #response = Http.post(remote_url,post_data)

				if 200 == response.code:
					encode_body = json.loads(response.body,encoding = 'utf-8')

					if 0 == encode_body['code'] or 2 == encode_body['code']:
						ret['code'] = 7
						ret['message'] = 'invalid token'
						LOG.error('ERR[token not exist]')
						break

					if 1 == encode_body['code']:
						subject_id = encode_body['subject_id']
						grade_id = encode_body['grade_id']
						system_id = encode_body['system_id']
						org_type = encode_body['org_type']

						db = Mysql()

						question_sql = "insert into entity_question (difficulty,question_docx,html,upload_time,question_type,subject_id,new_format,upload_id,upload_src,question_group,grade_id) values (%(level)d,'%(json)s','%(html)s',now(),'%(type)s',%(subject_id)d,1,%(upload_id)d,%(upload_src)d,%(question_group)d,%(grade_id)d);"
						
						link_topic_sql = "insert into link_question_topic (question_id,topic_id) values (%(q_id)d,%(t_id)d);"

						link_series_sql = "insert into link_question_series (question_id,series_id) values (%(q_id)d,%(s_id)d);"

						try:
							db.connect_master()
							db.start_event()

							question_res = db.exec_event(question_sql,level = int(question_level),json = json_key,html = html_key,type = type_name,subject_id = int(subject_id),upload_id = int(system_id),upload_src = int(org_type),question_group = int(question_group),grade_id = int(grade_id))
							question_sql = db.get_last_sql()
							question_id = db.get_last_id()
							LOG.info('SQL[%s] - RES[%s] - INS[%d]' % (question_sql,question_res,question_id))
					
							if Base.empty(question_topic) is False:
								topic_list = question_topic.split(',')
								for question_theme in topic_list:
									topic_res = db.exec_event(link_topic_sql,q_id = int(question_id),t_id = int(question_theme))
									topic_sql = db.get_last_sql()
									topic_id = db.get_last_id()
									LOG.info('SQL[%s] - RES[%s] - INS[%d]' % (link_topic_sql,topic_res,topic_id))
							if Base.empty(question_seriess) is False:
								seriess_list = question_seriess.split(',')

								for question_special in seriess_list:
									series_res = db.exec_event(link_series_sql,q_id = int(question_id),s_id = int(question_special))
									series_sql = db.get_last_sql()
									series_id = db.get_last_id()
									LOG.info('SQL[%s] - RES[%s] - INS[%d]' % (link_series_sql,series_res,series_id))

						except DBException as e:
							ret['code'] = 3
							ret['message'] = 'server error'
							LOG.error('ERR[insert mysql error]') 
							break

				else:
					ret['code'] = 3
					ret['message'] = 'server error'
					LOG.error('ERROR[remote error]')
					break
								
				encode_json['question_id'] = question_id
				encode_html['question_id'] = question_id

				mongo = Mongo()

				try:
					mongo.connect('resource')
					mongo.select_collection('mongo_question_json')
					json_id = mongo.insert_one(encode_json)
					LOG.info('MONGO[insert json] - DATA[%s] - INS[%s]' % (question_json,json_id))

					mongo.select_collection('mongo_question_html')
					html_id = mongo.insert_one(encode_html)
					LOG.info('MONGO[insert html] - DATA[%s] - INS[%s]' % (question_html,html_id))

				except DBException as e:
					ret['code'] = 3 
					ret['message'] = 'server error'
					LOG.error('ERR[mongo exception]') 
					break

				db.end_event()

				ret['code'] = 0
				ret['message'] = 'success'
				ret['id'] = question_id

			else:
				ret['code'] = 5 
				ret['message'] = 'secure key error'
				LOG.error('ERR[secure key error]') 
				break

		LOG.info('PARAMETER OUT[%s]' % ret)
		LOG.info('API OUT[%s]' % (self.__class__.__name__))
		self.write(json.dumps(ret))
		self.finish()

class get_exercises(web.RequestHandler):

    def post(self):

        self.set_header("Access-Control-Allow-Origin", "*")

        if set(self.request.arguments.keys()) != set(['id', 'timestamp', 'secret']):
            LOG.error('invalid parameter keys: %s' % self.request.arguments)
            return self.write(error_process(1))

        topic_id = int(self.request.arguments['id'][0])
        timestamp = self.request.arguments['timestamp'][0]
        secret = self.request.arguments['secret'][0]

        secret_key = '%d%s' % (topic_id, timestamp)
        if secret != sha1(secret_key).hexdigest():
            LOG.error('sign error! secret_key: %s' % secret_key)
            return self.write(error_process(3))

        try:
            mysql = Mysql().get_handle()
            cursor = mysql.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT question_type, subject_id, difficulty FROM entity_question WHERE id = %d' % topic_id)
            result = cursor.fetchall()
            if not result and 1 != len(result):
                LOG.error('abnormal topic_id[%d]!' % topic_id)
                return self.write(error_process(2))
            level_id = result[0]['difficulty']
            topic_type = result[0]['question_type']
            subject_id = result[0]['subject_id']

            # 获取题目类型
            cursor.execute('SELECT type_id id, name FROM entity_question_type WHERE name = "%s"' % topic_type)
            topic_type = cursor.fetchall()
            if not topic_type and 1 != len(topic_type):
                LOG.error('abnormal type of topic_id[%d]!' % topic_id)
                return self.write(error_process(2))
#            print 'topic_type: %s' % topic_type

            # 获取主题
            cursor.execute('select id, substring_index(name, "\n", 1) name from entity_topic where id in (select topic_id from link_question_topic where question_id = %d)' % topic_id)
            theme_list = list(cursor.fetchall())
#            print 'theme: %s' % theme_list

            # 获取专题
            cursor.execute('select id, substring_index(name, "\n", 1) name from entity_seriess where id in (select series_id from link_question_series where question_id = %d)' % topic_id)
            special_list = list(cursor.fetchall())
#            print 'special: %s' % special_list

            mongo = Mongo().get_handle()
            result = mongo.resource.mongo_question_json.find_one( { "question_id" : topic_id } )
            if not result:# or 'body' not in result:
                LOG.error('json body of question_id[%d] nonexistent!' % topic_id)
                return self.write(error_process(2))
            json_body = result['body']

            result = mongo.resource.mongo_question_html.find_one( { "question_id" : topic_id } )
            if not result:# or 'body' not in result:
                LOG.error('html body of question_id[%d] nonexistent!' % topic_id)
                return self.write(error_process(2))
            html_body = result['body']

            result            = error_process(0)
            result['json']    = json_body
            result['html']    = html_body
            result['topic']   = theme_list
            result['seriess'] = special_list
            result['level']   = level_id
            result['type']    = topic_type[0]

            self.write(json.dumps(result, ensure_ascii=False))

            mongo.close()
            cursor.close()
            mysql.close()
        except MySQLdb.Error, e:
            LOG.error(e)
            return self.write(error_process(100))
        except Exception, e:
            LOG.error(e)
            return self.write(error_process(100))

class update_exercises(web.RequestHandler):

    def post(self):

        self.set_header("Access-Control-Allow-Origin", "*")

        if set(self.request.arguments.keys()) != set(['id', 'json', 'html', 'topic', 'seriess', 'level', 'type', 'timestamp', 'secret']):
            LOG.error('invalid parameter keys: %s' % self.request.arguments.keys())
            return self.write(error_process(1))

        theme         = self.request.arguments['topic'][0]
        secret        = self.request.arguments['secret'][0]
        special       = self.request.arguments['seriess'][0]
        level_id      = int(self.request.arguments['level'][0])
        timestamp     = self.request.arguments['timestamp'][0]
        question_id   = int(self.request.arguments['id'][0])
        question_type = self.request.arguments['type'][0]
        question_json = self.request.arguments['json'][0]
        question_html = self.request.arguments['html'][0]

        LOG.debug('question_id: %d, theme: %s, special: %s, level_id: %d, question_type: %s, timestamp: %s, secret: %s, question_json: %s, question_html: %s' % (question_id, theme, special, level_id, question_type, timestamp, secret, question_json, question_html))

        secret_key = '%d%s%s%d%s%s' % (question_id, theme, special, level_id, question_type, timestamp)
        if secret != sha1(secret_key).hexdigest():
            LOG.error('sign error! secret_key: %s' % secret_key)
            return self.write(error_process(3))

        try:
            if Business.is_level(level_id) is False:
                LOG.error('invalid level_id[%d]' % level_id)
                return self.write(error_process(1))
 
            if not (level_id and question_type and question_json and question_html and question_id and secret and timestamp and theme + special):
                LOG.error('invalid parameters: %s' % self.request.arguments)
                return self.write(error_process(1))
 
            try:
                question_json = urllib.unquote(question_json)
                encode_json   = json.loads(question_json, encoding = 'utf-8')
                question_html = urllib.unquote(question_html)
                encode_html   = json.loads(question_html, encoding = 'utf-8')
            except:
                traceback.print_exc()
                LOG.error(sys.exc_info())
                return self.write(error_process(100))
 
            LOG.debug('question_json: %s, question_html: %s' % (question_json, question_html))
 
            sql_list = []
 
            if theme: # 主题
                sql_list.append('DELETE FROM link_question_topic WHERE question_id=%d' % question_id) # 生成删除原有主题关联的SQL
                for theme_id in theme.split(','): # 将传入的主题号按逗号切割
                    if Business.is_topic(theme_id) is False: # 判断主题号是否存在
                        LOG.error('invalid theme_id[%s]' % theme_id)
                        return self.write(error_process(1))
                    sql_list.append('INSERT INTO link_question_topic (question_id, topic_id) VALUES (%s, %s)' % (question_id, theme_id)) # 生成将新主题关联插库的SQL
 
            if special: # 专题
                sql_list.append('DELETE FROM link_question_series WHERE question_id=%d' % question_id) # 生成删除原有专题关联的SQL
                for special_id in special.split(','): # 将传入的专题号按逗号切割
                    if Business.is_seriess(special_id) is False: # 判断专题号是否存在
                        LOG.error('invalid special_id[%s]' % special_id)
                        return self.write(error_process(1))
                    sql_list.append('INSERT INTO link_question_series (question_id, series_id) VALUES (%s, %s)' % (question_id, special_id)) # 生成将新专题关联插库的SQL
 
#            if Business.is_type(question_type) is False: # 判断题目类型是否存在
#                LOG.error('invalid question_type[%s]' % question_type)
#                return self.write(error_process(1))
            sql_list.append('UPDATE entity_question SET difficulty=%d, upload_time=now(), question_type="%s" WHERE id=%d' % (level_id, question_type, question_id)) # 生成更新题目属性的SQL
 
            mysql_handle = Mysql().get_handle()
            mysql_cursor = mysql_handle.cursor(MySQLdb.cursors.DictCursor)
            mysql_cursor.execute('SELECT question_docx, html FROM entity_question WHERE id=%d' % question_id) # 通过题目ID查询存储的json/html文件名
            result = mysql_cursor.fetchall()
            if not result:
                LOG.error('invalid question_id[%d]' % question_id)
                return self.write(error_process(1))
 
            qiniu = QiniuWrap()
            mongo = Mongo()
            mongo.connect('resource')
 
            if '.json' in result[0]['question_docx']:
                json_name = result[0]['question_docx']
                # 将七牛上的json文件删除后重新上传
                qiniu.bucket.delete("temp", json_name)
                qiniu.upload_data("temp", json_name, question_json)
                # 将MongoDB中的json文件删除后重新上传
                mongo.select_collection('mongo_question_json')
                mongo.remove( { "question_id" : question_id } )
                encode_json['question_id'] = question_id
                mongo.insert_one(encode_json)
 
            if '.html' in result[0]['html']:
                html_name = result[0]['html']
                # 将七牛上的html文件删除后重新上传
                qiniu.bucket.delete("temp", html_name)
                qiniu.upload_data("temp", html_name, question_html)
                # 将MongoDB中的html文件删除后重新上传
                mongo.select_collection('mongo_question_html')
                mongo.remove( { "question_id" : question_id } )
                encode_html['question_id'] = question_id
                mongo.insert_one(encode_html)
 
            print 'json_name: %s, html_name: %s' % (json_name, html_name)
 
            for sql in sql_list:
                mysql_cursor.execute(sql)
            mysql_handle.commit()
            mysql_cursor.close()
            mysql_handle.close()
 
            self.write(error_process(0))
        except MySQLdb.Error, e:
            LOG.error(e)
            return self.write(error_process(100))
        except Exception, e:
            LOG.error(e)
            return self.write(error_process(100))

