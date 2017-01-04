# matchbox

## introduction
This tool tries to detect whether the test images are from the same person as the training images.

## steps
1. extract feature representations from training faces
2. calculate mean (or median)
3. extract feature representations from a test face
4. compare and calculate a distance estimate
5. images with a distance within the threshold are considered to be of the same person

## usage
Tested in docker container (bamos/openface).
example:
`python main.py --verbose  --targetDir /path/to/rawimg/Yifei_Liu/ /path/to/rawimg/Wei_Zhao/006-vi.jpg /path/to/rawimg/Wei_Zhao/007-vi.jpg | tee zhaowei-liuyifei.log`

## TODO:
improve distance estimation: instead of comparing test image with mean representaions, try to compare the test image with each training image, then check how many (80%-90%) of them pass a certain threshold.
