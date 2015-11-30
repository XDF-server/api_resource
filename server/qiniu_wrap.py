# *-* coding:utf-8 *-* 
import qiniu
from qiniu import Auth,BucketManager
from qiniu import PersistentFop,op_save,put_file,put_data
import urllib2
from base import Configer
import os
from design_model import singleton

@singleton
class QiniuWrap(object):

	def __init__(self):
		
		configer = Configer('')

		access_key = configer.get_configer('QINIU','access_key')
		secret_key = configer.get_configer('QINIU','secret_key')

		self.q=Auth(access_key,secret_key)
		self.bucket = BucketManager(self.q)
	
	def transcode_h264(self,bucket_name,key):

		file_tail = ['ori.mp4','.mp4']
	
		for type in file_tail:
		
			des_filename = key.replace(type,'h264.mp4')

			if des_filename is not None:
				break

		op=op_save('avthumb/mp4/ab/32k/aq/10/ar/44100/acodec/libfaac/r/25/vb/260k/vcodec/libx264/s/640x360/autoscale/1/stripmeta/0',bucket_name,des_filename)

		ops = []
		ops.append(op)
		self.pfop=PersistentFop(self.q,bucket_name,'videoconverth264')
		ret,info = self.pfop.execute(key,ops,1)

		if 200 == info.status_code:
			return 0
		else:
				
			return info.text_body[10:-2]

        def download_pub_file(self,bucket_name,key,path='.'):

                base_url = 'http://%s.okjiaoyu.cn/%s' % (bucket_name,key)
                request = urllib2.Request(base_url)
                response = urllib2.urlopen(request)
                pic = response.read()

                with open(path + '/' + key,'wb') as fd:
                        fd.write(pic)

                return response.code

        def download_pri_file(self,bucket_name,key):

                base_url = 'http://%s.okjiaoyu.cn/%s' % (bucket_name,key)
                private_url = q.private_download_url(base_url,expires = 3600)
                request = urllib2.Request(base_url)
                response = urllib2.urlopen(request)
                pic = response.read()

                with open(path + '/' + key,'wb') as fd:
                        fd.write(pic)

                return response.code

	def upload_file(self,bucket_name,key,localfile):

		if bucket_name is None or key is None or localfile is None:
			return 'sys error'

		token = self.q.upload_token(bucket_name,key)

		ret,info = put_file(token,key,localfile)

		if 200 == info.status_code:
			return None
		else:
			return info.text_body[10:-2]
	def upload_data(self,bucket_name,key,data):

		if bucket_name is None or key is None or data is None:
			return 'sys error'

		token = self.q.upload_token(bucket_name,key)

		ret,info = put_data(token,key,data)

		if 200 == info.status_code:
			return True
		else:
			return False


        def get_file_info(self,bucket_name,key):
                bucket_name = bucket_prex + bucket_name
                ret, info = bucket.stat(bucket_name, key)
                return info

        def copy_file(self,frm_bucket_name,frm_key,to_bucket_name,to_key):
                frm_bucket_name = bucket_prex + frm_bucket_name
                to_bucket_name = bucket_prex + to_bucket_name
                ret, info = bucket.copy(frm_bucket_name, frm_key, to_bucket_name, to_key)
                return ret

        def move_file(self,frm_bucket_name,frm_key,to_bucket_name,to_key):
                frm_bucket_name = bucket_prex + frm_bucket_name
                to_bucket_name = bucket_prex + to_bucket_name
                ret, info = bucket.move(frm_bucket_name, frm_key, to_bucket_name, to_key2)
                return ret
        
        def del_file(self,bucket_name,key):
        	bucket_name = bucket_prex + bucket_name
                ret, info = bucket.delete(bucket_name, key)
                return ret

	def get_uptoken(self,bucket_name,key):
			
		return self.q.upload_token(bucket_name,key)
 		
	def list_bucket(self,bucket_name):
		marker = None
		eof = False
		
		while eof is False:
			ret, eof, info = self.bucket.list(bucket_name, prefix=prefix, marker=marker, limit=limit)
			marker = ret.get('marker', None)

			for item in ret['items']:
				print(item['key'])
				pass

			if eof is not True:
				# 错误处理
				pass               
                        
if __name__ == '__main__':
       	aa = QiniuWrap()
	#print aa.transcode_h264('fs-rv','rv_hOsImw4283.ori.mp4')
	#print aa.upload_file('temp','tmp_12345','server.py')




