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

from google.appengine.ext import db

class TaskList(db.Model):
	user = db.UserProperty()
	count = db.IntegerProperty(default=0)
	
class LibraryUser(db.Model):
    user = db.UserProperty()
    barcode = db.StringProperty()
    password = db.StringProperty()
    borrow_list = db.BlobProperty()     # for storing user's borrowing list
	
class BookTask(db.Model):
	user = db.UserProperty()
	blob = db.BlobProperty()		# for storing a Gdata object describing the book entry
	index = db.StringProperty()		# indexing number e.g. TP391.xx
	isbn = db.StringListProperty()	# [isbn10, isbn13]
	created = db.DateTimeProperty(auto_now_add=True)
	tasklist = db.ReferenceProperty(TaskList, collection_name="tasks")	# reference to tasklist
	
	#note = db.StringProperty(multiline=True)