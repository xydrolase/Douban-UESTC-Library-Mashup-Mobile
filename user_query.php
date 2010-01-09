<?php
/*
Douban & UESTC Library Mashup
	User Borrowing List API
	
	Author : killkeeper
		killkeeper at gmail dot com
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

	$memc = new Memcache();
	$memc->connect("locaohost", 11211);
	
	if (isset($_POST['auth'])){
		$auth = base64_decode($_POST['auth']);
		if ($auth){
			list($barcode, $password) = explode(":", $auth);
			$key = 'libdb_user_'.$barcode;
			
			if ($borrow_list = $memc->get($key)){
				return $borrow_list;	/* hit a cache */
			}
			
			/* create the Auth instance */
			$libauth = new LibraryAuth($barcode, $password);
			$portal = $libauth->auth();
			
			if ($portal){
				$borrow_list = $libauth->retrieve_list($portal);
				
				$memc->set($key, $borrow_list, 3600);	// cache for 1 hour
				die($borrow_list);
			}
			else{
				/* auth failed */
			}
		}
		
	}

	class LibraryAuth{	
		var $barcode = null;
		var $password = null;
		var $cookies = null;
		var $borrow_list = null;
		var $auth_api = "/patroninfo*chx";
		var $domain = 'http://222.197.164.247';
		var $referer = null;
		var $margin_flag = '<table border="0" class="patFunc">';
		
		function __construct($barcode, $pass){
			$this->barcode = $barcode;
			$this->password = $pass;
		}
		
		function retrieve_list($loc){
			if ($loc){
				$response = $this->http_get($this->domain.$loc, false, $this->cookies);
				$content = $response['content'];
				$start_pos = strpos($content, $this->margin_flag);
				$end_pos = strpos($content, '</table>', $start_pos);
				
				$this->borrow_list = substr($content, $start_pos, $end_pos - $start_pos + 7);
				return $this->borrow_list;
			}
		}
		
		function auth(){
			$response = $this->http_get($this->domain.$this->auth_api, true, $this->cookies);	// retrieve 'Set-Cookie' header
			$this->cookies = $this->parse_cookies($response);
			
			if ($this->cookies){
				$response = $this->http_post($this->domain.$this->auth_api, 
						array('code' => $this->barcode, 'pin' => $this->password, 'submit' => 'submit'),	// 	post body
						true,	// return the headers of HTTP response
						$this->cookies);	// set the cookies to maintain session
						
				$http_code = $response['code'];
				if ($http_code == 200){
					// 200 OK indicates an error when logining
					return null;
				}
				else if($http_code == 302){
					if (preg_match("/Location: (.+)/", $response['content'], $matches)){
						$loc = $matches[1];
						return $loc;
					}
				}
			}
		}
		
		function parse_cookies($response){
			if (isset($response['header']) && $response['header']){
				$headers = explode("\n", $response['header']);
				$cookies = array();
				
				foreach($headers as $hdr){
					if (preg_match("/^Set-Cookie: ([A-Za-z0-9_]+\=[A-Za-z0-9_]+;)/", $hdr, $matches)){
						array_push($cookies, $matches[1]);
					}
				}
				
				return $cookies;
			}
		}
		
		function failure($info){
			die("Error: ". $info);
		}
		
		function http_get($url, $header = false, $cookie = null){
			$ch = curl_init();
			curl_setopt($ch, CURLOPT_URL, $url);
			curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
			curl_setopt($ch, CURLOPT_FOLLOWLOCATION, false);	// do not follow the 302 See Other header
			curl_setopt($ch, CURLOPT_HEADER, $header);
			
			if ($this->referer){
				curl_setopt($ch, CURLOPT_HTTPHEADERS, array('Referer' => $this->referer));
			}
			
			if ($cookie){
				if (is_array($cookie)){
					$cookie = implode(' ', $cookie);
				}
				curl_setopt($ch, CURLOPT_COOKIE, $cookie);
			}
			
			$content = curl_exec($ch);
			$http_code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
			curl_close($ch);
			
			$headers = null;
			if ($header){
				// split the header information
				$pos = strpos($content, "\n\n");
				if ($pos !== false){
					$headers = substr($content, 0, $pos);
					$content = substr($content, $pos);
				}
			}
			
			$this->referer = $url;
			
			return array('code'=> $http_code, 'content' => $content, 'header' => $headers);
		}
		
		function http_post($url, $params = null, $header = false, $cookie = null){
			$ch = curl_init();
			curl_setopt($ch, CURLOPT_URL, $url);
			curl_setopt($ch, CURLOPT_FOLLOWLOCATION, false);	// do not follow the 302 header
			curl_setopt($ch, CURLOPT_HEADER, $header);		// return the headers
			curl_setopt($ch, CURLOPT_POST, true);
			curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
			
			if ($params){
				$post_field = $this->param_to_string($params);
				curl_setopt($ch, CURLOPT_POSTFIELDS, $post_field);
			}
			
			if ($cookie){
				if (is_array($cookie)){
					$cookie = implode(' ', $cookie);
				}
				curl_setopt($ch, CURLOPT_COOKIE, $cookie);
			}
			
			if ($this->referer){
				curl_setopt($ch, CURLOPT_HTTPHEADERS, array('Referer' => $this->referer));
			}
			
			$content = curl_exec($ch);
			$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);	// status code
			curl_close($ch);
			
			$headers = null;
			if ($header){
				// split the header information
				$pos = strpos($content, "\n\n");
				if ($pos !== false){
					$headers = substr($content, 0, $pos);
					$content = substr($content, $pos);
				}
			}
			
			$this->referer = $url;
			
			return array('code'=> $http_code, 'content' => $content, 'header' => $headers);
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