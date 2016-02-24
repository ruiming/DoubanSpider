#!/usr/bin/python
# -*- coding:utf-8 -*-
# __author__ = 'Ruiming Zhuang'
import urllib
import urllib2
import cookielib
import random
import re
import threading
import os
import multiprocessing
import time
import proxy
from bs4 import BeautifulSoup

number = 0
tagsLink = []       # 标签链接
tagsName = []       # 标签名
booklinklist = []   # 豆瓣全部书籍链接
UserAgent = [
    'Mozilla/5.0 (Linux; Android 4.1.1; Nexus 7 Build/JRO03D) AppleWebKit/535.19 (KHTML, like Gecko) '
    'Chrome/18.0.1025.166  Safari/535.19',
    'Mozilla/5.0 (Android; Mobile; rv:14.0) Gecko/14.0 Firefox/14.0',
]                   # User-Agent池
proxyList = []      # proxy列表,proxy[0]则为代理地址和端口组合
# proxyList = proxy.getproxylist()
txtpath = r"proxy_list.txt"
fp = open(txtpath)
for lines in fp.readlines():
    lines = lines.replace("\n", "")
    proxyList.append(lines)
fp.close()


# 爬取豆瓣所有标签的标签名和标签链接
class GetTags:

    # 初始化方法
    def __init__(self):
        # 代理设置
        self.proxy_url = proxyList[3]
        self.proxy = urllib2.ProxyHandler({"http": self.proxy_url})
        # 参数
        self.hostURL = 'http://book.douban.com/tag/'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.47 (KHTML, like Gecko)'
                          ' Chrome/48.1.2524.116 Safari/537.36',
            'Referer': 'http://book.douban.com/',
            'Host': 'book.douban.com',
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive'
        }
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
            tagsLink.append(re.sub(pattern, r'book?start=', tag.get('href').encode('utf-8')))
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
        self.hosturl = 'http://book.douban.com/tag/'

    # 根据proxyurl获取opener
    def get_opener(self, proxy_url):
        # 代理设置,随机获取一个代理和UA
        proxyurl = proxy_url
        proxysupport = urllib2.ProxyHandler({"http": proxyurl})
        # opener设置
        cookie = cookielib.LWPCookieJar()
        cookiehandler = urllib2.HTTPCookieProcessor(cookie)
        opener = urllib2.build_opener(cookiehandler, proxysupport, urllib2.HTTPHandler)
        return opener

    # 获取proxyurl
    def get_proxy(self):
        i = random.randint(0, len(proxyList)-1)
        proxyurl = self.proxylist[i]
        return proxyurl

    # 获取header
    def get_header(self):
        j = random.randint(0, len(UserAgent)-1)
        header = {
            'User-Agent': UserAgent[j],
            'Referer': 'http://book.douban.com/',
            'Host': 'www.douban.com',
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive'
        }
        return header

    # 获取标签页面的全部书籍链接并存入list
    def get_tag_page(self):
        # retry 重试次数, count 同个代理的派去次数， page 书籍
        retry, count, page = 0, 0, 0
        proxyurl = self.get_proxy()
        opener = self.get_opener(proxyurl)
        header = self.get_header()
        while True:
            try:
                # 同个代理爬五次换UA
                if count == 5:
                    header = self.get_header()
                # 同个代理爬十次代理
                if count == 10:
                    proxyurl = self.get_proxy()
                    opener = self.get_opener(proxyurl)
                    count = 0
                # 每重试两次换一次UA和代理
                if retry == 2:
                    header = self.get_header()
                    proxyurl = self.get_proxy()
                    opener = self.get_opener(proxyurl)
                    retry = 0
                    count = 0
                # 开始
                pagelink = self.taglink + str(page)
                request = urllib2.Request(pagelink, None, header)
                response = opener.open(request, None, 8)
                content = response.read()
                # 匹配页面的书籍索引号并存入booklinklist
                pattern = re.compile('<dt.*?<a.*?subject/(.*?)/\?from', re.S)
                booklinks = re.findall(pattern, content)
                if len(booklinks) > 0:
                    filename = ("book/" + self.tagname + ".txt").decode('UTF-8')
                    f = open(filename, 'a')
                    for booklink in booklinks:
                        booklinklist.append(booklink)
                        f.write("%s\r\n" % booklink)
                    f.close()
                    count += 1
                    print "success - " + " 获取 " + self.tagname + " 标签第" + str(page/15+1) + "页书籍 -- " + proxyurl
                    page += len(booklinks)
                    # END 若该页面书籍数量在1-14本之间，则说明结束
                    if page % 15 != 0:
                        print "*****" + "已获取 " + self.tagname + " 标签下的全部 " + str(page) + " 本书籍"
                        break
                    # NEXT 爬取页面正常结束，开始下一页的爬取
                    time.sleep(random.randint(1, 3))
                # END 正则匹配不到，说明结束
                elif response.getcode() == 200 and len(booklinks) == 0:
                    print "----" + "已获取 " + self.tagname + " 标签下的全部 " + str(page) + " 本书籍"
                    break
            # ERROR 若报错
            except Exception, e:
                print "fail    - " + " 获取 " + self.tagname + " 标签第" + str(page/15+1) + "页书籍 -- " + proxyurl
                retry += 1
                time.sleep(random.randint(4, 8))

    # 多进程，每个标签开一个进程处理
    def run(self):
        self.get_tag_page()
        time.sleep(10)


# todo
if __name__ == "__main__":
    gettags = []
    getbooks = []
    path = 'book'
    path = path.strip()
    if not os.path.exists(path):
        os.makedirs(path)
    GetTags().run()
    process = []
    for n in range(len(tagsName)):
        p = GetBooks(tagsLink[n], tagsName[n], proxyList)
        process.append(p)
        p.start()
        time.sleep(random.randint(0, 5))
    for x in range(len(tagsName)):
        process[x].join()
    print " -- over"

