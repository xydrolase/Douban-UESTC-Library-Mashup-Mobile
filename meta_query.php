<?php
	
/* Douban & UESTC Library Mashup
		Version: 0.1.2.0
		Author:	killkeeper
			killkeeper AT gmail DOT com
			http://tremblefrog.org
			
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
*/
	
	require('dorm_db.php');
	
	define('QUERY_ISBN', 1);
	define('QUERY_CALLNO', 2);
	
	if (isset($_POST['meta']) && $_POST['meta']){
		$meta_needed = true;
	}
	
	if (isset($_POST['isbn'])){
		$isbn = $_POST['isbn'];
		
		$libm = new LibraryMashUp($isbn, QUERY_ISBN, $meta_needed);
		$html = $libm->query_all_by_isbn();
	
		die($html);
	}
	
	if (issset($_POST['callno'])){
		$callno = $_POST['callno'];
		
		$libm = new LibraryMashUp($callno, QUERY_CALLNO, $meta_needed);
		$html = $libm->query_all_by_isbn();
	
		die($html);
	}

	class LibraryMashup{
		var $isbn_list;
		var $cache_id;
		var $book_title;
		var $table_keywords = '<table width="100%" border="0" cellspacing="1" cellpadding="2" class="bibItems">';
		var $metadata_keywords = '<!-- BEGIN INNER BIB TABLE -->';
		
		var $query_path = "http://222.197.164.247/search*chx";
		
		function LibraryMashup($meta, $query_type, $meta_needed = false){
			if ($query_type == QUERY_ISBN){
				$this->isbn_group = explode(',', $meta);
				if (!is_array($this->isbn_group) || !count($this->isbn_group)){
					die("{}");
				}
				
				$this->expires = 3600;	// Expires after 1 hour
			}
			else if($query_type == QUERY_CALLNO){
				$this->callno_group = explode(',', $meta);
				if (!is_array($this->callno_group) || !count($this->callno_group)){
					die("{}");
				}
				
				$this->expires = 3600 * 72;	// cache for 3 days	
			}
			
			$this->metadata = $meta_needed;
			$this->memcache = new Memcache();
			$this->memcache->connect('127.0.0.1',11211);	/* connect memcache for cache */
		}
		
		function query_all($query_type){
			$response_list = array();
			if ($query_type == QUERY_ISBN){
				$meta_group = $this->isbn_group;
			}
			else if ($query_type == QUERY_CALLNO){
				$meta_group = $this->callno_group;
			}
			
			foreach($meta_group as $entry){
				array_push($response_list, $this->query($entry, $query_type));
			}
			
			return implode("<split />", $response_list);
		}
		
		function query($meta, $query_type){
			$queries = array();	/* Queries to execute for this entry */
			
			if ($query_type == QUERY_ISBN){
				$isbn = $meta;
				$isbn_list = explode('-', $isbn);
				$this->cache_id = 'libdb_isbn_'.$isbn;
				
				$cache = $this->memcache->get($this->cache_id);
				if ($cache){
					return $cache;
				}
				
				foreach($isbn_list as $_isbn){
					$query = array( 'SORT' => 'D', 'searchscope' => 1, 'searchtype' => 'i', 'searcharg' => $_isbn );
					array_push($queries, $query);
				}
			}
			else if ($query_type == QUERY_CALLNO){
				$callno = $meta;
				$this->cache_id = 'libdb_callno_'.md5($callno);
				
				$cache = $this->memcache->get($this->cache_id);	
				if ($cache){
					return $cache;
				}
				
				$query = array( 'SORT' => 'D', 'searchscope' => 1, 'searchtype' => 'c', 'searcharg' => $callno );
				array_push($queries, $query);
			}
					
			$entity_found = false;
			foreach($queries as $q){
				$ret_val = $this->library_query_by_isbn($q);
				
				if ($ret_val){
					$entity_found = true;	/* found a corresponding entity in library */
					return $ret_val;
				}
			}
					
			if (!$entity_found){
				/* still nothing */
				$not_found_html = '{}';	
				$this->memcache->set($this->cache_id, $not_found_html, false, $this->expires);	// cache for 1 hour :)
					
				return $not_found_html;
			}
					
		}
		
		function library_query($params){
			$result = $this->http_post($this->query_path, $params);
			
			if (strpos($result, '未找到') !== false){
				// no such entry found in library
				return null;
			}
			else{
				if ($this->metadata){
					$table_start = strpos($result, $this->metadata_keywords) + strlen($this->metadata_keywords);
				}
				else{
					$table_start = strpos($result, $this->table_keywords);
				}
				
				if ($table_start !== false){
					$table_end = strpos($result, '</table>', $table_start) + strlen('</table>');	// search with an offset
					
					$table_html = substr($result, $table_start, $table_end - $table_start);
					
					/* replace the relative hyperlink to a absolute link */
					$table_html = preg_replace("/href=\"(.+)\"/i", "href=\"http://webpac.uestc.edu.cn\\1\"", $table_html);
					
					/* insert into the cache */
					$this->memcache->set($this->cache_id, $table_html, false, $this->expires);	// cache for 1 hour :)
					
					return $table_html;
				}
				else
					return null;
			}
		}
		
		function http_get($url){
			$ch = curl_init();
			curl_setopt($ch, CURLOPT_URL, $url);
			curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
			
			$content = curl_exec($ch);
			curl_close($ch);
			
			return $content;
		}
		
		function http_post($url, $params = null){
			
			$ch = curl_init();
			curl_setopt($ch, CURLOPT_URL, $url);
			curl_setopt($ch, CURLOPT_POST, true);
			curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
			
			if ($params){
				$post_field = $this->param_to_string($params);
				curl_setopt($ch, CURLOPT_POSTFIELDS, $post_field);
			}
			
			$content = curl_exec($ch);
			curl_close($ch);
			
			return $content;
		}
		
		function param_to_string($params){
			$_temp = array();
			
			foreach($params as $key => $value){
				array_push($_temp, "{$key}={$value}");
			}
			$post_field = implode('&', $_temp);
			
			return $post_field;
		}
	}
	
	
?>
	
