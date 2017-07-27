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

## query face 
mywf = webFace()
q_imgurl = "http://img4.duitang.com/uploads/item/201507/28/20150728133323_HfVnr.jpeg" # yangmi
q_bgrImg = url_to_bgrImg(q_imgurl)
q_facerep = mywf.getRepsFromImg(q_bgrImg, multiple=False)[0]
print q_facerep


## create connection and access specific database
client = MongoClient("172.17.0.1", 27017)
db = client['webface']['post2'] # dabatase--collection

cursor = db.find({})
for web in cursor:
    web_imgurls = []
    web_facereps = []
    ## iterate over all faces
    if 'reps' not in web:
        rootLogger.debug("no valid image: %s" % (web['url']))
        continue
    for img_idx, face_reps in enumerate(web['reps']):
        for face in face_reps:
            web_imgurls.append(urljoin(web['url'], web['imgurls'][img_idx]))
            web_facereps.append(face)
    rootLogger.debug("comparing with %d faces: %s %s" % (len(web_facereps), web['url'], web['title']))
    if len(web_facereps) == 0:
        continue
    web_facereps = np.array(web_facereps)
    ## calculate distance of query face to all faces in this webpage
    dist = calDist(q_facerep, web_facereps)
    rootLogger.debug("dist=%s" %(dist))

sys.exit(0)
