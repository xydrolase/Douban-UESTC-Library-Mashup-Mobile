#!/usr/bin/env python
# encoding: UTF-8
#
# Copyright 2010 killkeeper.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.api import urlfetch
import base64
from config import *
from urllib import urlencode
from main import BaseHandler

UPDATE_API = "%s/statuses/update.json" % TWITTER_API

""" tinytwi.py implements a tiny client for updating and retrieveing Twitter
status through GAE urlfetch API. Administrators of Pixian Douban could push 
updates to assigned twitter client easily.
	
	WARNING: For security consideration, this tiny twitter client portal should 
be configured in app.yaml to be admin only.  """
    
class TwitterHandler(BaseHandler):
    def get(self):
        html = """
        <form method="post" action="/twitter/" name="tweet_form">
        Tweet: <textarea cols="50" rows="4" name="tweet"></textarea>
        <input type="submit" value="Publish" />
        </form>
        """
        self.response.out.write(html)
    
    def uni2utf8(self, raw_string):
    	"""parse the escaped unicode string into a utf encoded string"""
    	uni_string = eval("u'%s'" % raw_string)
    	return uni_string.encode('utf8')
        
    def post(self):
        auth_body = base64.b64encode(':'.join(TWITTER_AUTH))
        
        tweet = self.request.get('tweet').encode('utf8')
        post = {'status': tweet}
        form_data = urlencode(post)
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 
            'Authorization': 'Basic %s' % auth_body }   
        
        result = urlfetch.fetch(url=UPDATE_API,
                        payload=form_data,
                        method=urlfetch.POST,
                        headers=headers)
        
        self.response.out.write(result.content)       
        
def main():
  application = webapp.WSGIApplication([
    ('/twitter/', TwitterHandler),
  ], debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()