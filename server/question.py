# *-*coding:utf8*-*

import json
import time
import redis
import urllib
import MySQLdb
import hashlib
import urllib2
import traceback

from gl import LOG
from http import Http
from mysql import Mysql
from mongo import Mongo
from hashlib import sha1
from business import Business
from base import Base, Configer
from qiniu_wrap import QiniuWrap
from tornado import web, httpclient, gen
from exception import DBException, CKException

#public_key = '&*312#'
#host = 'wenku.baidu.com'
#secret_key = '6f614cb00c6b6821e3cdc85ab1f8f907'
public_key = '$@a5d3'
host = 'xdf.baidu.com'
secret_key = '358ce98368a638bd23583c38cbddc1d1'

def error_process(index):
    msg = [ { "error_code" : 0, "error_msg" : "success" }, { "error_code" : 1, "error_msg" : "invalid parameters" }, { "error_code" : 2, "error_msg" : "resources nonexistent" }, { "error_code" : 3, "error_msg" : "sign error" } ] 
    if index >= len(msg):
        return { "error_code" : 100, "error_msg" : "unknown error" }
    return msg[index]


def generate_token():
    ctime = int(time.time())
    md5 = hashlib.md5()
    md5.update('%s%s%d' % (host, public_key, ctime))
    return '%s|%s' % (md5.hexdigest(), ctime)

#    url = 'http://wenku.baidu.com/api/interface/gettoken?host=%s&secretKey=%s' % (host, secret_key)
#    result = eval(urllib2.urlopen(url).read())
#    if 0 != result['status']['code']:
#        LOG.info(result)
#        return ''
#    return result['data']['token']

class UploadQuestion(web.RequestHandler):

	@web.asynchronous
	@gen.engine
	def post(self):
		
		for i in range(1):

			self.set_header("Access-Control-Allow-Origin", "*")

			LOG.info('API IN[%s]' % (self.__class__.__name__))
			LOG.info('PARAMETER IN[%s]' % self.request.arguments)
			
			ret = {'code':'','message':''}

			essential_keys = set(['json','html','topic','level','type','group','chapter'])

			if Base.check_parameter(set(self.request.arguments.keys()),essential_keys):
				ret['code'] = 1
				ret['message'] = 'invalid parameters'
				LOG.error('ERR[in parameter invalid]') 
				break

			question_json = ''.join(self.request.arguments['json'])
			question_html = ''.join(self.request.arguments['html'])
			question_topic = ''.join(self.request.arguments['topic'])
			question_level = ''.join(self.request.arguments['level'])
			question_type = ''.join(self.request.arguments['type'])
			question_group = ''.join(self.request.arguments['group'])
			question_chapter = ''.join(self.request.arguments['chapter'])

			if Business.is_level(question_level) is False:
				ret['code'] = 1
				ret['message'] = 'invalid parameters'
				LOG.error('ERR[level is invalid]') 
				break

			try:
				question_json = urllib.unquote(question_json)
				question_json = question_json.replace("'","\"")
				encode_json = json.loads(question_json,encoding = 'utf-8')
				question_html = urllib.unquote(question_html)
				question_html = question_html.replace("'","\"")
				encode_html = json.loads(question_html,encoding = 'utf-8')

				answer_num = 0
				
				if Base.empty(question_topic) and Base.empty(question_chapter):
					ret['code'] = 1
					ret['message'] = 'invalid parameters'
					LOG.error('ERR[topic and chapter empty]') 
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

				type_name =  Business.is_type(question_type)

				if type_name is False:
					ret['code'] = 1
					ret['message'] = 'invalid parameters'
					LOG.error('ERR[type is invalid]') 
					break

				if type_name == '选择题'.decode('utf-8'):
					if 'answer' in encode_json.keys():
						print encode_json['answer']
				    		answer_num = len(encode_json['answer'])

				if type_name == '填空题'.decode('utf-8'):
					if 'answer' in encode_json.keys():
						print encode_json['answer']
				    		answer_num = max([int(group['index']) for group in encode_json['answer']])

				if not Base.empty(question_chapter):
					if Business.chapter_id_exist(question_chapter) is False:
						ret['code'] = 1
						ret['message'] = 'invalid parameters'
						LOG.error('ERR[seriess %s invalid]' % question_theme) 
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

			key = question_topic + question_level + question_type + question_group
			secret_key = hashlib.sha1(key).hexdigest()

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


					if 0 != int(question_group):
						if Business.group_id_exist(question_group,system_id) is False:
							ret['code'] = 8
							ret['message'] = 'key not exsit'
							LOG.error('ERROR[group not exist]')
							break	

					db = Mysql()

					question_sql = "insert into entity_question (difficulty,question_docx,html,upload_time,question_type,subject_id,new_format,upload_id,upload_src,question_group,grade_id,state,is_single,question_typeid,answer_num,count_ref,paper_year,parent_question_id) values (%(level)d,'%(json)s','%(html)s',now(),'%(type)s',%(subject_id)d,1,%(upload_id)d,%(upload_src)d,%(question_group)d,%(grade_id)d,'RAW',1,%(question_typeid)d,%(answer_num)d,0,0,0);"
					
					link_topic_sql = "insert into link_question_topic (question_id,topic_id) values (%(q_id)d,%(t_id)d);"

					link_chapter_sql = "insert into link_question_chapter (question_id,chapter_id) values (%(q_id)d,%(c_id)d);"

					try:
						db.connect_master()
						db.start_event()

						question_res = db.exec_event(question_sql,level = int(question_level),json = json_key,html = html_key,type = type_name,subject_id = int(subject_id),upload_id = int(system_id),upload_src = int(org_type),question_group = int(question_group),grade_id = int(grade_id),question_typeid = int(question_type),answer_num = answer_num)
						question_sql = db.get_last_sql()
						question_id = db.get_last_id()
						LOG.info('RES[%s] - INS[%d]' % (question_res,question_id))
				
						if Base.empty(question_topic) is False:
							topic_list = question_topic.split(',')
							for question_theme in topic_list:
								topic_res = db.exec_event(link_topic_sql,q_id = int(question_id),t_id = int(question_theme))
								topic_sql = db.get_last_sql()
								topic_id = db.get_last_id()
								LOG.info('RES[%s] - INS[%d]' % (topic_res,topic_id))

						if not Base.empty(question_chapter):
							chapter_res = db.exec_event(link_chapter_sql,q_id = int(question_id),c_id = int(question_chapter))
							chapter_sql = db.get_last_sql()
							chapter_id = db.get_last_id()
							LOG.info('RES[%s] - INS[%d]' % (chapter_res,chapter_id))
						
					except DBException as e:
						db.rollback()
						db.end_event()
						ret['code'] = 3
						ret['message'] = 'server error'
						LOG.error('ERR[insert mysql error]') 
						break

			else:
				ret['code'] = 3
				ret['message'] = 'server error'
				LOG.error('ERROR[remote error]')
				break
							
			mongo = Mongo()

			try:
				mongo.connect('resource')
				mongo.select_collection('mongo_question_json')
				json_id = mongo.insert_one({"content":encode_json,"question_id":question_id})
				LOG.info('MONGO[insert json] - DATA[%s] - INS[%s]' % (json.dumps(encode_json),json_id))

				mongo.select_collection('mongo_question_html')
				html_id = mongo.insert_one({"content":encode_html,"question_id":question_id})
				LOG.info('MONGO[insert html] - DATA[%s] - INS[%s]' % (json.dumps(encode_html),html_id))

			except DBException as e:
				db.rollback()
				db.end_event()
				ret['code'] = 3 
				ret['message'] = 'server error'
				LOG.error('ERR[mongo exception]') 
				break

			db.end_event()

			ret['code'] = 0
			ret['message'] = 'success'
			ret['id'] = question_id

		LOG.info('PARAMETER OUT[%s]' % ret)
		LOG.info('API OUT[%s]' % (self.__class__.__name__))
		self.write(json.dumps(ret))
		self.finish()


class get_exercises(web.RequestHandler):

    def get(self):

        self.set_header("Access-Control-Allow-Origin", "*")
        enter_func(self)

        if not set(['id']).issubset(self.request.arguments.keys()):
            return leave_func(self, 1)
        question_id = self.request.arguments['id'][0]
        if not question_id.isdigit():
            return leave_func(self, 1)

        try:
            mysql = Mysql().get_handle()
            cursor = mysql.cursor(MySQLdb.cursors.DictCursor)
            sql = 'SELECT question_type, subject_id, difficulty, question_group FROM entity_question WHERE id = %s' % question_id
            LOG.info('mysql> %s' % sql)
            cursor.execute(sql)
            result = cursor.fetchall()
            if not result:
                LOG.error('question_id[%s] nonexistent!' % question_id)
                return leave_func(self, 2)
            level_id      = result[0]['difficulty']
            group_id      = result[0]['question_group']
            question_type = result[0]['question_type']
            subject_id    = result[0]['subject_id']

            # 获取题目类型
            sql = 'SELECT type_id id, name FROM entity_question_type WHERE name = "%s"' % question_type
            LOG.info('mysql> %s' % sql)
            cursor.execute(sql)
            ret = cursor.fetchall()
            if not ret:
                LOG.error('invalid question_type[%s] of question_id[%s]!' % (question_type, question_id))
                return leave_func(self, 100)
            question_type = ret[0]

            # 获取主题
            sql = 'SELECT id, SUBSTRING_INDEX(name, "\n", 1) name FROM entity_topic WHERE id IN (SELECT topic_id FROM link_question_topic WHERE question_id = %s)' % question_id
            LOG.info('mysql> %s' % repr(sql)[1:-1])
            cursor.execute(sql)
            theme_list = list(cursor.fetchall())

#            # 获取专题
#            sql = 'select id, substring_index(name, "\n", 1) name from entity_seriess where id in (select series_id from link_question_series where question_id = %s)' % question_id
#            LOG.info('mysql> %s' % repr(sql)[1:-1])
#            cursor.execute(sql)
#            special_list = list(cursor.fetchall())

            mongo = Mongo().get_handle()
            json_body = mongo.resource.mongo_question_json.find_one( { 'question_id': int(question_id) } )
            if not json_body:
                LOG.error('json body of question_id[%s] is nonexistent in MongoDB.' % question_id)
                return leave_func(self, 2)
            if 'content' in json_body:
                json_body = json_body['content']
            else:
                json_body = {}

            html_body = mongo.resource.mongo_question_html.find_one( { 'question_id': int(question_id) } )
            if not html_body:
                LOG.error('html body of question_id[%s] is nonexistent in MongoDB.' % question_id)
                return leave_func(self, 2)
            if 'content' in html_body:
                html_body = html_body['content']
            else:
                html_body = {}

            chapter_info = []

            sql = 'SELECT chapter_id FROM link_question_chapter WHERE question_id = %s' % question_id
            LOG.info('mysql> %s' % sql)
            cursor.execute(sql)
            ret = cursor.fetchall()
            if ret:
                chapter_id = ret[0]['chapter_id']

                sql = 'SELECT id, level, parent_id, REPLACE(prefix_name, "\r\n", "") prefix_name, REPLACE(name, "\r\n", "") name FROM entity_teaching_chapter WHERE id = %s' % chapter_id
                LOG.info('mysql> %s' % repr(sql)[1:-1])
                cursor.execute(sql)
                ret = cursor.fetchall()
                if not ret:
                    LOG.error('chapter_id[%s] nonexistent!' % chapter_id)
                else:
                    chapter_id  = ret[0]['id']
                    parent_id   = ret[0]['parent_id']
                    prefix_name = ret[0]['prefix_name']
                    name        = ret[0]['name']
                    level       = ret[0]['level']
                    chapter_info.insert(0, { 'id': chapter_id, 'prefix': prefix_name, 'name': name })

                    for i in range(int(level) - 1):
                        sql = 'SELECT id, level, parent_id, REPLACE(prefix_name, "\r\n", "") prefix_name, REPLACE(name, "\r\n", "") name FROM entity_teaching_chapter WHERE id = %s' % parent_id
                        LOG.info('mysql> %s' % repr(sql)[1:-1])
                        cursor.execute(sql)
                        ret = cursor.fetchall()
                        if not ret:
                            break
                        chapter_id  = ret[0]['id']
                        parent_id   = ret[0]['parent_id']
                        prefix_name = ret[0]['prefix_name']
                        name        = ret[0]['name']
                        level       = ret[0]['level']
                        chapter_info.insert(0, { 'id': chapter_id, 'prefix': prefix_name, 'name': name })

            result          = error_process(0)
            result['json']  = json_body
            result['html']  = html_body
            result['type']  = question_type
            result['topic'] = theme_list
            result['level'] = level_id
            result['group'] = group_id
            result['chapter_info'] = chapter_info

            mongo.close()
            cursor.close()
            mysql.close()

            leave_func(self, 0)
            return self.write(json.dumps(result, ensure_ascii=False))
        except Exception, e:
            LOG.error(e)
            return leave_func(self, 100)


class update_exercises(web.RequestHandler):

    def post(self):

        self.set_header("Access-Control-Allow-Origin", "*")

        enter_func(self)

        if not set(['id', 'json', 'html', 'topic', 'level', 'type', 'group', 'chapter']).issubset(self.request.arguments.keys()):
            return leave_func(self, 1)

        theme         = self.request.arguments['topic'][0]
        type_id       = self.request.arguments['type'][0]
        level_id      = self.request.arguments['level'][0]
        group_id      = self.request.arguments['group'][0]
        chapter_id    = self.request.arguments['chapter'][0]
        question_id   = self.request.arguments['id'][0]
        question_json = self.request.arguments['json'][0]
        question_html = self.request.arguments['html'][0]

        try:
            if not (type_id.isdigit() and int(type_id) and level_id.isdigit() and int(level_id) and group_id.isdigit() and question_id.isdigit() and int(question_id) and theme + chapter_id and question_json and question_html):
                return leave_func(self, 1)
            if chapter_id and not chapter_id.isdigit():
                return leave_func(self, 1)

            if Business.is_level(level_id) is False:
                LOG.error('invalid level_id[%s]' % level_id)
                return leave_func(self, 1)

            try:
                question_json = urllib.unquote(question_json)
                encode_json = {}
                encode_json['content'] = json.loads(question_json, encoding = 'utf-8')
                question_html = urllib.unquote(question_html)
                encode_html = {}
                encode_html['content'] = json.loads(question_html, encoding = 'utf-8')
            except:
                traceback.print_exc()
                LOG.error(sys.exc_info())
                return leave_func(self, 100)

            sql_list = []
            if chapter_id:
                sql_list.append('UPDATE link_question_chapter SET chapter_id = %s WHERE question_id = %s' % (chapter_id, question_id)) # 生成更新章节关联信息的SQL

            if theme: # 主题
                sql_list.append('DELETE FROM link_question_topic WHERE question_id = %s' % question_id) # 生成删除原有主题关联的SQL
                for theme_id in theme.split(','): # 将传入的主题号按逗号切割
                    if Business.is_topic(theme_id) is False: # 判断主题号是否存在
                        LOG.error('invalid theme_id[%s]' % theme_id)
                        return leave_func(self, 1)
                    sql_list.append('INSERT INTO link_question_topic (question_id, topic_id) VALUES (%s, %s)' % (question_id, theme_id)) # 生成将新主题关联插库的SQL

            question_type = Business.is_type(type_id)
            if question_type is False: # 判断题目类型是否存在
                LOG.error('invalid type_id[%s]' % type_id)
                return leave_func(self, 1)

            answer_num = 0
            if 'answer' in encode_json['content'].keys():
                if type_id == '1':
                    answer_num = len(encode_json['content']['answer'])
                elif type_id == '2':
                    answer_num = len([int(answer_group['index']) for answer_group in encode_json['content']['answer']])

            sql_list.append('UPDATE entity_question SET difficulty = %s, update_time = now(), question_type = "%s", question_group = %s, answer_num = %s WHERE id = %s' % (level_id, question_type, group_id, answer_num, question_id)) # 生成更新题目属性的SQL

            mysql_handle = Mysql().get_handle()
            mysql_cursor = mysql_handle.cursor(MySQLdb.cursors.DictCursor)
            mysql_cursor.execute('SELECT question_docx, html FROM entity_question WHERE id = %s' % question_id) # 通过题目ID查询存储的json/html文件名
            result = mysql_cursor.fetchall()
            if not result:
                LOG.error('invalid question_id[%s]' % question_id)
                return leave_func(self, 1)

            qiniu = QiniuWrap()
            mongo = Mongo()
            mongo.connect('resource')

            if result[0]['question_docx'] and '.json' in result[0]['question_docx']:
                json_name = result[0]['question_docx']
                # 将七牛上的json文件删除后重新上传
                qiniu.bucket.delete("temp", json_name)
                qiniu.upload_data("temp", json_name, question_json)
                # 将MongoDB中的json文件删除后重新上传
                mongo.select_collection('mongo_question_json')
                LOG.debug('resource.mongo_question_json.remove( { question_id: %s } )' % question_id)
                mongo.remove( { "question_id" : int(question_id) } )
                encode_json['question_id'] = int(question_id)
                LOG.debug('resource.mongo_question_json.insert_one( %s )' % encode_json)
                mongo.insert_one(encode_json)

            if result[0]['html'] and '.html' in result[0]['html']:
                html_name = result[0]['html']
                # 将七牛上的html文件删除后重新上传
                qiniu.bucket.delete("temp", html_name)
                qiniu.upload_data("temp", html_name, question_html)
                # 将MongoDB中的html文件删除后重新上传
                mongo.select_collection('mongo_question_html')
                LOG.debug('resource.mongo_question_html.remove( { question_id: %s } )' % question_id)
                mongo.remove( { "question_id" : int(question_id) } )
                encode_html['question_id'] = int(question_id)
                LOG.debug('resource.mongo_question_html.insert_one( %s )' % encode_html)
                mongo.insert_one(encode_html)

            for sql in sql_list:
                LOG.info(sql)
                mysql_cursor.execute(sql)
            mysql_handle.commit()
            mysql_cursor.close()
            mysql_handle.close()

            leave_func(self, 0)
            self.write(error_process(0))
        except Exception, e:
            LOG.error(e)
            return leave_func(self, 100)


class delete_exercises(web.RequestHandler):
    def get(self):
        enter_func(self)
        if not set(['id']).issubset(self.request.arguments.keys()):
            return leave_func(self, 1)
        id = int(self.request.arguments['id'][0])
        mysql_handle = Mysql().get_handle()
        mysql_cursor = mysql_handle.cursor(MySQLdb.cursors.DictCursor)
        sql = 'UPDATE entity_question SET state = "DISABLED" WHERE id = %d' % id
        LOG.info('mysql> %s' % sql)
        mysql_cursor.execute(sql)
        mysql_handle.commit()
        mysql_cursor.close()
        mysql_handle.close()
        leave_func(self, 0)
        return self.write(error_process(0))


def enter_func(self):
    LOG.debug('%s(%s) ...' % (self.__class__.__name__, json.dumps(self.request.arguments, ensure_ascii=False)))


def leave_func(self, code):
    if 0 == code:
        LOG.debug('%s(%s) ...' % (self.__class__.__name__, json.dumps(self.request.arguments, ensure_ascii=False)))
    else:
        LOG.debug('%s(%s) %s' % (self.__class__.__name__, json.dumps(self.request.arguments, ensure_ascii=False), error_process(code)))
        self.write(error_process(code))


class search_keyword(web.RequestHandler):
    def get(self):
        enter_func(self)
        if not set(['word']).issubset(self.request.arguments.keys()):
            return leave_func(self, 1)
        if 'page_num' in self.request.arguments.keys() and self.request.arguments['page_num'][0]:
            page_num = int(self.request.arguments['page_num'][0])
        else:
            page_num = 1
        if 'page_size' in self.request.arguments.keys() and self.request.arguments['page_size'][0]:
            page_size = int(self.request.arguments['page_size'][0])
        else:
            page_size = 10
        keyword = self.request.arguments['word'][0]
        if 'uid' in self.request.arguments.keys() and self.request.arguments['uid'][0]:
            uid = int(self.request.arguments['uid'][0])
            LOG.info('data_statistics: %s' % {'uid': uid, 'keyword': keyword, 'func': self.__class__.__name__})
        if not keyword or page_num < 1 or page_size < 1:
            return leave_func(self, 1)
        url = 'http://wenku.baidu.com/api/interface/search?%s' % urllib.urlencode({ 'word': keyword, 'pn': page_num, 'rn': page_size, 'token': generate_token(), 'host': host })
        LOG.info(url)
        docs = json.loads(urllib2.urlopen(url).read().decode('raw_unicode_escape'))
        LOG.info(docs)
        if 0 != docs['status']['code']:
            LOG.error(docs['status'])
            return leave_func(self, 100)
        ret = dict(error_process(0).items() + docs['data'].items())
        if 'jsonp' in self.request.arguments.keys():
            jsonp = self.request.arguments['jsonp'][0]
            leave_func(self, 0)
            return self.write('%s(%s)' % (jsonp, json.dumps(ret, ensure_ascii=False)))
        leave_func(self, 0)
        return self.write(json.dumps(ret, ensure_ascii=False))


class get_class(web.RequestHandler):
    def get(self):
        enter_func(self)
        params = { 'token': generate_token(), 'host': host, 'zone': 8 }
        if 'zone' in self.request.arguments.keys() and self.request.arguments['zone'][0].isdigit():
            params['zone'] = int(self.request.arguments['zone'][0])
        redis_handle = redis.Redis(Configer().get_configer('REDIS', 'host'))
        if redis_handle.exists('json_class:%d' % params['zone']):
            leave_func(self, 0)
            return self.write(redis_handle.get('json_class:%d' % params['zone']))
        url = 'http://wenku.baidu.com/api/interface/getclass?%s' % urllib.urlencode(params)
        LOG.info(url)
        ret = json.loads(urllib2.urlopen(url).read().decode('raw_unicode_escape'))
        LOG.info(ret)
        if 0 != ret['status']['code']:
            LOG.error('baidu library interface error: %s' % ret['status'])
            return leave_func(self, 100)
        result = error_process(0)
        result['data'] = ret['data']
        result = json.dumps(result, sort_keys=True, ensure_ascii=False)
        redis_handle.set('json_class:%d' % params['zone'], result)
        leave_func(self, 0)
        return self.write(result)


class get_token(web.RequestHandler):
    def get(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        return self.write(generate_token())


class get_subject(web.RequestHandler):
    def get(self):
        enter_func(self)
        if not set(['subject', 'grade', 'version']).issubset(self.request.arguments.keys()):
            return leave_func(self, 1)
        params = { 'subject': self.request.arguments['subject'][0], 'grade': self.request.arguments['grade'][0], 'version': self.request.arguments['version'][0] }
        if 'unit' in self.request.arguments.keys():
            params['Unite'] = self.request.arguments['unit'][0]
        if 'lesson' in self.request.arguments.keys():
            params['Lesson'] = self.request.arguments['lesson'][0]
        if 'word' in self.request.arguments.keys():
            params['word'] = self.request.arguments['word'][0]
        if 'stype' in self.request.arguments.keys():
            params['stype'] = self.request.arguments['stype'][0]
        if 'order' in self.request.arguments.keys():
            params['order'] = self.request.arguments['order'][0]
        if 'page_num' in self.request.arguments.keys():
            params['pn'] = self.request.arguments['page_num'][0]
        else:
            params['pn'] = 1
        if 'page_size' in self.request.arguments.keys():
            params['rn'] = self.request.arguments['page_size'][0]
        params['token'] = generate_token()
        params['host'] = host
        url = 'http://wenku.baidu.com/api/interface/getsubject?%s' % urllib.urlencode(params)
        LOG.info(url)
        ret = json.loads(urllib2.urlopen(url).read().decode('raw_unicode_escape'))
        LOG.info(ret)
        if 0 != ret['status']['code']:
            LOG.error('baidu library interface error: %s' % ret['status'])
            return leave_func(self, 100)
        ret = dict(error_process(0).items() + ret['data'].items())
        leave_func(self, 0)
        return self.write(json.dumps(ret, ensure_ascii=False))


class doc_download(web.RequestHandler):
    def get(self):
        enter_func(self)
        if not set(['doc_id']).issubset(self.request.arguments.keys()):
            return leave_func(self, 1)
        doc_id = self.request.arguments['doc_id'][0]
        if 'uid' in self.request.arguments.keys():
            uid = self.request.arguments['uid'][0]
            LOG.info('data_statistics: %s' % {'uid': uid, 'doc_id': doc_id, 'func': self.__class__.__name__})
        url = 'http://wenku.baidu.com/api/interface/download?doc_id=%s&token=%s&host=%s' % (doc_id, generate_token(), host)
        LOG.info(url)
        result = error_process(0)
        result['url'] = url
        leave_func(self, 0)
        return self.write(result)


class get_doc_info(web.RequestHandler):
    def get(self):
        enter_func(self)
        if not set(['doc_id']).issubset(self.request.arguments.keys()):
            return leave_func(self, 1)
        doc_id = self.request.arguments['doc_id'][0]
        if 'uid' in self.request.arguments.keys():
            uid = self.request.arguments['uid'][0]
            LOG.info('data_statistics: %s' % {'uid': uid, 'doc_id': doc_id, 'func': self.__class__.__name__})
        url = 'http://wenku.baidu.com/api/interface/getdocinfobyid?doc_id=%s&token=%s&host=%s' % (doc_id, generate_token(), host)
        LOG.info(url)
        ret = json.loads(urllib2.urlopen(url).read().decode('raw_unicode_escape'))
        LOG.info(ret)
        if 0 != ret['status']['code']:
            LOG.error('baidu library interface error: %s' % ret['status'])
            return leave_func(self, 100)
        ret = dict(error_process(0).items() + ret['data'].items())
        leave_func(self, 0)
        return self.write(ret)

