#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

## query face 
mywf = webFace()
q_imgurl = "http://img4.duitang.com/uploads/item/201507/28/20150728133323_HfVnr.jpeg" # yangmi
q_imgurl = 'http://imgbdb3.bendibao.com/bjbdb/20157/30/2015730235720677.jpg'  # wujing 吴京
q_bgrImg = url_to_bgrImg(q_imgurl)
q_facerep = mywf.getRepsFromImg(q_bgrImg, multiple=False)[0]
rootLogger.info("query image url: %s" % (q_imgurl))
rootLogger.debug("query face rep: %s" % ([round(x, 2) for x in q_facerep]))

topN = 5
topN_imgurl = []
topN_dist = []

## create connection and access specific database
client = MongoClient("172.17.0.1", 27017)
db = client['webface']['post2'] # dabatase--collection

cursor = db.find({})
for web in cursor:
    web_imgurls = []
    web_facereps = []

    ## iterate over all images and get all the face reps
    if 'reps' not in web:
        rootLogger.debug("no valid image: %s" % (web['url']))
        continue
    for img_idx, face_reps in enumerate(web['reps']):
        for face in face_reps:
            web_imgurls.append(u' '.join([urljoin(web['url'], web['imgurls'][img_idx]), web['url'], web['title']]))
            web_facereps.append(face)
    rootLogger.debug("comparing with %d faces: %s %s" % (len(web_facereps), web['url'], web['title']))
    if len(web_facereps) == 0:
        continue
    web_facereps = np.array(web_facereps)

    ## calculate distance of query face to all faces in this webpage
    web_faceDists = calDist(q_facerep, web_facereps)
    rootLogger.debug("dists=%s" %(web_faceDists))

    ## update the list of (top N) most similar faces
    tmp_dists = np.concatenate([topN_dist, web_faceDists])
    tmp_idx = np.argsort(tmp_dists)[::+1][:topN]  # index of ordered items
    if any(i >= topN for i in tmp_idx): # if there is any face with smaller distance
        topN_dist = [tmp_dists[i] for i in tmp_idx]
        tmp_imgurls = topN_imgurl + web_imgurls
        topN_imgurl = [tmp_imgurls[i] for i in tmp_idx]
        rootLogger.debug("updated topN dists: %s" % (topN_dist))
        rootLogger.debug("updated topN imgurl: %s" % (repr(topN_imgurl).decode("unicode-escape")))
        rootLogger.debug("-----")

## print the final result
rootLogger.info("########### final top %d face ##############" % (topN))
rootLogger.info("query image: %s" % (q_imgurl))
for i,dist in enumerate(topN_dist):
    rootLogger.info("%.3f %s" % (dist, topN_imgurl[i].encode('utf-8')))

sys.exit(0)
