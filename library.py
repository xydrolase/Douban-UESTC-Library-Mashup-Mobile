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

STATE_LOC = 1
STATE_INQ_NO = 2
STATE_STATUS = 3
STATE_BARCODE = 4
STATE_RESERVED = 5

INDEX_2_FLOOR = {'T':2, 'U':2, 'V':2, 'X':2,
                'A':3, 'B':3, 'C':3, 'D':3, 'E':3, 'F':3, 'G':3, 'H':3,
                'I':4, 'J':4, 'K':4, 'O':4, 'P':4, 'Q':4, 'R':4, 'S':4, 'Z':4}
                
INDEX_2_CATEGORY = {'T':'工业技术','TB':'一般工业技术','TD':'矿业工程','TE':'石油, 天然气工业','TF':'冶金工业','TG':'金属学与金属工业','TH':'机械. 仪表工业','TJ':'武器工业','TK':'能源与动力工程','TL':'原子能技术','TM':'电工技术','TN':'无线电电子学, 电信技术','TP':'自动化技术, 计算机技术','TQ':'化学工业','TS':'轻工业, 手工业','TU':'建筑科学','TV':'水利工程','U':'交通运输','V':'航空航天','X':'环境科学, 安全科学','C':'社会科学总论','D':'政治, 法律','E':'军事','F':'经济','G':'文化, 科学, 教育, 体育','H':'语言, 文学','A':'马列主义, 毛泽东思想, 邓小平理论','B':'哲学, 宗教','C':'社会科学总论','I':'文学','J':'艺术','K':'历史, 地理','O':'数理科学和化学','P':'天文学, 地球科学','Q':'生物科学','R':'医药, 卫生','S':'农业科学','Z':'综合性图书'}

idx_re = re.compile('([A-Z]+)\d+\.\d+')

def parse_index(idx):
    if idx:
        prefix = idx_re.search(idx).groups()[0]
        
        floor = INDEX_2_FLOOR.get(idx[0], None)
        category = INDEX_2_CATEGORY.get(prefix, None)
        
        return floor, category        
    else:
        return None, None

class LibraryParser(HTMLParser):
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

class LibraryMashup:
    API_ENTRY = "http://tremblefrog.org/libdb/query_isbn.php";  # we need our bridge for speed up again :(
    TABLE_KEYWORDS = '<table width="100%" border="0" cellspacing="1" cellpadding="2" class="bibItems">'
    TR_SPLIT = '<tr  class="bibItemsEntry">'
    
    parser = LibraryParser()
    
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
        
    def library_inquiry(self, isbn):
        params = ('isbn', )
            
        param = urlencode(params)
        
        
        if '未找到' in response:   # not found
            return None
        else:
            tbl_start = response.find(self.TABLE_KEYWORDS)
            if tbl_start:
                tbl_end = response.find('</table>', tbl_start) + len('</table>')
                tbl_content = response[tbl_start:tbl_end]
                
                return tbl_content
            else:
                return None