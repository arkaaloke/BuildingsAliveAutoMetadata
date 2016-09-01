import os
import sys
import signal

import ast
from expand import *
import random

from sklearn.cluster import KMeans
import numpy
import re
from sklearn.cluster import AgglomerativeClustering
import StringIO, pydot
from sklearn.metrics import pairwise_distances
from sklearn.cluster import DBSCAN
from pointcluster import *

from sklearn.feature_extraction.text import CountVectorizer as CV
from sklearn.cross_validation import StratifiedKFold
from sklearn.cross_validation import KFold
from sklearn.tree import DecisionTreeClassifier as DT
from sklearn.ensemble import RandomForestClassifier as RFC
from sklearn.ensemble import ExtraTreesClassifier as ETC
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.metrics import precision_score
from sklearn.metrics import recall_score
from sklearn.metrics import confusion_matrix as CM
from sklearn import tree
from sklearn.preprocessing import normalize
from collections import defaultdict

def readDumpFile(dumpFileName):
	readState(dumpFileName)

def writeDumpFile(dumpFileName):
	writeState(dumpFileName)


'''
This is the main script function
It takes the input original metadata, the ground-truth file already containing the normalized metadata and 
checks how well our algorithm performs
At each step this script checks which cluster the next example should be drawn from, which example to ask the expert
and learns the rules for that example, and applies them to all the points within the cluster
'''
def initialize(allPointsFile, filename, labelledExampleFile ):
	global allExamples
	global existingExamples
	global numFullyQualified
	global result
	global prevExpansion
	global exampleType
	global wrongBoolClassified
	global overClassified
	global numExamplesChanged
	global wrongPoints
	global incorrectQualifications
	global correctlyClassified
	global haystacktags 
	global lastStringLeft
	global correctTagIdentification
	global threshold
	global expType
	global correctlyClassifiedRequired
	global clusters
	global clusternum
	global dataBased
	global dataBasedLearningType
	global reqd_metadata_file
	global num_agnostic_learning_steps
	

	correctlyClassifiedRequired = []
	correctTagIdentification = []
	lastStringLeft = []
	haystacktags = {}	
	wrongPoints = {}
	correctlyClassified = []
	prevExpansion = {}
	numFullyQualified = {}
	exampleType = []
	wrongBoolClassified = []
	overClassified = []
	numExamplesChanged = []
	incorrectQualifications = []
	#incorrectFullQualifications = []
	noQualifications = []
	getAllExamples(labelledExampleFile, filename)
	clusterPoints()
	result = None
	oldExampleNum = 0
	for i in range(len(existingExamples)) :	
		numFullyQualified[i] = 0
		exampleType.append("initial")
		wrongBoolClassified.append(0)
		overClassified.append(0)
		numExamplesChanged.append(0)
		incorrectQualifications.append(len(allExamples))
		noQualifications.append(0)
		correctlyClassified.append(0)
		correctlyClassifiedRequired.append(0)
		correctTagIdentification.append(0)


	fout = open(sys.argv[2].strip() + "-out", "w")
	print >> fout , "Example id, fullyQualified, incorrectly Qualified, Required Fully Qualified, Cluster, Example , DATA-BASED? "

	data_based_file = open(sys.argv[2].strip() + "-data-based" , "w")	
	readDataFVS()
	examplenum = 0
	while True:

		dataBased = False
		nextCluster = None
		newExample = None   
		if examplenum >= num_agnostic_learning_steps :
			temp = getNextCluster()
			newExample = getDataBasedExample(examplenum, dataBasedLearningType, data_based_file)
			if newExample == None:
				nextCluster = getNextCluster()
				newExample = clusters[nextCluster].getNextExample(expType)

			dataBased = True
			for i in range(numclusters):
				if newExample in clusters[i].points:
					nextCluster = i
					break
		else:
			nextCluster = getNextCluster()
			newExample = clusters[nextCluster].getNextExample(expType) 


		examplenum += 1 
		if newExample == None:
			break
		print "Trying to add new example : ", newExample, allExamples[newExample]

		clusters[nextCluster].addNewExample(newExample, allExamples[newExample])
		clusters[nextCluster].applyOnPoints()

		print "Result : "
		print result

		numExamples = len(existingExamples)
		allDone = True
		for i in range(numclusters):
			flag = clusters[i].done()
			if flag == False:
				allDone = False
	
		if flag == True:
			print "DONE"
			break

		correctlyClassified = sum( clusters[i].correct for i in range(numclusters) )
		incorrectQualifications = sum(clusters[i].incorrect for i in range(numclusters) )
		correctlyClassifiedRequired = sum( clusters[i].requiredCorrect for i in range(numclusters) )
		
		print >>fout , i,  ",", correctlyClassified,  ",", incorrectQualifications,  ",", correctlyClassifiedRequired , "," , nextCluster , ",", newExample , "," , str(dataBased)

		if correctlyClassifiedRequired == len(open(reqd_metadata_file).readlines()) :
			break


'''
Read pre-computed feature vectors (based on data) of each data stream
Filename for my local installation --- SodacollectedData-fv
'''
def readDataFVS():
	lines = open("SodacollectedData-fv").readlines()
	global datafvs
	datafvs = {}
	for line in lines:
		pointName = line.strip().split(";")[0].strip()
		parts = line.strip().split(";")[-1].strip().split(",")
		arr = []
		for part in parts:
			arr.append(float(part))

		datafvs[pointName] = numpy.array(arr)

'''
Learn on data already learned, based on data-based feature vector
'''
def getDataBasedExample(examplenum, expType, outfile):
	global clusters
	global numclusters
	global datafvs
	global sensorTypeLabels
	global reqd_metadata_label_indices

	pointsdone = []
	pointsnotdone = []
	for i in range(numclusters):
		pointsdone.extend(clusters[i].correctlyDone)
		pointsnotdone.extend(clusters[i].incorrectlyDone)

	trainingData = []
	trainingLabels = []
	testData = []
	for point in pointsdone:
	 	trainingData.append(datafvs[point])
		trainingLabels.append(sensorTypeLabels[point])

	clf = RFC(n_estimators=50, criterion='entropy')
 	clf.fit(trainingData, trainingLabels)

	exampleToReturn = None
	tp = 0
	fp = 0
	tot = 0
	possibleExamples = []
	possibleCorrectExamples = []
	for point in pointsnotdone:
		pred = clf.predict( datafvs[point] )
		sorted_proba = sorted( clf.predict_proba( datafvs[point] ) )
		proba = sorted_proba[-1] - sorted_proba[-2]
		
		if pred[0] in reqd_metadata_label_indices:
			possibleExamples.append((point, proba))
		if point in requiredPoints:
			tot += 1
			if pred[0] == sensorTypeLabels[point]:
				possibleCorrectExamples.append( point )
				tp += 1
			else:
				print "True Negative : ", point
		else:
			if pred[0] in reqd_metadata_label_indices:
				fp += 1

	if expType == "random":
		if len(possibleExamples) > 0 :
			exampleToReturn = possibleExamples[ random.randint(0, len(possibleExamples) - 1 ) ][0]
	if expType == "maxLikelihood":
		if len(possibleExamples) > 0:
			exampleToReturn = sorted( possibleExamples, key=lambda k:k[1] , reverse=True )[0][0]
	if expType == "manual":
		if len(possibleCorrectExamples) > 0:
			exampleToReturn = possibleCorrectExamples [ random.randint( 0, len(possibleCorrectExamples) - 1 ) ]

	print "DATA-BASED : ", examplenum, tp, fp, tot, len(pointsnotdone) , exampleToReturn
	print >> outfile, examplenum, tp, fp, tot, len(pointsnotdone) , exampleToReturn
	return exampleToReturn

'''
Choose next cluster to normlize
Here the algorithm is simply to choose the cluster based on which has maximum number of points not yet expanded
'''
def getNextCluster( ):
	global numclusters
	global clusters
	c = 0
	maxRemaining = -1
	for i in range(numclusters):
		rem  = clusters[i].computeRemaining()
		if rem > maxRemaining : 
			maxRemaining = rem
			c = i
	
	print "Next choosing cluster : ", c
	return c


'''
Read all the ground truth file where the normalized metadata already exists.
This will automate the process of figuring out how well our technique does
'''
def getAllExamples(exampleFileName, filename):
	global existingExamples
	global allExamples
	global correctTags
	global requiredPoints
	global sensorTypeToLabelMapping 
	global sensorTypeLabels
	global reqd_metadata_label_indices
	global sensorTypes

	sensorTypes = {}
	sensorTypeLabels = {}
	correctTags = {}
	existingExamples = []
	allExamples = {}
	lines = open(exampleFileName).readlines()
	count = 0
	sensorTypeToLabelMapping = []
	sensorTypeLabels = {}

	f = open(filename, "w")
	while count + 2 <= len(lines):
		pointName = lines[count].strip()
		desc = lines[count+1].strip()
		allExamples[pointName] = desc
		correctTags[pointName] = []
		sensorType = desc.split(',')[-1].split(":")[0]
		if "-id" not in sensorType:
			if sensorType not in sensorTypeToLabelMapping:
				sensorTypeToLabelMapping.append(sensorType) 
			sensorTypes[pointName] = sensorType
			sensorTypeLabels[pointName] = sensorTypeToLabelMapping.index(sensorType)
		else:
			sensorType = desc.split(',')[-2].split(":")[0]
			sensorTypes[pointName] = sensorType
			if sensorType not in sensorTypeToLabelMapping:
				sensorTypeToLabelMapping.append(sensorType) 
			sensorTypeLabels[pointName] = sensorTypeToLabelMapping.index(sensorType)

		for tag in desc.split(','):
			[ t, v, c ] = tag.strip().split(':')
			if c == 'c':
				correctTags[pointName].append( t + "=" + v + ":" + v )
			else:
				correctTags[pointName].append( t + ":" + v )

		if count <=1:
			existingExamples.append(pointName)
			f.write(str(pointName) + "\n")
			f.write(str(desc) + "\n")

		count += 2

	
	#print "CORRECT TAGS : ",
	#print correctTags
	f.close()

	requiredPoints = []
	lines = open("SODA-REQUIRED-METADATA").readlines()
	for line in lines:
		if line.strip() == "":
			continue
		requiredPoints.append(line.strip())
	reqd_metadata_label_indices = []
	for point in requiredPoints :
		labelIndex = sensorTypeLabels[point]
		if labelIndex not in reqd_metadata_label_indices:
			reqd_metadata_label_indices.append(labelIndex)

'''
compute the apriori syntactic clustering feature vector
'''
def getFeatureVector2(point):
	global specialCharTable
	
	point = point.upper()
	fv = []	
	prevChar = None
	for i in range(len(point)):
		if len(re.compile('[A-Z]').findall(point[i])) == 1:
			fv.append(1)
		elif len(re.compile('[0-9]').findall(point[i])) == 1:
			fv.append(2)
		else:
			specialChar = point[i]
			if specialChar not in specialCharTable:
				val = len(specialCharTable) + 3
				specialCharTable[ specialChar ] = val
			fv.append( specialCharTable[ specialChar ] )


	string = ''.join( map(str, fv))
	for i in range(0, 10):
		string = re.sub(str(i) + "+", str(i) , string)
	return list(string)

'''
Create a matrix with all feature vectors
''' 
def createMatrix( pointList, allPoints, fvs ):
	x = []
	for point in pointList:
		index = allPoints.index( point )
		x.append(fvs[index])

	return x

''' 
create the apriori syntactic clustering of points
'''
def clusterPoints( ):
	global allExamples
	global specialCharTable
	global hierarchy
	global points
	global final_leaves
	global clusters
	global clusternum

	specialCharTable = {}
	fvs = []
	points = []
	maxLen = 0
	for pointName in allExamples:
		fv =  getFeatureVector2( pointName )
		points.append(pointName)
		maxLen = max( maxLen, len(fv) )
		fvs.append( fv )
		

	for i in range(len(fvs)):
		if len(fvs[i]) == maxLen:
			continue
		else :
			currLen = len(fvs[i])
			for j in range( currLen , maxLen):
				fvs[i].append( 0 )

	obs = None
	print "Calculating obs matrix"
	obs = numpy.array(fvs)	
	print " Fitting"
	clf = None
	clf = AgglomerativeClustering(n_clusters=2, affinity='precomputed', linkage='average')
	x = createMatrix (points, points, fvs)
	distn = pairwise_distances( x , metric='jaccard')
	clf.fit(distn)
	L = clf.children_

	hierarchy = {}
	strings = {}
	hierarchy[0] = []
	labels_written = []
	for i in range(len(points)):
		hierarchy[i] = []
		hierarchy[i].append(points[i])
		strings[i] = points[i]
	count = i + 1
	numLeaves = 0 
	print "Number of clusters : ", len(L)
	leaves = []
	parents = []
	for j in range(len(L)):
		cluster1 = int(L[j][0])
		cluster2 = int(L[j][1])
		hierarchy[count] = []
		hierarchy[count].extend(hierarchy[cluster1])
		hierarchy[count].extend(hierarchy[cluster2])
		x = createMatrix( hierarchy[cluster1],  points , fvs )
		y = createMatrix( hierarchy[cluster2], points, fvs )
		print "Resulting cluster ",count," : From (%d,%d)" % (cluster1, cluster2)
		distn = pairwise_distances( x, y  , metric='jaccard').mean()
		arr = []

		if distn < 0.01:
			count += 1
			continue
		leaves.append(cluster1)
		leaves.append(cluster2)
		parents.append(count)
		count += 1


	final_leaves = []
	for i in leaves:
		if i not in parents:
			final_leaves.append(i)

	print "Number of leaves : ", len(final_leaves)
	
	leaf_sizes = []
	for c in final_leaves:
		leaf_sizes.append( (c, len( hierarchy[c]) ) )

	subcluster()

'''
Subcluster if necessary within the clusters
'''
def subcluster(opt="none"):
	global hierarchy
	global final_leaves
	global cluster_number
	global all_clusters
	global clusters
	global numclusters

	clusters = []
	numclusters = 0
	cluster_number = 0
	all_clusters = {}
	'''

	SUB-CLUSTERING 

	'''
	maxLen = 0
	fvs = []
	for point in points:
		fv =  getFeatureVector1( point )
		maxLen = max( maxLen, len(fv) )
		fvs.append( fv )
		

	for i in range(len(fvs)):
		if len(fvs[i]) == maxLen:
			continue
		else :
			currLen = len(fvs[i])
			for j in range( currLen , maxLen):
				fvs[i].append( 0 )



	for l in sorted(final_leaves, key=lambda k: len(hierarchy[k]) ):
		if len( hierarchy[l] ) < 5:
			continue

		if opt == "dbscan":
			dbscan( hierarchy[l], points, fvs, 0.3, 10, 'euclidean' )
		elif opt == "none":
			none( hierarchy[l])

	os.system("rm " + sys.argv[1] + "-*")
	ground_truth_file = sys.argv[1].split("-")[0].strip() + "-GROUND-TRUTH"
	lines = open(ground_truth_file).readlines()
	global gt
	gt = {}
	for i in range(len(lines)/2):
		gt[lines[i*2].strip()] = lines[i*2 + 1].strip()	

	count = 0
	
	for c in sorted(all_clusters, key=lambda k:len(all_clusters[k]), reverse=True):
		splitFile(all_clusters[c], count)
		count += 1
		numclusters += 1

'''
split the input file into a separate file for each cluster
'''
def splitFile(pointList, clusternum):
	global gt
	global clusters
	global requiredPoints

	print "++ NEW CLUSTER ++ "
	print clusternum , pointList	
	p = PointCluster( clusternum )
	p.addPoints(pointList, gt, correctTags)
	p.addRequiredPoints( requiredPoints ) 
	clusters.append( p )
	print len(clusters)

if __name__ == "__main__":
	global threshold
	global expType
	global dataBased
	global dataBasedLearningType
	global reqd_metadata_file
	global num_agnostic_learning_steps
	
	dataBased = False
	expType = "sameLeft"
	dataBasedLearningType = "random"

	'''
	arg 1 : original metadata
	arg 2 : example file
	arg 3 : ground truth
	arg 4 : syntactic active learning parameter
	arg 5 : syntactic threshold
	arg 5 : data based?
	arg 6 : data based active learning parameter : manual/maxLikelihood/random
	arg 7 : required metadata file
	arg 8 : num agnostic learning
	'''
	if len(sys.argv) < 8:
		print "python ActiveLearning.py SODA-ORIGINAL-METADATA l-ex-random SODA-GROUND-TRUTH sameLeft 0.1 dataBased random SODA-REQUIRED-METADATA 5"
	if sys.argv[5] == "dataBased":
		dataBased = True
	dataBasedLearningType = sys.argv[6]
	reqd_metadata_file = sys.argv[7]
	num_agnostic_learning_steps = int(sys.argv[8])
	if dataBased == False:
		num_agnostic_learning_steps = sys.maxint

	#signal.signal(signal.SIGINT, signal_handler)
	threshold = float(sys.argv[5].strip())
	expType = str(sys.argv[4].strip())
	initialize(sys.argv[1], sys.argv[2], sys.argv[3])


