# *-* coding:utf-8 *-*

import MySQLdb 
from base import Base
from exception import DBException
from base import Base
from gl import LOG
from design_model import singleton
from base import Configer

@singleton
class Mysql(object):

	def __init__(self):
	
		self.conn = None
		self.cur = None
		self.sql = ''
		self.status_enum = Base.enum(CONN_SUC = 0,CONN_ERR= -1,QUERY_SUC = 1,QUERY_ERR = -2,QUERY_WAR = 2,EVENT_SUC = 3,EVENT_ERR = -3,OTHER_ERR = -4)
		self.status = 0
		self.event_flag = False
		self.connect_flag = False
	
	def connect_master(self):

		if self.connect_flag:
			self.cur.close()
			self.conn.close()		
			self.connect_flag = False

		configer = Configer()
	
		host = configer.get_configer('MYSQL','host')
		port = configer.get_configer('MYSQL','port')
		user = configer.get_configer('MYSQL','user')
		passwd = configer.get_configer('MYSQL','passwd')
		db = configer.get_configer('MYSQL','db')
		charset = configer.get_configer('MYSQL','charset')
		timeout = configer.get_configer('MYSQL','timeout')

		try:
			self.conn = MySQLdb.connect(
					host = host,
					port = int(port),
					user = user,
					passwd = passwd,
					db = db,
					charset = charset,
					connect_timeout = int(timeout))
			
			self.cur = self.conn.cursor()
			self.query('set autocommit=1;')

			self.connect_flag = True

		except MySQLdb.Error,e:
			self.status = self.status_enum.CONN_ERR
			msg = 'connect failed'
			LOG.error('Error:%s' % str(e))
			raise DBException(msg)

	def start_event(self):
		self.query('set autocommit=0;')
		self.query('begin;')
		self.event_flag = True

	def exec_event(self,sql,**kwds):

		if self.event_flag:
			res = self.query(sql,**kwds)
			return res

		else:
			self.status = self.status_enum.EVENT_ERR
			raise DBException('event failed')

	def end_event(self):
		
		if self.event_flag:
			self.commit()
			self.event_flag = False
			self.query('set autocommit=1;')

	def get_last_id(self):

		return int(self.conn.insert_id())

	def get_status(self):
		
		return self.status
	
	def commit(self):
		
		self.conn.commit()

	def rollback(self):

		self.conn.rollback()

	def query(self,sql,**kwds):

		self.cur.execute("show variables like 'autocommit';")
		flag = self.cur.fetchone()
		LOG.info(flag)
		
		try:
			self.sql = sql % kwds
			LOG.info('execute SQL[%s]' % (self.sql))
			self.cur.execute(self.sql)	

		except MySQLdb.Warning,w:
			LOG.warn('Warning:%s' % str(w))
			self.status = self.status_enum.QUERY_WAR

		except MySQLdb.Error,e:
			self.rollback()
			self.event_flag = False
			LOG.error('Error:%s' % str(e))
			self.status = self.status_enum.QUERY_ERR
			raise DBException('query failed')
		
		except:
			self.status = self.status_enum.OTHER_ERR
			LOG.error('format failed')
			raise DBException('format failed')
	
		if self.cur.rowcount:
		
			return True
		
		else:
			return False

	def fetch(self):
		
		return self.cur.fetchone()

	def fetchall(self):
		
		return self.cur.fetchall()


	def get_last_sql(self):
				
		return self.sql

	def __def__(self):
		self.cur.close()
		self.conn.close()

        def get_handle(self):
                return MySQLdb.connect(host = Configer().get_configer('MYSQL', 'host'), user = Configer().get_configer('MYSQL', 'user'), passwd = Configer().get_configer('MYSQL', 'passwd'), db = Configer().get_configer('MYSQL', 'db'), port = int(Configer().get_configer('MYSQL', 'port')), charset = Configer().get_configer('MYSQL', 'charset'))
