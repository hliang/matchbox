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

fileHandler = logging.FileHandler("run.log")
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)


mywf = webFace()

## create connection and access specific database
client = MongoClient("172.17.0.1", 27017)
db = client['webface']['post2'] # dabatase/collection

if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
    url = sys.argv[1]
else:
    url = "http://xxx.xxxx.xxx"  # start with this website

## crawl the website
soup = getSoup(url)
soup = soup.find(attrs={"class": "widthMain main"}) # discard the naviagtion bar. change if needed
all_a_tags = soup.find_all('a')  # find all links

for x_i, x_link in enumerate(all_a_tags):  # crawl all linked pages (posts)
    x_url = urljoin(url, x_link['href'])
    ## skip if x_url has been crawled and stored in db
    if db.find({'url':x_url}, limit=1).count() > 0 :
        rootLogger.debug("skip url already in db: %s" % (x_url) )
        continue

    ## extract image urls from the webpage
    try:
        x_ret = getPostImgUrls(x_url)
    except Exception as e:
        rootLogger.exception("fail to getPostImgUrls() for %s-th url: %s" %(x_i, x_url))
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

rootLogger.info("crawled %s links" %(len(all_a_tags)))

