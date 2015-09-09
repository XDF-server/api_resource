#!/usr/bin/python2.7
# *-* coding:utf-8 *-* 

import os
import sys
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define,options
from loader import Loader

define('port',default = 9000,help='this is default port',type = int)

if __name__ == "__main__":
	
	Loader.load()

	from gl import LOG
	from question import UploadQuestion, get_exercises, update_exercises, search_keyword
	from transcode import Transcode,TranscodeRes
	from group import CreateGroup,GetGroupList
	from approve import UpToken
	
	tornado.options.parse_command_line()

	application = tornado.web.Application([
		(r'/api/upload_question',UploadQuestion),
        	(r'/api/get_exercises', get_exercises),
        	(r'/api/update_exercises', update_exercises),
        	(r'/api/search_keyword', search_keyword),
		(r'/api/create_group',CreateGroup),
		(r'/api/get_group_list',GetGroupList),
		(r'/api/uptoken',UpToken),
		(r'/api/transcode',Transcode),
		(r'/api/transcode_res',TranscodeRes),
	])

	http_server = tornado.httpserver.HTTPServer(application)

        http_server.listen(options.port)

	LOG.info('idc_api is started,port is [%s]' % options.port)

        tornado.ioloop.IOLoop.instance().start()

