# *-* coding:utf-8 *-*

from base import Base
from base import Logger
from base import Configer

class Loader(object):
	
	@staticmethod
	def load():

		configer = Configer('../config.ini')

		log_info = configer.get_configer('LOG','info')
		log_path = configer.get_configer('LOG','path')
		log_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s'

		logger = Logger(info = log_info,path = log_path,format = log_format)
		LOG = logger.get_logger()
			
		from mongo import Mongo

		mongo = Mongo()

		mongo.connect('resource')

		from mysql import Mysql

		mysql = Mysql()

		mysql.connect_master()

		from qiniu_wrap import QiniuWrap

		qiniu = QiniuWrap
		

