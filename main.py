#!/usr/bin/env python2
#

import time

start = time.time()

import argparse
import cv2
import itertools
import os
from openface.data import iterImgs

import numpy as np
np.set_printoptions(precision=2)

import openface
import pickle
import sys

fileDir = os.path.dirname(os.path.realpath(__file__))
modelDir = os.path.join(fileDir, 'models')
# modelDir = os.path.join('/root/openface/models')  # docker image bamos/openface
dlibModelDir = os.path.join(modelDir, 'dlib')
openfaceModelDir = os.path.join(modelDir, 'openface')

parser = argparse.ArgumentParser()

parser.add_argument('--targetDir', type=str, help="Path to raw images with faces of the target person.",
                    default="./rawimg/")
parser.add_argument('imgTest', type=str, nargs='+', help="Input images.")
parser.add_argument('--dlibFacePredictor', type=str, help="Path to dlib's face predictor.",
                    default=os.path.join(dlibModelDir, "shape_predictor_68_face_landmarks.dat"))
parser.add_argument('--networkModel', type=str, help="Path to Torch network model.",
                    default=os.path.join(openfaceModelDir, 'nn4.small2.v1.t7'))
parser.add_argument('--imgDim', type=int,
                    help="Default image dimension.", default=96)
parser.add_argument('--verbose', action='store_true')

args = parser.parse_args()

if args.verbose:
    print("Argument parsing and loading libraries took {} seconds.".format(
        time.time() - start))

start = time.time()
align = openface.AlignDlib(args.dlibFacePredictor)
net = openface.TorchNeuralNet(args.networkModel, args.imgDim)
if args.verbose:
    print("Loading the dlib and OpenFace models took {} seconds.".format(
        time.time() - start))


def getRep(imgPath):
    if args.verbose:
        print("Processing {}.".format(imgPath))
    bgrImg = cv2.imread(imgPath)
    if bgrImg is None:
        raise Exception("Unable to load image: {}".format(imgPath))
    rgbImg = cv2.cvtColor(bgrImg, cv2.COLOR_BGR2RGB)

    if args.verbose:
        print("  + Original size: {}".format(rgbImg.shape))

    start = time.time()
    bb = align.getLargestFaceBoundingBox(rgbImg)
    if bb is None:
        raise Exception("Unable to find a face: {}".format(imgPath))
    if args.verbose:
        print("  + Face detection took {} seconds.".format(time.time() - start))

    start = time.time()
    alignedFace = align.align(args.imgDim, rgbImg, bb,
                              landmarkIndices=openface.AlignDlib.OUTER_EYES_AND_NOSE)
    if alignedFace is None:
        raise Exception("Unable to align image: {}".format(imgPath))
    if args.verbose:
        print("  + Face alignment took {} seconds.".format(time.time() - start))

    start = time.time()
    rep = net.forward(alignedFace)
    if args.verbose:
        print("  + OpenFace forward pass took {} seconds.".format(time.time() - start))
        # print("Representation:")
        # print(type(rep))
        # print(rep)
        print("-----\n")
    return rep


fName = "./rep.pkl"
if os.path.isfile(fName):
    print("Loading mean representation from '{}'".format(fName))
    with open(fName, 'r') as f:
        (repMean, repMedian) = pickle.load(f)
else:
    # iter through images in input dir, get representations, calculate mean/median
    repList = list()
    imgs = list(iterImgs(args.targetDir))
    for imgObject in imgs:
        print("=== {} ===".format(imgObject.path))
        imgRep = getRep(imgObject.path)
        repList.append(imgRep)
    
    repAll = np.vstack(repList)
    print "=== representations:"
    print repAll.shape
    repMean   = np.mean(repAll, axis=0)
    repMedian = np.median(repAll, axis=0)
    
    # store in a pickle file
    print("Saving mean representation to '{}'".format(fName))
    with open(fName, 'w') as f:
        pickle.dump((repMean, repMedian), f)


# calculate distance between mean representation and test image
for imgtest in args.imgTest:
    try:
        imgRep = getRep(imgtest)
    except Exception as exc:
        print "Something unexpected happened:"
        print exc
        continue
    else:
        dmean   = repMean   - imgRep
        dmedian = repMedian - imgRep
        print("Squared l2 distance between mean   representation and test image ({}): {:0.3f}".format(imgtest, np.dot(dmean, dmean)))
        print("Squared l2 distance between median representation and test image ({}): {:0.3f}\n".format(imgtest, np.dot(dmedian, dmedian)))


