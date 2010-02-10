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

import urllib2
from urllib import urlencode
from HTMLParser import HTMLParser
import re
import base64

STATE_LOC = 1
STATE_INQ_NO = 2
STATE_STATUS = 3
STATE_BARCODE = 4
STATE_RESERVED = 5

INDEX_2_FLOOR = {'T':2, 'U':2, 'V':2, 'X':2,
                'A':3, 'B':3, 'C':3, 'D':3, 'E':3, 'F':3, 'G':3, 'H':3,
                'I':4, 'J':4, 'K':4, 'O':4, 'P':4, 'Q':4, 'R':4, 'S':4, 'Z':4}
                
INDEX_2_CATEGORY = {'T':'工业技术','TB':'一般工业技术','TD':'矿业工程','TE':'石油, 天然气工业','TF':'冶金工业','TG':'金属学与金属工业','TH':'机械. 仪表工业','TJ':'武器工业','TK':'能源与动力工程','TL':'原子能技术','TM':'电工技术','TN':'无线电电子学, 电信技术','TP':'自动化技术, 计算机技术','TQ':'化学工业','TS':'轻工业, 手工业','TU':'建筑科学','TV':'水利工程','U':'交通运输','V':'航空航天','X':'环境科学, 安全科学','C':'社会科学总论','D':'政治, 法律','E':'军事','F':'经济','G':'文化, 科学, 教育, 体育','H':'语言, 文学','A':'马列主义, 毛泽东思想, 邓小平理论','B':'哲学, 宗教','C':'社会科学总论','I':'文学','J':'艺术','K':'历史, 地理','O':'数理科学和化学','P':'天文学, 地球科学','Q':'生物科学','R':'医药, 卫生','S':'农业科学','Z':'综合性图书'}

idx_re = re.compile('([A-Z]+)\d+(\.\d+)?')

def parse_index(idx):
    if idx:
        srch = idx_re.search(idx)
        if srch:
            prefix = idx_re.search(idx).groups()[0]
        else:
            # not a valid indexing number
            return None, None
            
        floor = INDEX_2_FLOOR.get(idx[0], None)	# use initial to get floor
        category = INDEX_2_CATEGORY.get(prefix, None)
        
        return floor, category        
    else:
        return None, None

class Stack:
    def __init__(self, initial=None):
        self._stack = []
        self.count = 0
        
        if initial:
            self._stack.extend(initial)
            self.count = len(self._stack)
            
    def push(self, val):
        self.count += 1
        self._stack.append(val)
        
    def pop(self):
        if not self.count:
            return None
        
        val = self._stack.pop()
        self.count -= 1
        return val
        
    def top(self):
    	if self.count == 0:
    		return None
        return self._stack[self.count - 1]
        
    def truncate(self):
        self._stack = []
        self.count = 0

class UserListParser(HTMLParser):
    """Parse the HTML body of specific user's borrowing list"""
    def initialize(self):
        self.stack = Stack()
        self.user_list = []
        self.book = {}
        
    def handle_starttag(self, tag, attrs):
        if tag == 'tr' and ('class', 'patFuncEntry') in attrs:
            self.stack.push('tr.patFuncEntry')
            return
        elif tag == 'td' and self.stack.top() == 'tr.patFuncEntry':
            td_class = self.get_attr('class', attrs)
            if td_class in ('patFuncMark', 'patFuncTitle', 'patFuncBarcode', 'patFuncStatus', 'patFuncCallNo'):
                self.stack.push(".".join([tag, td_class]))
                return
        elif tag == 'input' and self.stack.top() == 'td.patFuncMark':
            self.book.setdefault('renew_id', self.get_attr('value', attrs))
        elif tag == 'a' and self.stack.top() == 'td.patFuncTitle':
            self.book.setdefault('entry', self.get_attr('href', attrs))
        
        self.stack.push(tag)
        
    def handle_endtag(self, tag):
        if tag == 'tr' and self.stack.top() == 'tr.patFuncEntry':
            self.user_list.append(dict(self.book))
            self.book = {} # reset 
        
        self.stack.pop()
        
    def handle_data(self, data):
        if self.stack.top()[:3] == 'td.':
            td, td_class = self.stack.top().split('.')
            data = data.strip()
            
            if td_class in ('patFuncBarcode', 'patFuncStatus', 'patFuncCallNo'):
                tag = td_class[7:].lower()
                self.book.setdefault(tag, data)
                
    def get_attr(self, name, attrs):
        for attr_name, value in attrs:
            if name == attr_name:
                return value
                
        return None

class LibISBNParser(HTMLParser):
    def initialize(self):
        self.isbn = ''
        self.state = None
        self.stack = Stack()
        self.r_field_tag = re.compile('fieldtag\=(\w)')
        
    def handle_starttag(self, tag, attrs):
        if tag == 'td' and ('class', 'bibInfoData') in attrs:
            self.stack.push("td.bibInfoData")
            return
            
        self.stack.push(tag)
        
    def handle_comment(self, data):
        srch = self.r_field_tag.search(data)
        if srch.groups():
            self.state = srch.groups()[0]
            
    def handle_data(self, data):
        if self.stack.top() == 'td.bibInfoData' and self.state == 'i':
            data = data.strip()
            pos = data.find('CNY')
            if pos > -1:
                self.isbn = re.sub('-', '', data[:pos-1])
        
    def handle_endtag(self, tag):
        self.stack.pop()
        
class LibReservParser(HTMLParser):
    """Parse the reservation information (represented in HTML), and generates metadata for specific books"""
    STATES = {'field 1': STATE_LOC, 'field C': STATE_INQ_NO, 'field %': STATE_STATUS, 'field b': STATE_BARCODE, 'field !': STATE_RESERVED }
    
    tr_start = False
    state = STATE_RESERVED
    books = []
    entry = []
    count = 0
    available = 0
    
    def initialize(self):
        self.books = []
        self.entry = []
        self.count = 0
        self.available = 0
    
    def handle_starttag(self, tag, attrs):
        if tag == 'tr' and ('class', 'bibItemsEntry') in attrs:
            # this indicates a <tr> body containing the book information
            self.count += 1
            self.tr_start = True
            
    def handle_endtag(self, tag):
        if tag == 'tr' and self.tr_start:
            self.tr_start = False
            if self.entry:
                self.books.append(self.entry)
                self.entry = []   # reset the book list
    
    def handle_comment(self, data):
        data = data.strip()
        self.state = self.STATES.get(data, STATE_RESERVED)
    
    def handle_data(self, data):
        data = data.strip()
        if not data: return # ignore empty data
    
        if self.state == STATE_STATUS:
            if data == '可借':
                self.available += 1
            
            self.entry.append( ('available', data) )
        elif self.state == STATE_LOC:
            self.entry.append( ('loc', data) )
        elif self.state == STATE_INQ_NO:
            self.entry.append( ('inq_no', data))
        elif self.state == STATE_BARCODE:
            self.entry.append( ('barcode', data))

class LibraryUserList:
    def __init__(self, barcode, password, user_api='', query_api=''):
        self.USER_API_ENTRY = user_api
        self.QUERY_API_ENTRY = query_api
        
        self.barcode = barcode.strip()
        self.password = password.strip()
        self.authbody = None
        self.user_parser = UserListParser()
        self.isbn_parser = LibISBNParser()
        
        if self.barcode and self.password:
            self.authbody = base64.b64encode("%s:%s" % (self.barcode, self.password))
    
    def get_user_list(self):
        if not self.authbody:
            return None
            
        response = self.post(self.USER_API_ENTRY, [('auth', self.authbody)])
                    
        self.user_parser.initialize()
        self.user_parser.feed(response)
        
        return self.user_parser.user_list
    
    def retrieve_isbn(self, user_list):
        """Retrieve corresponding ISBN number for books in the borrowing list.
        Since ISBN is utilized as the unique 'KEY' in identifying and locating book on Douban,
        we need to map the Call Numbers to ISBN serial number."""
        
        callno_list = [book['callno'] for book in user_list if 'callno' in book]
        callno_concat = ",".join(callno_list)
        response = self.post(self.QUERY_API_ENTRY, [('callno', callno_concat),
            ('meta', 1)])
        
        isbn_dict = {}
        response_group = response.split('<split />')
        if response_group and len(response_group):
            for idx in range(len(response_group)):
                self.isbn_parser.initialize()
                self.isbn_parser.feed(response_group[idx])
                _isbn = self.isbn_parser.isbn
                user_list[idx].setdefault('isbn', _isbn)
                
                isbn_dict.setdefault(_isbn, user_list[idx])
                
        return isbn_dict
                
    def check_updates(self, history_dict):
        """Check for updates and differences of user's borrowing list
        by comparing the historical set of books and newly synchronized one.
        
        Returns: One dict and two lists wrapped by a tuple:
        ({SYNC_LIST}, [NEWLY_BORROWED], [RETURNED])"""
        user_list = self.get_user_list()
        if user_list:
            isbn_indexed_dict = self.retrieve_isbn(user_list)
            isbn_new_books = set(isbn_indexed_dict.keys())
            isbn_history_books = set(history_dict.keys())
            
            set_intersection = isbn_new_books & isbn_history_books
            return isbn_indexed_dict, list(isbn_new_books - isbn_history_books), list(isbn_history_books - set_intersection)
            # return ({SYNC_LIST}, [NEWLY_BORROWED], [RETURNED])
        else:
            raise Exception, 'Failed to synchornize user list.'
            
    def post(self, uri, params):
        param = urlencode(params)
        try:
            response = urllib2.urlopen(uri, param).read()
        except:
            return None
        
        return response
    
class LibraryMashup:
    """This class inquiries metadata and reservation status through UESTC Library portal.
    Given any valid and arbitrary ISBN serial, this class simulates an inquiry in library portal via HTTP.
    Finally, after parsing raw HTML response, this class returns a list of books with required properties.
    """
    def __init__(self, api=''):
        self.API_ENTRY = api
        self.TABLE_KEYWORDS = '<table width="100%" border="0" cellspacing="1" cellpadding="2" class="bibItems">'
        self.TR_SPLIT = '<tr  class="bibItemsEntry">'
    
        self.parser = LibReservParser()
    
    def query(self, isbn):
        if not isbn: return None
        
        param = urlencode( [('isbn', isbn)] )
        try:
            response = urllib2.urlopen(self.API_ENTRY, param).read()
        except:
            return None
            
        response_group = response.split('<split />')
        if response_group and len(response_group):
            return [self.process(r) for r in response_group]
    
    def process(self, response):
        if response != '{}': # this indicates a not found exception
            return self.parse(response)
        else:
            return (0, 0, []) # no books matched :(
          
    def parse(self, html):
        self.parser.initialize()
        self.parser.feed(html)
        return (self.parser.count, self.parser.available, [dict(book) for book in self.parser.books])
