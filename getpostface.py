#!/usr/bin/env python

import sys
import time
import logging
import logging.config
from urlparse import urljoin
from pymongo import MongoClient
from util import *

logFormatter = logging.Formatter(fmt='%(asctime)s %(levelname)s %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
rootLogger = logging.getLogger('__name__')
rootLogger.setLevel(logging.DEBUG)

fileHandler = logging.FileHandler("runmm.log")
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)


mywf = webFace()

## create connection and access specific database
client = MongoClient("172.17.0.1", 27017)
db = client['webface']['mmjpg'] # dabatase/collection

if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
    url = sys.argv[1]
else:
    url = "http://www.mmjpg.com"  # start with this website

## crawl the website
url_done = {}  # url done for this session
def nestedCrawler(url, url_done):
    soup = getSoup(url)
    soup = soup.find(attrs={"class": "pic"}) # discard the naviagtion bar. change if needed
    all_a_tags = soup.find_all('a')  # find all links
    rootLogger.info("about to crawl %s links in %s" %(len(all_a_tags), url))
    
    #rootLogger.debug("url_done11: %s" % (url_done.keys()))
    #rootLogger.debug("all_a_tags in (%s): %s" % (url, [x['href'] for x in all_a_tags]))
    for x_i, x_link in enumerate(all_a_tags):  # crawl all linked pages (posts)
        x_url = urljoin(url, x_link['href'])
        #continue
        #x_url = "http://www.mmjpg.com/mm/241"
        ## skip if x_url has been crawled in this run session
        if x_url in url_done:
            continue
        ## skip if x_url has been crawled and stored in db
        if db.find({'url':x_url}, limit=1).count() > 0 :
            rootLogger.debug("skip url already in db: %s" % (x_url) )
            url_done[x_url] = 1
            continue
        rootLogger.debug("No.%s url: %s" % (x_i, x_url))
    
        ## extract image urls from the webpage
        try:
            x_ret = getPostImgUrls_mmjpg(x_url)
        except Exception as e:
            rootLogger.exception("fail to getPostImgUrls() for %s-th url: %s" %(x_i, x_url))
            url_done[x_url] = 1
            nestedCrawler(x_url, url_done)
            continue
        if x_ret is None:
            rootLogger.debug("get None img url, skip it: %s" % (x_url) )
            continue
    
        ## calculate face embedding (representation) using openface
        if 'imgurls' in x_ret:
            x_ret['reps'] = []
            start = time.time()
            for imgurl in x_ret['imgurls']:
                imgurl = urljoin(x_ret['url'], imgurl)
                bgrImg = url_to_bgrImg(imgurl)
                if bgrImg is None:
                    rootLogger.exception("getPostImgUrls() returns None from %s %s" % (imgurl, x_ret['url']))
                    x_ret['reps'].append([])
                    continue
                imgReps = mywf.getRepsFromImg(bgrImg)
                x_ret['reps'].append(imgReps)
                # time.sleep(1)
            rootLogger.info("process %d img urls in %.2f seconds" % (len(x_ret['imgurls']), time.time() - start) )
    
        db.update({'url':x_url}, {"$set":x_ret}, upsert=True, multi=False) # update (upsert) database
        time.sleep(2)  # take a break and avoid getting banned
    
    url_done[x_url] = 1

nestedCrawler(url, url_done)
rootLogger.debug("nestedCrawler done with url_done: %s" % (len(url_done)))
