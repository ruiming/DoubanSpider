#!/usr/bin/python
# -*- coding:utf-8 -*-
# __author__ = 'Ruiming Zhuang'
# 爬虫通用程序
import urllib2
import re
import threading
import cookielib
import time


proxyList = []
checkedProxyList = []
proxy_ok = []
useragent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36'


class Target(object):
    def __init__(self, pageurl, page, pattern, header):
        """
        :param pageurl: 爬取的页面
        :param page: 页面拥有的页码数
        :param pattern: 页面ip和端口正则,两组
        :param header: 页面header
        :return: Target类，需要爬取的页面全部链接
        """
        self.page = page
        self.pageurl = pageurl
        self.pattern = pattern
        self.header = header
        self.links = []

    def run(self):
        # todo
        urlpattern = re.compile('(1){1}', re.S)
        getthreads = []
        checkthreads = []
        if self.page > 0:
            for x in xrange(1, self.page):
                link = re.sub(urlpattern, str(x), self.pageurl)
                self.links.append(link)
        else:
            self.links.append(self.pageurl)
        print '.'*10 + "正在读取网站上的代理" + '.'*10
        for x in range(len(self.links)):
            t = GetProxy(self, self.links[x])
            getthreads.append(t)
        for x in range(len(self.links)):
            getthreads[x].start()
        for x in range(len(self.links)):
            getthreads[x].join()
        print '.'*10+"一共抓取了%s个代理" % len(proxyList) + '.'*10
        for i in range(20):
            t = CheckProxy(proxyList[((len(proxyList)+19)/20) * i:((len(proxyList)+19)/20) * (i+1)])
            checkthreads.append(t)
        for i in range(len(checkthreads)):
            checkthreads[i].start()
        for i in range(len(checkthreads)):
            checkthreads[i].join()
        print '.'*10+"总共有%s个代理通过校验" % len(checkedProxyList) +'.'*10
        f = open("proxy_list.txt", 'a')
        for proxy in checkedProxyList:
            proxyurl = proxy[0] + ":" + proxy[1]
            proxy_ok.append(proxyurl)
            f.write("%s:%s\r\n" % (proxy[0], proxy[1]))
        f.close()
        print '.'*10 + "成功存入文件 proxy_list.txt" + '.'*10
        time.sleep(3)


class GetProxy(threading.Thread):
    # 将target类传入，多线程分配link
    def __init__(self, target, link):
        threading.Thread.__init__(self)
        self.pageurl = target.pageurl
        self.page = target.page
        self.pattern = target.pattern
        self.header = target.header
        self.link = link

    def getproxy(self):
        retry = True
        while retry:
            # 默认使用代理
            try:
                proxy_support = urllib2.ProxyHandler({'http': '127.0.0.1:1080'})
                opener = urllib2.build_opener(proxy_support)
                urllib2.install_opener(opener)
                request = urllib2.Request(self.link, None, self.header)
                response = urllib2.urlopen(request)
                response = response.read()
                matchs = self.pattern.findall(response)
                for line in matchs:
                    ip = line[0]
                    port = line[1]
                    proxy = [ip, port]
                    print r'读取  http://%s:%s' % (line[0], line[1])
                    proxyList.append(proxy)
                retry = False
            except Exception, e:
                retry = True
                time.sleep(3)

    def run(self):
        self.getproxy()


class CheckProxy(threading.Thread):
    def __init__(self, proxyList):
        threading.Thread.__init__(self)
        self.proxyList = proxyList
        self.timeout = 5
        self.testStr = "html"
        self.testURL = "http://www.baidu.com"

    def checkproxy(self):
        cookies = urllib2.HTTPCookieProcessor()
        for proxy in self.proxyList:
            proxyhandler = urllib2.ProxyHandler({"http": r'http://%s:%s' % (proxy[0], proxy[1])})
            opener = urllib2.build_opener(cookies, proxyhandler)
            opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                                '(KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36')]
            opener.addheaders = [('Referer', 'http://proxy.moo.jp/zh/')]
            t1 = time.time()
            try:
                request = opener.open(self.testURL, timeout=self.timeout)
                result = request.read()
                timeused = time.time() - t1
                pos = result.find(self.testStr)
                if pos > 1:
                    print r'success --http://%s:%s' % (proxy[0], proxy[1])
                    checkedProxyList.append((proxy[0], proxy[1]))
                else:
                    print r'fail    --http://%s:%s' % (proxy[0], proxy[1])
                    continue
            except Exception, e:
                print r'fail    --http://%s:%s' % (proxy[0], proxy[1])
                continue

    def run(self):
        self.checkproxy()


def main():
    # 网站 pageurl, page, pattern, header 第一页的带页码地址，页码，正则，header
    # 网站1  www.proxy.com.ru
    pageurl = r"http://www.proxy.com.ru/list_1.html"
    page = 100
    pattern = re.compile('<tr.*?<td>\d{1,4}</t.*?<td>(.*?)<.*?<td>(.*?)</td>', re.S)
    header = {
        'Referer': 'www.proxy.com.ru',
        'User-Agent': useragent,
        'Host': 'www.proxy.com.ru'
    }
    # Target(pageurl, page, pattern, header).run()

    # 网站4 https://www.us-proxy.org/
    pageurl = r"https://www.us-proxy.org/"
    page = 0
    pattern = re.compile('<tr><td>(.*?)</td><td>(\d{1,5})</td>', re.S)
    header = {
        'Referer': 'https://www.us-proxy.org/',
        'User-Agent': useragent,
    }
    # Target(pageurl, page, pattern, header).run()

    pageurl = r"http://www.cz88.net/proxy/"
    page = 0
    pattern = re.compile('<li><div.*?ip">(.*?)</div>.*?port">(.*?)</div>')
    header = {
        'Referer': 'www.cz88.net',
        'User-Agent': useragent,
        'Host': 'www.cz88.net'
    }
    Target(pageurl, page, pattern, header).run()


if __name__ == "__main__":
    main()
