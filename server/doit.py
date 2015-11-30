# *-* coding:utf-8 *-*

from base import Configer
from design_model import singleton
import os

@singleton
class Doit(object):
	
	def __init__(self):
			
		self._read_config()
		self.pipe_fd = os.open(self.pipe_file,os.O_NONBLOCK | os.O_CREAT | os.O_RDWR)

	def _read_config(self):

		configer = Configer('../config.ini')
		self.pipe_file = configer.get_configer('QUEUE','PIPE_FILE')
	
	def write(self,data):

		data = "write(" + data + ")"
		os.write(self.pipe_fd,data)

	def transcode(self,filepath):
		
		data = "transcode(" + filepath + ")"
		os.write(self.pipe_fd,data)

	def local_img(self,question_id):
		
		data = "local_img(" + question_id + ")"
		os.write(self.pipe_fd,data)

	def kill(self):
		
		data = "kill()"
		os.write(self.pipe_fd,data)

	def __del__(self):

		os.close(self.pipe_fd)

if __name__ == '__main__':
	#do = Doit()
	#do.transcode('/home/work/mmpeg/fjdslfjdsf.mp4')
	do = Doit()
	#do.kill()
	do.local_img('1401043')
	#do.transcode('/home/work/mmpeg/fjdslfjdsf.mp4')
	#do.transcode('/home/work/mmpeg/fjdslfjdsf.mp4')
	#do.transcode('/home/work/mmpeg/fjdslfjdsf.mp4')
	#do.transcode('/home/work/mmpeg/fjdslfjdsf.mp4')
