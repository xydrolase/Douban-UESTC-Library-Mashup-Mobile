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
import douban.service
from library import *
import os, re, pickle, base64
from config import *
from models import *	# import Datastore models
from gdata.service import RequestError
import urllib

client = douban.service.DoubanService(server=SERVER,
                    api_key=API_KEY,secret=SECRET)
                    
pager_re = re.compile('\&index=\d+')
douban_re = re.compile('www.douban.com')
                    
ATTR2NAME = {'price': '价格', 'publisher': '出版社', 'pubdate':'出版时间', 'translator': '译者'}

ERR_URLFETCH_FAILED = 1
ERR_ENTRY_NOT_FOUND = 2

class BaseHandler(webapp.RequestHandler):
    ERR_INFO = {
                ERR_URLFETCH_FAILED: '无法读取图书馆馆藏信息',
                ERR_ENTRY_NOT_FOUND: '无法找到您指定的条目或内容'
            }
    
    def back(self):
        """Redirect to the previous page the client was browsing"""
        referer = self.request.headers.get('Referer', '/')
        self.redirect(referer)
    
    def terminate(self, errno):
        """Renders error information to client"""
        err_info = self.ERR_INFO.get(errno, '未知的程序错误')
        referer = self.request.headers.get('Referer', None)
        self.render_to_response('error.html', {'error': err_info, 'referer':referer})
        
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
        
        # remove the indexing parameter
        uri = re.sub('\&index\=\d+', '', self.request.uri)
        
        template_args.setdefault('current_uri', uri)
        template_args.setdefault('user_login', user_logined)
        template_args.setdefault('user', user)
        template_args.setdefault('login_url',
            users.create_login_url(self.request.uri))
        template_args.setdefault('logout_url', users.create_logout_url('/'))
        
        self.response.out.write(
            template.render(self.template_path(filename), template_args)
        )

class MainHandler(BaseHandler):
    def get(self):
        self.render_to_response('index.html', {})

class AboutHandler(BaseHandler):
    def get(self):
        self.render_to_response('about.html', {})

class DebugHandler(BaseHandler):
    def get(self):
        from google.appengine.api import mail
        
        libul = LibraryUserList('barcode', 'pin', user_api=LIBRARY_USER_API, query_api=LIBRARY_QUERY_API)
        user_list, newly_borrowed, returned = libul.check_updates({})

        self.render_to_response('debug.html', {'title': 'User List Debug', 'debug': repr(user_list)})

class ReservationHandler(BaseHandler):
    """Retrieve books reservation status from library"""
    def get(self, isbn):
        key = '_'.join(['libdb', isbn])
        blob = memcache.get(key)
        
        if not blob:
            # Cache expires
            try:
                libm = LibraryMashup(api=LIBRARY_QUERY_API)
                uri = "/book/subject/isbn/%s" % isbn.split('-')[0]
                blob = client.GetBook(uri)
                if blob and blob.title.text:
                    hack_gdata(blob)
                    
                    result = libm.query(blob.isbn_string)
                    # if result is None, it means we encounter some errors
                    if not result:
                        self.terminate(ERR_URLFETCH_FAILED)
                        return
                        
                    blob.book_count, blob.book_available, book.books = result[0]
                    cache_blob(blob)	# write blob into cache
            except RequestError:
                self.render_to_response('query.html', {'feed': None, 'keyword': keyword, 'index': 0, 'pager': None})    # render a "not found" page 
                return
        
        inq_no = blob.books[0]['inq_no'] if blob.book_count else None
        # get the where the book locates, and the category of the book
        blob.floor, blob.category = parse_index(inq_no)
        
        user = users.get_current_user()
        task = BookTask.all().filter('user = ', user)\
                .filter('index = ', inq_no).get() if user else None
        
        self.render_to_response('loc.html', {'entry': blob, 'inq_no': inq_no, 'task': task})

class CollectionHandler(BaseHandler):
    """Handles reqeusts for updating users' borrowing collections"""
    def get(self, param):
        """GET /collect|remove/ISBN
        
        Creates or deletes an entry in user's collection with specific ISBN	
        """
        req_path = self.request.path
        if req_path.startswith("/collect/"):
            self.collect(param)
        elif req_path.startswith("/remove/"):
            self.remove(param)
    
    def post(self):
        """POST /collect|remove/
        POST BODY: ?
        """
        
        pass
            
    def remove(self, isbn):
        user = users.get_current_user()
        isbn = isbn.split('-')[0].strip()
        if not isbn or not user:
            self.back()
            return
        
        task = BookTask.all().filter('user = ', user).filter('isbn = ', isbn).get()
        if task:
            # found the matching instance
            task.delete()
            
            # update the tasklist counter
            tasklist = TaskList.all().filter('user = ', user).get()
            if not tasklist:
                tasklist = TaskList(user = user, count = 1) # starts with 1 since we need to minus 1 later
            
            tasklist.count -= 1
            tasklist.put()  # update the counter
        
            self.redirect("/mine/") # redirect back to user's page
        else:
            self.terminate(ERR_ENTRY_NOT_FOUND)
        
        
    def collect(self, isbn):
        user = users.get_current_user()
        key = '_'.join(['libdb', isbn])
        blob = memcache.get(key)
    
        if not blob or not user: # our cache expires...
            self.back()
            return
        
        inq_no = blob.books[0]['inq_no']
        
        # check for duplicitity
        task = BookTask.all().filter('user = ', user).filter('index = ', inq_no).get()
        if task:
            self.back() # found duplicate element... -.-
            return
        
        # retrieve the tasklist, increase the counter
        tasklist = TaskList.all().filter('user = ', user).get()
        if not tasklist:
            tasklist = TaskList(user = user, count = 0)
        
        tasklist.count += 1
        tasklist.put()
        
        # insert a new booktask record into datastore
        BookTask(user=user,
            blob=pickle.dumps(blob),
            index=inq_no,
            isbn=isbn.split('-'),
            tasklist=tasklist).put()	
    
        self.redirect("/mine/")

class MineHandler(BaseHandler):
    def get(self):
        user = users.get_current_user()
        if not user: 
            self.back()
            return
        
        tasklist = TaskList.all().filter('user = ', user).get()
        if tasklist and tasklist.count:
            libm = LibraryMashup(api=LIBRARY_QUERY_API)
            books = []
            isbn_group = []
            for task in tasklist.tasks:
                book = pickle.loads(task.blob)	# deserilize the blob
                book.index = task.index	# indexing number
                # task.isbn stores as string list
                isbn_group.append("-".join(task.isbn))
                book.floor, book.category = parse_index(book.index)
                books.append(book)
            
            isbn_query = ",".join(isbn_group)
            result_list = libm.query(isbn_query)
            
            # if result is None, it means we encounter some errors
            if not result_list:
                self.terminate(ERR_FAILED_URLFETCH)
                return
            
            # update the book's reservation information
            for x in range(len(result_list)):
                bk = books[x]
                bk.book_count, bk.book_available, bk.books = result_list[x]
                cache_blob(bk)  # write to cache
        
            self.render_to_response("mine.html", {'task_count': tasklist.count, 'books': books})
        else:
            self.render_to_response("mine.html", {'task_count': 0, 'books': None}) 

class SearchHandler(BaseHandler):
    def get(self):
        method = self.request.get("method")
        keyword = self.request.get("keywords").encode("utf8")
        index = self.request.get("index")
        if not index: 
            index = 0 
        else: 
            index = int(index)
        
        libm = LibraryMashup(api=LIBRARY_QUERY_API)
            
        if method == 'isbn':
            uri = '/book/subject/isbn/%s' % keyword
            try:
                entry = client.GetBook(uri)
                if entry and entry.title.text:
                    hack_gdata(entry)
                    result = libm.query(entry.isbn_string)
                    
                    if not result: # if result is None, it means we encounter some errors
                        self.terminate(ERR_FAILED_URLFETCH)
                        return
                        
                    entry.book_count, entry.book_available, entry.books = result[0]
                    cache_blob(entry)
                    self.redirect("/loc/%s" % entry.isbn_string)    # jump to the details page
            except RequestError:
                self.render_to_response('query.html', {'feed': None, 'keyword': keyword, 'index': 0, 'pager': None})    # render a "not found" page         
        elif method == 'keyword':
            feed = client.SearchBook(keyword, max_results=5, start_index=index)
            pager = page_indexer(0, int(feed.total_results.text), index=index)
            
        elif method == 'tag':
            feed = client.QueryBookByTag(keyword, max_results=5, start_index=index)
            pager = page_indexer(0, int(feed.total_results.text), index=index)
        
        if method in ('keyword', 'tag'):
            isbn_group = []
            if len(feed.entry):
                for bk in feed.entry:
                    # hack the structure of feed by inserting some content into it
                    hack_gdata(bk)
                    isbn_group.append(bk.isbn_string)   # prepare the search entries
                    
                # now search by once for all entries...
                isbn = ','.join(isbn_group)
                result_list = libm.query(isbn)
                
                if not result_list: # if result is None, it means we encounter some errors
                    self.terminate(ERR_URLFETCH_FAILED)
                    return
                
                for x in range(len(result_list)):
                    bk = feed.entry[x]
                    bk.book_count, bk.book_available, bk.books = result_list[x]
                    cache_blob(bk) # write to cache
                    
            self.render_to_response('query.html', 
                    {'feed': feed,  'keyword': keyword, 
                    'index': int(index), 'pager': pager})

def hack_gdata(entry):
    entry.isbn = [attr.text for attr in entry.attribute \
        if attr.name in ('isbn10', 'isbn13')]
    entry.isbn_string = "-".join(entry.isbn)
    entry.author_list = ', '.join([author.name.text for author in entry.author])
    
    for link in entry.link:
        if link.rel == 'alternate':
            # replace the standard douban URL to mobile URL
            link.href = re.sub('www.douban.com/subject/', 'm.douban.com/book/subject/', link.href)
    
    attr_list = []
    for attr in entry.attribute:
        if attr.name in ATTR2NAME:
            attr_list.append( '<span class="tag">%s</span>: %s' %\
                 (ATTR2NAME[attr.name], attr.text) )
    
    entry.attributes = ' / '.join(attr_list)

def page_indexer(start, end, index=0, step=5):
    lower_bound = index - 20
    if lower_bound < 0: lower_bound = 0
    upper_bound = end if index + 25 > end else index + 25
    
    return range(lower_bound, upper_bound, step)

def cache_blob(entry):
    key = '_'.join(['libdb', entry.isbn_string])
    memcache.set(key, entry, 3600)  # 1 hour of caching

def main():
  application = webapp.WSGIApplication([
    ('/', MainHandler),
    ('/q/', SearchHandler ),
    ('/loc/(.+)', ReservationHandler),
    ('/about/', AboutHandler),
    ('/collect/(.+)', CollectionHandler),
    ('/remove/(.+)', CollectionHandler),
    ('/mine/', MineHandler),
    ('/userlist/', DebugHandler)
  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()