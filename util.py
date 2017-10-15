#!/usr/bin/env python
# -*- coding: utf-8 -*-  

import sys
import os
import re
import time
import random
import logging
import logging.config
import requests
import json
import cv2
import numpy as np
np.set_printoptions(precision=2)
import openface
from StringIO import StringIO
from bs4 import BeautifulSoup
from urlparse import urljoin
from pymongo import MongoClient

rootLogger = logging.getLogger('__name__')

agents = [
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/532.5 (KHTML, like Gecko) Chrome/4.0.249.0 Safari/532.5",
    "Mozilla/5.0 (Windows; U; Windows NT 5.2; en-US) AppleWebKit/532.9 (KHTML, like Gecko) Chrome/5.0.310.0 Safari/532.9",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.7 (KHTML, like Gecko) Chrome/7.0.514.0 Safari/534.7",
    "Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US) AppleWebKit/534.14 (KHTML, like Gecko) Chrome/9.0.601.0 Safari/534.14",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.14 (KHTML, like Gecko) Chrome/10.0.601.0 Safari/534.14",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.20 (KHTML, like Gecko) Chrome/11.0.672.2 Safari/534.20",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/534.27 (KHTML, like Gecko) Chrome/12.0.712.0 Safari/534.27",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/13.0.782.24 Safari/535.1",
    "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/535.2 (KHTML, like Gecko) Chrome/15.0.874.120 Safari/535.2",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.7 (KHTML, like Gecko) Chrome/16.0.912.36 Safari/535.7",
    "Mozilla/5.0 (Windows; U; Windows NT 6.0 x64; en-US; rv:1.9pre) Gecko/2008072421 Minefield/3.0.2pre",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.10) Gecko/2009042316 Firefox/3.0.10",
    "Mozilla/5.0 (Windows; U; Windows NT 6.0; en-GB; rv:1.9.0.11) Gecko/2009060215 Firefox/3.0.11 (.NET CLR 3.5.30729)",
    "Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6 GTB5",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; tr; rv:1.9.2.8) Gecko/20100722 Firefox/3.6.8 ( .NET CLR 3.5.30729; .NET4.0E)",
    "Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:2.0.1) Gecko/20100101 Firefox/4.0.1",
    "Mozilla/5.0 (Windows NT 5.1; rv:5.0) Gecko/20100101 Firefox/5.0",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0a2) Gecko/20110622 Firefox/6.0a2",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:7.0.1) Gecko/20100101 Firefox/7.0.1",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:2.0b4pre) Gecko/20100815 Minefield/4.0b4pre",
    "Mozilla/4.0 (compatible; MSIE 5.5; Windows NT 5.0 )",
    "Mozilla/4.0 (compatible; MSIE 5.5; Windows 98; Win 9x 4.90)",
    "Mozilla/5.0 (Windows; U; Windows XP) Gecko MultiZilla/1.6.1.0a",
    "Mozilla/5.0 (Windows; U; Win98; en-US; rv:1.4) Gecko Netscape/7.1 (ax)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:48.0) Gecko/20100101 Firefox/48.0"]

def getHtmlContent(url):
    """
    use requests to get content
    """
    ## TODO: use the same user agent for related url, that makes it more like real-world browsing
    if url.startswith("javascript:"):
        rootLogger.debug("skip javascript: %s" %(url))
        return None
    for _ in range(3):  # retry if status_code is not ok
        try:
            r = requests.get(url, headers={'User-Agent':random.choice(agents)})
        except requests.exceptions.InvalidSchema as e:
            rootLogger.error("InvalidSchema: %s" % (e) )
            raise e
        except Exception as e:
            rootLogger.exception("Unexpected error: %s" % (e) )
            raise e
        if r.status_code == requests.codes.ok :
            return r.content
        rootLogger.warn("attemp failed, will retry")
        time.sleep(5) # wait
    rootLogger.warn("return code (%s) not ok for: %s" % (r.status_code, url) )
    #r.raise_for_status()
    return None

def getSoup(url):
    """
    get content and parse with beautifulsoup
    """
    html = getHtmlContent(url)
    if html is None:
        return None
    soup = BeautifulSoup(html, 'html.parser')
    return soup

def getPostImgUrls(url):
    """
    retrieve these info:
      title
      text content, only first 100 char
      image urls
    """
    x_soup = getSoup(url)
    if x_soup is None:
        return {'url': url}
    x_title = ''.join(x_soup.title.text.splitlines())
    rootLogger.info("got soup from: %s %s" % (url, x_title) )

    ## the following is for ent.news.cn as of July 2017. modifications might be needed for parsing other websites
    x_detail = x_soup.find(attrs={"id": "p-detail"})
    if x_detail is None: # for news.xinhuanet.com/politics
        x_detail = x_soup.find(attrs={"id": "content"})
    if x_detail is None:
        return {'url': url}
    ## remove some tags
    [s.extract() for s in x_detail.find_all(attrs={"class": "lb"})]
    [s.extract() for s in x_detail.find_all(attrs={"id": "jc_close1"})]

    x_text = ''.join(x_detail.text.replace(u'\xa0', u' ').splitlines())[0:100]
    x_text = ' '.join(x_text.split()) # remove leading space, replace multiple space with single space
    imgtags = x_detail.find_all('img', src=True)
    imgurls = [tag['src'] for tag in imgtags] # could be relative
    #imgurls = [urljoin(url, tag['src']) for tag in imgtags] # full url

    # if x_detail.find(attrs={"class": "nextpage"}, text=u'\u4e0b\u4e00\u9875') is not None:
    #x_nextpage_tags = x_detail.find_all('a', text=u'\u4e0b\u4e00\u9875')
    x_nextpage_tags = x_detail.find_all('a', text=u'下一页') # 下一页
    if x_nextpage_tags:  # if not empty
        next_url = x_nextpage_tags[0]['href']  # use only first link
        next_url = urljoin(url, next_url)
        time.sleep(1)
        next_res = getPostImgUrls(next_url)
        imgurls = imgurls + next_res['imgurls']

    return {'url': url, 'title': x_title, 'text': x_text, 'imgurls': imgurls }

def getPostImgUrls_mmjpg(url):
    """
    retrieve these info:
      title
      text content, only first 100 char
      image urls
    """
    x_soup = getSoup(url)
    if x_soup is None:
        return {'url': url}
    x_title = ''.join(x_soup.title.text.splitlines())
    rootLogger.info("got soup from: %s %s" % (url, x_title) )

    ## the following is for mmjpg.com as of October 2017
    x_info = x_soup.find(attrs={"class": "info"})
    if x_info is None:
        return {'url': url}
    x_info = [s.text.encode("utf-8") for s in x_info.find_all("i")]

    x_keywords = x_soup.find(attrs={"class": "tags"})
    x_keywords = [s.text.encode("utf-8") for s in x_keywords.find_all("a")]

    x_text = ' '.join(x_info + ["tag:"] + x_keywords)

    picinfo = x_soup.find(attrs={"type": "text/javascript"}, text=re.compile('var picinfo.*'))
    picinfo = re.search(r'picinfo\s+=\s+\[(\d+),(\d+),(\d+)\]', picinfo.text).groups()
    picinfo = [int(s) for s in picinfo]
    imgurls = []
    for p in range(picinfo[2]):
        imgurls.append("http://img.mmjpg.com/%d/%d/%d.jpg" % (picinfo[0], picinfo[1], (p + 1)))

    return {'url': url, 'title': x_title, 'text': x_text, 'imgurls': imgurls }


def url_to_bgrImg_old(url):
    """
    given a url, download the image, convert and read it into OpenCV format (BGR mode)
    return object type: numpy.ndarray 
    """
    resp = requests.get(url)
    if resp.status_code == requests.codes.ok:
        image = np.asarray(bytearray((StringIO(resp.content).read())), dtype="uint8")
        bgrImg = cv2.imdecode(image, cv2.IMREAD_COLOR)
        return bgrImg
    else:
        rootLogger.error("return code not ok: %s" % (r.status_code) )
        return None

def url_to_bgrImg(url):
    """
    given a url, download the image, convert and read it into OpenCV format (BGR mode)
    return object type: numpy.ndarray 
    """
    # TODO: what if resp_content is None?
    resp_content = getHtmlContent(url)
    image = np.asarray(bytearray((StringIO(resp_content).read())), dtype="uint8")
    bgrImg = cv2.imdecode(image, cv2.IMREAD_COLOR)
    return bgrImg

def file_to_bgrImg(imgPath):
    """
    given a local file, read it into OpenCV format (BGR mode)
    return object type: numpy.ndarray 
    """
    bgrImg = cv2.imread(imgPath, cv2.IMREAD_COLOR)
    if bgrImg is None:
        raise Exception("Unable to load image: {}".format(imgPath))
    #rgbImg = cv2.cvtColor(bgrImg, cv2.COLOR_BGR2RGB)
    return bgrImg


class webFace:
    def __init__(self):
        modelDir = os.path.join('/root/openface/models')  # docker image bamos/openface
        dlibFaceLandmarksPath = os.path.join(modelDir, 'dlib', 'shape_predictor_68_face_landmarks.dat')
        openfaceModelPath = os.path.join(modelDir, 'openface', 'nn4.small2.v1.t7')
        self.imgDimResize = 96
        self.align = openface.AlignDlib(facePredictor=dlibFaceLandmarksPath)
        self.net = openface.TorchNeuralNet(model=openfaceModelPath, imgDim=self.imgDimResize)

    def getRepsFromImg(self, bgrImg, multiple=True, bboxArea=6400):
    
        """
        given an opencv image (from imread or imdecode, BGR mode)
        detect faces, align, and calculate representations.
        please note, the rep returned from openface is numpy array, but is converted into list
        returns a list of all face reps
        """
        start = time.time()
        bgrImg = bgrImg
        rgbImg = cv2.cvtColor(bgrImg, cv2.COLOR_BGR2RGB)
        #print("  + Original size: {}".format(rgbImg.shape))
    
        if multiple:
            bbs = self.align.getAllFaceBoundingBoxes(rgbImg)
        else:
            bb1 = self.align.getLargestFaceBoundingBox(rgbImg)
            bbs = [bb1]
    
        reps = []
        for bb in bbs:
            ## skip small faces. TODO: use size of specific landmarks (distance between two eyes, or distance from eye to nose), instead of box area. 
            if bb.area() < bboxArea:
                rootLogger.debug("  + small face at %s, width x height: %d x %d, area: %d" % (bb.center(), bb.width(), bb.height(), bb.area()) )
                continue
            rootLogger.debug("  + big face at %s, width x height: %d x %d, area: %d" % (bb.center(), bb.width(), bb.height(), bb.area()) )
            alignedFace = self.align.align(imgDim=self.imgDimResize, rgbImg=rgbImg, bb=bb,
                                      landmarkIndices=openface.AlignDlib.OUTER_EYES_AND_NOSE)
            if alignedFace is None:
                raise Exception("Unable to align image: {}".format("url"))
    
            rep = self.net.forward(alignedFace)
            reps.append(rep.tolist())
            #reps.append(rep.tolist()[0:3]) # for testing purpose, keep only the first few numbers
        rootLogger.debug("+ %d faces, processed in %.2f seconds" % (len(bbs), time.time() - start) )
        return reps


def calDist(q_arr, s_arr):
    """
    calculate distances of q_arr (1D array) to each item (with the same shape as q_arr) in s_arr
    q_arr = np.array([1, 1, 1])
    s_arr = np.array([[0, 0, 0], [1, 1, 0]]) # or np.array([0, 0, 0])
    """
    if len(s_arr.shape) == 1:
        dist = np.linalg.norm(q_arr - s_arr, axis=0)
    elif len(s_arr.shape) == 2:
        dist = np.linalg.norm(q_arr - s_arr, axis=1)
    else:
        raise Exception("need 1D or 2D array. but received s_array with unexpected shape: %s" %(s_arr.shape,))
    return dist
