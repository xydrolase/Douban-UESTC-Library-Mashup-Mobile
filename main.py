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
import douban.service
from library import *
import os, re
from config import *

client = douban.service.DoubanService(server=SERVER,
                    api_key=API_KEY,secret=SECRET)
                    
pager_re = re.compile('\&index=\d+')
                    
ATTR2NAME = {'price': '价格', 'publisher': '出版社', 'pubdate':'出版时间', 'translator': '译者'}

class BaseHandler(webapp.RequestHandler):
    def template_path(self, filename):
        """Returns the full path for a template from its path relative to here."""
        return os.path.join('templates', filename)

    def render_to_response(self, filename, template_args):
        """Renders a Django template and sends it to the client.
    
        Args:
          filename: template path (relative to this file)
          template_args: argument dict for the template
        """
        user = users.get_current_user()
        user_logined = True if user else False
        
        uri = re.sub('\&index\=\d+', '', self.request.uri)
        
        template_args.setdefault('current_uri', uri)
        template_args.setdefault('user_login', user_logined)
        template_args.setdefault('user', user)
        template_args.setdefault('login_url', users.create_login_url(self.request.uri))
        template_args.setdefault('logout_url', users.create_logout_url('/'))
        
        self.response.out.write(
            template.render(self.template_path(filename), template_args)
        )

class MainHandler(BaseHandler):
    def get(self):
        self.render_to_response('index.html', {})

class ReservationHandler(BaseHandler):
    def get(self, isbn):
        key = '_'.join(['libdb', isbn])
        blob = memcache.get(key)
        
        if not blob:
            # our cache expires...
            referer = self.request.headers.get('Referer', '/')
            self.redirect(referer)  # jump to previous link
        
        
        inq_no = blob.books[0]['inq_no'] if blob.book_count else None
        self.render_to_response('loc.html', {'entry': blob, 'inq_no': inq_no})

class SearchHandler(BaseHandler):
    def get(self):
        method = self.request.get("method")
        keyword = self.request.get("keywords").encode("utf8")
        index = self.request.get("index")
        if not index: 
            index = 0 
        else: 
            index = int(index)
        
        libm = LibraryMashup()
            
        if method == 'isbn':
            uri = '/book/subject/isbn/%s' % keyword
        elif method == 'keyword':
            feed = client.SearchBook(keyword, max_results=5, start_index=index)
            
        lower_bound = index - 20
        if lower_bound < 0: lower_bound = 0
        upper_bound = int(feed.total_results.text) if index + 25 > int(feed.total_results.text) else index + 25
        
        pager = range(lower_bound, upper_bound, 5)
        isbn_group = []
        if len(feed.entry):
            for bk in feed.entry:
                # hack the structure of feed by inserting some content into it
                bk.isbn = [attr.text for attr in bk.attribute if attr.name in ('isbn10', 'isbn13')]
                bk.isbn_string = "-".join(bk.isbn)
                bk.author_list = ', '.join([author.name.text for author in bk.author])
                attr_list = []
                for attr in bk.attribute:
                    if attr.name in ATTR2NAME:
                        attr_list.append( '<span class="tag">%s</span>: %s' % (ATTR2NAME[attr.name], attr.text) )
                
                bk.attributes = ' / '.join(attr_list)
                isbn_group.append(bk.isbn_string)   # prepare the search entries
                
                
            # now search by once for all entries...
            isbn = ','.join(isbn_group)
            result_list = libm.query(isbn)
            
            for x in range(len(result_list)):
                bk = feed.entry[x]
                bk.book_count, bk.book_available, bk.books = result_list[x]
                cache_blob(bk) # write to cache
            
            self.render_to_response('query.html', {'feed': feed, 'keyword': keyword, 'index': int(index), 'pager': pager})
        else:
            self.render_to_response('query.html', {'feed': feed, 'keyword': keyword, 'index': int(index), 'pager': pager})

def cache_blob(entry):
    key = '_'.join(['libdb', entry.isbn_string])
    memcache.add(key, entry, 1800)  # 30 min of caching

def main():
  application = webapp.WSGIApplication([
    ('/', MainHandler),
    ('/q/', SearchHandler ),
    ('/loc/(.+)', ReservationHandler)
    #('/mine/', UserHandler),
  ], debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
