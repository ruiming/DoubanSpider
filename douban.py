#!/usr/bin/python
# -*- coding:utf-8 -*-
# __author__ = 'Ruiming Zhuang'
import urllib
import urllib2
import cookielib
import json
import os
import random
import re
import sys
import threading
import multiprocessing
import time
import proxy
from multiprocessing import Pool
from bs4 import BeautifulSoup


tagsLink = []       # 标签链接
tagsName = []       # 标签名
booklinklist = []   # 豆瓣全部书籍链接
UserAgent = [
    'Mozilla/5.0 (Linux; Android 4.1.1; Nexus 7 Build/JRO03D) AppleWebKit/535.19 (KHTML, like Gecko) '
    'Chrome/18.0.1025.166  Safari/535.19',
    'Mozilla/5.0 (Android; Mobile; rv:14.0) Gecko/14.0 Firefox/14.0',
    'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:21.0) Gecko/20100101 Firefox/21.0',
    'Mozilla/4.0 (compatible; MSIE 7.0; Windows Phone OS 7.0; Trident/3.1; IEMobile/7.0; LG; GW910)',
    'Mozilla/5.0 (iPod; U; CPU like Mac OS X; en) AppleWebKit/420.1 (KHTML, like Gecko) Version/3.0 Mob'
    'ile/3A101a Safari/419.3',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:21.0) Gecko/20100101 Firefox/21.0',
    'Mozilla/5.0 (compatible; WOW64; MSIE 10.0; Windows NT 6.2)',
    'Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; en) Presto/2.9.168 Version/11.52',
    'Mozilla/5.0 (iPod; U; CPU like Mac OS X; en) AppleWebKit/420.1 (KHTML, like Gecko) Version/3.0 M'
    'obile/3A101a Safari/419.3'
]                   # User-Agent池，9个
proxyList = []      # proxy列表,proxy[0]则为代理地址和端口组合
# proxyList = proxy.getproxylist()
txtpath = r"proxy_list.txt"
fp = open(txtpath)
for lines in fp.readlines():
    lines = lines.replace("\n", "")
    proxyList.append(lines)
fp.close()


# 爬取豆瓣所有标签下的所有书籍
class GetTags:

    # 初始化方法
    def __init__(self):
        # 代理设置
        self.proxy_url = proxyList[-29]
        self.proxy = urllib2.ProxyHandler({"http": self.proxy_url})
        # 参数
        self.hostURL = 'http://book.douban.com/tag/'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.37 (KHTML, like Gecko)'
                          ' Chrome/48.1.2524.116 Safari/537.36',
            'Referer': 'http://book.douban.com/',
            'Host': 'book.douban.com',
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive'
        }
        self.type = sys.getfilesystemencoding()
        # opener设置
        self.cookie = cookielib.LWPCookieJar()
        self.cookieHandler = urllib2.HTTPCookieProcessor(self.cookie)
        self.opener = urllib2.build_opener(self.cookieHandler, self.proxy, urllib2.HTTPHandler)

    # 获取全部标签链接和标签名
    def get_all_tag(self):
        request = urllib2.Request(self.hostURL, None, self.headers)
        response = self.opener.open(request)
        content = response.read()
        soup = BeautifulSoup(content, "lxml")
        tags = soup.find_all("a", class_="tag")
        pattern = re.compile('\?focus=book')
        # 分别存放标签链接和标签名
        for tag in tags:
            tagsLink.append(re.sub(pattern, 'book', tag.get('href').encode('utf-8')))
            tagsName.append(tag.get_text().encode('utf-8'))

    # 获取全部链接和标签名，保存到全局变量tasLink和tagsName中
    def run(self):
        self.get_all_tag()
        print "成功获取"+str(len(tagsName))+"个标签"


class GetBooks(multiprocessing.Process):

    # 初始化方法
    def __init__(self, taglink, tagname, proxylist):
        multiprocessing.Process.__init__(self)
        self.taglink = taglink
        self.tagname = tagname
        self.proxylist = proxylist
        self.content = None
        self.opener = None
        self.hosturl = 'http://book.douban.com/tag/'

    # 获取标签页面的全部书籍链接并存入list,每次调用都从代理列表随机选一个
    def get_tag_page(self):
        code = 0
        while code != 200:
            try:
                # 代理设置,随机获取一个代理
                i = random.randint(0, len(proxyList)-1)
                j = random.randint(0, len(UserAgent)-1)
                headers = {
                    'User-Agent': UserAgent[j],
                    'Referer': 'http://book.douban.com/',
                    'Host': 'www.douban.com',
                    'Upgrade-Insecure-Requests': '1',
                    'Connection': 'keep-alive'
                }
                proxy_url = self.proxylist[i]
                proxysupport = urllib2.ProxyHandler({"http": proxy_url})
                # opener设置
                cookie = cookielib.LWPCookieJar()
                cookiehandler = urllib2.HTTPCookieProcessor(cookie)
                opener = urllib2.build_opener(cookiehandler, proxysupport, urllib2.HTTPHandler)
                # 获取标签XX页代码
                request = urllib2.Request(self.taglink, None, headers)
                response = opener.open(request)
                content = response.read()
                # 匹配页面的书籍链接并存入booklinklist todo
                pattern = re.compile('<dt.*?<a.*?"(.*?)?from', re.S)
                booklinks = re.findall(pattern, content)
                if len(booklinks) > 0:
                    name = self.tagname + ".txt"
                    f = open(name, 'w+')
                    for booklink in booklinks:
                        booklinklist.append(booklink)
                        f.write("%s\r\n" % booklink)
                    f.close()
                    code = 200
                    print "success -" + " 获取 " + self.tagname + " 标签书籍 -- "+ proxy_url
            except Exception, e:
                print "fail    -" + " 获取 " + self.tagname + " 标签书籍，已重试-- "+ proxy_url
                code = 0
                time.sleep(8)

    # 从某页获取该页全部书籍链接
    def get_page_booklinks(self):
        # 该正则用于匹配该页书籍的全部链接
        books_pattern = re.compile('<dd.*?href="(.*?)"', re.S)
        books_url = re.findall(books_pattern, self.content)
        return books_url

    # 多进程，每个标签开一个进程处理
    def run(self):
        self.get_tag_page()
        time.sleep(8)


# todo
if __name__ == "__main__":
    gettags = []
    getbooks = []
    n = 0
    GetTags().run()
    while n < len(tagsLink):
        p = GetBooks(tagsLink[n], tagsName[n], proxyList)
        p.start()
        n += 1
