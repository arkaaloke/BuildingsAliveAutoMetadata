import os
import sys
from expand import *
import random

class PointCluster:
	def __init__(self, clusternum):
		self.points = []
		self.gt = {}
		self.correct = 0
		self.incorrect = 0
		self.requiredCorrect = 0

		self.correctTags = {}
		self.expandedPoints = []
		self.threshold = 90.0
		self.existingExamples = []
		self.ep = Expand()
		self.clusternum = clusternum
		self.requiredPoints = []
		self.notDone = []
		self.examples = []

		self.correctlyDone = []
		self.incorrectlyDone = []
		self.lastStringLeft = []

	def getNextExample(self, expType):
		
		newExample = None
		if expType == "random":
			newExample = self.randomize()
		elif expType == "maxleft":
			newExample = self.maxLeft() 
		elif expType == "minleft":
			newExample = self.minLeft()
		elif expType == "super":
			newExample = self.superClassifier()
		elif expType == "sameLeft":
			newExample = self.maxCommonLeft()
		if newExample == None:
			print "NO NEW EXAMPLES"

		return newExample

	def addNewExample(self, point, desc):
		self.ep.addNewExample(point, desc)
		self.examples.append(point)
		print >> sys.stderr, "Cluster : %d . Example added : %s " % (self.clusternum, point)

	def applyOnPoints(self):
		self.ep.applyOnPoints( self.points)
		
	def addRequiredPoints(self, points):
		self.requiredPoints = list(points)

	def addPoints(self, points, groundtruth, correctTags):
		for point in points:
			self.points.append(point)
			self.gt[point] = groundtruth[point]
			self.correctTags[point] = correctTags[point]

		self.ep.init()
		self.incorrectQualifications = len(points)

	def setThreshold(self, threshold):
		self.threshold = threshold

	def getExpandedResults(self):
		[expandedPoints, keyPredicates, examples] =  self.ep.getData()
		self.expandedPoints = {}
		for point in self.points:
			if point not in expandedPoints:
				self.expandedPoints[point] = ""
				continue
			self.expandedPoints[point] = expandedPoints[point]

	def computeRemaining(self):
		self.incorrect = 0
		self.correct = 0
		self.requiredCorrect = 0
		self.getExpandedResults()
		self.notDone = []
		self.correctlyDone = []
		self.incorrectlyDone = []
		for point in self.expandedPoints:
			print point, self.expandedPoints[point].strip().split(','), self.correctTags[point]
			tags = self.expandedPoints[point].strip().split(',')
			change1 = [ item for item in self.correctTags[point] if item not in tags ]
			change2 = [ item for item in tags if item not in self.correctTags[point] ]
			c = [ item for item in self.correctTags[point] if item in tags ]
			if len(change1) + len(change2) > 0:
				self.incorrect += 1
				if point not in self.examples:
					self.notDone.append(point)
				self.incorrectlyDone.append(point)
			else:
				self.correct += 1	
				self.correctlyDone.append(point)
				if point in self.requiredPoints:
					self.requiredCorrect += 1

		print >>sys.stderr, self.clusternum, "Incorrect : ",self.incorrect, "Correct :", self.correct
		return self.incorrect

	def done(self):
		if self.correct > self.threshold * len(self.points):
			return True
		else:
			return False	
	def randomize(self):
		l = len(self.notDone)	
		if l == 0:
			return None
		randNumber = random.randint(0,l-1)
		newExample = self.notDone[randNumber]
		return newExample


		
	def minLeft(self):
	
		for point in sorted(percentDone, key=percentDone.get, reverse=True):
			if point not in existingExamples and percentDone[point] < 99.0:
				exampleType.append("minLeft")
				return point

		return None

	def maxLeft(self):
		for point in sorted(percentDone, key=percentDone.get):
			if point not in existingExamples and percentDone[point] < 99.0:
				exampleType.append("maxLeft")
				return point

		return None


	def maxCommonLeft(self):
		amtLeft = {}
		stringsLeft = {}
		for point in self.expandedPoints:

			tempPoint = list(point)
			tags = self.expandedPoints[point].strip().split(',')
			if len(tags) == 0:
				percentDone[point] = 0
				continue
			#print tags
			for tag in sorted(tags, key=lambda t : len(t.strip().split(':')[-1]), reverse=True):
				k = tag.strip().split(':')[0]
				v = tag.strip().split(':')[-1]
				pointStatus = ''.join(tempPoint)
				if v in pointStatus:
					index = pointStatus.index(v)
					for i in range(index, index + len(v)):
						tempPoint[i] = 'x'

			pointStatus = ''.join(tempPoint)
			pointStatus = re.sub('\_|\:\.\-','x', pointStatus)
			partsLeft=  pointStatus.split('x')
			index = 0
			for part in partsLeft:
				if len(part.strip()) == 0:
					index += 1
					continue

				key = part.strip() + "-" + str(index)
				if key not in stringsLeft:
					stringsLeft[key] = {}
					stringsLeft[key]["count"] = 1
					stringsLeft[key]["strings"] = []
					stringsLeft[key]["strings"].append(point)
				else:
					stringsLeft[key]["count"]  += 1
					stringsLeft[key]["strings"].append(point)

				index += len(part.strip())

		for s in sorted(stringsLeft, key=lambda k: stringsLeft[k]["count"], reverse = True):
			if s in self.lastStringLeft:
				continue
			for p in stringsLeft[s]["strings"]:
				if p not in self.examples :
					print "max common left : ", s, stringsLeft[s], " returning : ", p
					print >> sys.stderr, "max common left : ", s
					self.lastStringLeft.append(s)
					return p
				
		return None

