# Douban-UESTC Library Mashup Mobile

GAE driven website enhanced by douban.com and UESTC library Webpac system. 
Provides portal for searching your favorable books while fetching books reservation information simultaneously.

> You could visit a deployed version of Douban-UESTC Library Mashup Mobile called "Pixian Douban" via [http://dbutils.appspot.com/](http://dbutils.appspot.com/)
> This project is being developed on the basis of [Project libdb](http://tremblefrog.org/libdb/), which provides Bookmarklet/Greasemonkey script service. Yet this project mainly concerns a handy approach of accessing book information on your portalbe devices.

You fill find a great convenience using the new website version of Douban-UESTC Library Mashup. Logging with your Google Accounts, we provide services to record your intended borrowing book list, to notify the deadline of borrowing, to automatically renew your books, and to sync your booklist on douban.com. (_some features are still under development_)

## Requirements

* Google App Engine (with Python 2.5)
* PHP 5.2+
* Memcached 1.2.x+

To run this project correctly, you need to install serveral 3rd-party libraries:

* [gdata-python-client](http://code.google.com/apis/gdata/)
* atom (_provided in gdata-python-client_)
* [douban-python](http://code.google.com/p/douban-python/)

## Installation

**Step 1. Download the source**
    $ git clone git@github.com:killkeeper/Douban-UESTC-Library-Mashup-Mobile.git
    
**Step 2. Configure the website**
    Modify _config.py.default_ with your favorite text-editor, assign your own Douban API Key and corresponding SECRET.
    Specify a Twitter account to activate the twitter update feature in your admin console.
    After finishing modifications, rename the filename to _config.py_.
    
**Step 3. Install the dependent libraries**
    Download the prerequisite libraries, install with setuptools.
    Example:
    
    $ wget http://gdata-python-client.googlecode.com/files/gdata-2.0.6.tar.gz
    $ tar zxvf gdata-2.0.6.tar.gz
    $ cd gdata-2.0.6
    $ python setup.py install
    
    Then copy the "gdata" and "atom" directories from the Python libraries folder to where your source locates.
    
**Step 4. Deploy your source to GAE**
    Please read GAE reference for more information. :)  

## Contacts

> Any questions towards this project? Wanna implement your university's version of this project?
You could contact me via email: `killkeeper _at_ gmail _dot_ com`,

> If you are interested in me, you might:

* Visit [my blog](http://tremblefrog.org/blog/)
* Follow [@killkeeper](http://twitter.com/killkeeper) on Twitter

> Report bugs?
Please refer to the [issue list](http://github.com/killkeeper/Douban-UESTC-Library-Mashup-Mobile/issues)

## References

* [Douban](http://www.douban.com/)
* [UESTC Library](http://www.lib.uestc.edu.cn/)
* [Webpac System](http://webpac.uestc.edu.cn/)

- - -

# 豆瓣-电子科大图书馆馆藏查询 mobile (_a.k.a_ 郫县豆瓣.mobile)

由Google App Engine驱动的移动站点, 基于豆瓣网和电子科大图书馆为您的手持设备浏览器提供图书信息和馆藏状态查询.
你可以访问部署在GAE上的项目主页: [郫县豆瓣.mobile](http://dbutils.appspot.com/)

> 本项目基于豆瓣-电子科大图书馆馆藏查询脚本(`http://tremblefrog.org/libdb/`)发展而来.
> 不同于原来的Bookmarklet/Greasemonkey脚本, 这个项目致力于扩展应用的方便性和可用性.

您可以使用您的Google Accounts登录, 将您喜欢的图书保存到网站的列表中. 同时, 在开发中的新功能还有:
* 还书提醒
* 自动续借
* 同步我的豆瓣图书列表
 
等等...

## 需求

* Google App Engine (Python 2.5)
* PHP 5.2+
* Memcached 1.2.x+

要将这个程序正确的运行, 您还需要安装一些第三方的Python库, 包括:

* [gdata-python-client](http://code.google.com/apis/gdata/)
* atom (_provided in gdata-python-client_)
* [douban-python](http://code.google.com/p/douban-python/)

## 安装与运行

>  **注意:** 如果你希望运行一个基于其他大学图书馆的版本, 你需要实现自己的图书馆查询接口.

**Step 1. 下载源码**
    $ git clone git@github.com:killkeeper/Douban-UESTC-Library-Mashup-Mobile.git
    
**Step 2. 配置参数**
    修改 _config.py.default_, 设定你的豆瓣API Key和私钥.
    你可以指定一个Twitter账号, 以便在后台的建议twitter更新功能中发布项目的更新信息等等.
    完成配置后, 将文件重命名为_config.py_.
    
**Step 3. 安装第三方库**
    请下载上述需求的第三方Python库, 正确安装后将其源码拷贝到本项目的源码根目录
    
    Example:
    
    $ wget http://gdata-python-client.googlecode.com/files/gdata-2.0.6.tar.gz
    $ tar zxvf gdata-2.0.6.tar.gz
    $ cd gdata-2.0.6
    $ python setup.py install
    
    接着将Python库目录中的"gdata"和"atom"两个目录拷贝到当前源代码目录下
    
**Step 4. 部署你的网站到GAE**
    请查阅GAE的相关文档:) 

## 联系我

> 如果您有任何关于本项目的疑问, 或者您希望实现基于其他大学图书馆系统的系统, 请通过以下方式联系:

Email: `killkeeper _at_ gmail _dot_ com`

> 如果你关注我的动态, 可以:

* 访问 [我的Blog](http://tremblefrog.org/blog/)
* Follow [@killkeeper](http://twitter.com/killkeeper) on Twitter

> 如果要提交bug, 请到项目页面的[issue list](http://github.com/killkeeper/Douban-UESTC-Library-Mashup-Mobile/issues)

## 相关站点

* [豆瓣网](http://www.douban.com/)
* [电子科技大学图书馆](http://www.lib.uestc.edu.cn/)
* [Webpac](http://webpac.uestc.edu.cn/)