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

class UpToken(web.RequestHandler):

	def post(self):

		for i in range(1):
	
			LOG.info('API IN[%s]' % (self.__class__.__name__))
                        LOG.info('PARAMETER IN[%s]' % self.request.arguments)

                        ret = {'code':'','message':'','uptoken':-9999}

                        essential_keys = set(['bucket','key','timestamp','secret'])

                        if Base.check_parameter(set(self.request.arguments.keys()),essential_keys):
                                ret['code'] = -5
                                ret['message'] = 'parameter is wrong'
                                break

                        bucket_name = ''.join(self.request.arguments['bucket'])
                        key = ''.join(self.request.arguments['key'])
                        timestamp = ''.join(self.request.arguments['timestamp'])
                        secret = ''.join(self.request.arguments['secret'])

                        key = bucket_name + key + timestamp
                        secret_key = sha1(key).hexdigest()

			#if secret == secret_key:
			
			qiniu = QiniuWrap()

			uptoken = qiniu.get_uptoken(bucket_name,key)

			ret['code'] = 0
			ret['message'] = 'success'
			ret['uptoken'] = uptoken
			'''
			else:
				ret['code'] = -1
                                ret['message'] = 'secure key error'
			'''
		LOG.info('PARAMETER OUT[%s]' % ret)
                LOG.info('API OUT[%s]' % (self.__class__.__name__))
                self.write(json.dumps(ret))
