<?php
	/* Douban & UESTC Library Mashup
		Version: 0.1.2.0
		Author:	killkeeper
			killkeeper AT gmail DOT com
			http://tremblefrog.org
	*/
	
	require('dorm_db.php');
	
	if (isset($_POST['isbn'])){
	    $isbn = $_POST['isbn'];
	    
	    $libm = new LibraryMashUp($isbn);
		$html = $libm->query_all();
	
	    die($html);
	}
	
	
	function html_to_js_wrapper($html, $book_title){
		$html = str_replace("\n", "", $html);
		$book_title = htmlentities($book_title, ENT_QUOTES, "UTF-8"); // convert the special characters, specifically the quotes into safe html to prevent corruption of generated javascript
		
		$js = "$('#libdbDiv').hide('slow');\nshow_dialog('<h2 class=\"usf\">$book_title - 馆藏分布 &middot;&middot;&middot;&middot;</h2><div class=\"indent\"><ul class=\"bs\"><li><div style=\"max-height:250px; overflow-y:auto; height:200px;\">$html</div></li><li>(注意: 查询结果具有1小时的缓存, 您看到的可能不是即时的查询结果)</li></ul><p><input type=\"button\" onclick=\"close_dialog()\" value=\"关闭\" />');";
		return $js;
	}

	class LibraryMashup{
		var $isbn_list;
		var $cache_id;
		var $book_title;
		var $table_keywords = '<table width="100%" border="0" cellspacing="1" cellpadding="2" class="bibItems">';
		
		var $query_path = "http://222.197.164.247/search*chx";
		
		function LibraryMashup($isbn){
		    $this->isbn_group = explode(',', $isbn);
		    if (!is_array($this->isbn_group) || !count($this->isbn_group)){
    	        die("{}");
    	    }
    	    
			$this->memcache = new Memcache();
			$this->memcache->connect('127.0.0.1',11211);	/* connect memcache for cache */
		}
		
		function query_all(){
		    $response_list = array();
		    foreach($this->isbn_group as $entry){
		        array_push($response_list, $this->query_by_isbn($entry));
		    }
		    
		    return implode("<split />", $response_list);
		}
		
		function query_by_isbn($isbn){
		    $isbn_list = explode('-', $isbn);
		    $this->cache_id = 'libdb_isbn_'.$isbn;
		    
		    $cache = $this->memcache->get($this->cache_id);
		    if ($cache){
		        return $cache;
		    }
		    
			$queries = array();
			foreach($isbn_list as $isbn){
			    $query = array( 'SORT' => 'D', 'searchscope' => 1, 'searchtype' => 'i', 'searcharg' => $isbn );
			    array_push($queries, $query);
			}
						
			$entity_found = false;
			foreach($queries as $q){
				$ret_val = $this->library_query($q);
				
				if ($ret_val){
					$entity_found = true;	/* found a corresponding entity in library */
					return $ret_val;
				}
			}
					
			if (!$entity_found){
				/* still nothing */
				$not_found_html = '{}';	
				$this->memcache->set($this->cache_id, $not_found_html, false, 3600);	// cache for 1 hour :)
					
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
				$table_start = strpos($result, $this->table_keywords);
				if ($table_start !== false){
					$table_end = strpos($result, '</table>', $table_start) + strlen('</table>');	// search with an offset
					
					$table_html = substr($result, $table_start, $table_end - $table_start);
					
					/* replace the relative hyperlink to a absolute link */
					$table_html = preg_replace("/href=\"(.+)\"/i", "href=\"http://webpac.uestc.edu.cn\\1\"", $table_html);
					
					
					/* insert into the cache */
					$this->memcache->set($this->cache_id, $table_html, false, 3600);	// cache for 1 hour :)
					
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
	
