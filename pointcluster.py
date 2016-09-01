import os
import sys
from expand import *
import random

class PointCluster:
	'''
	Treating each cluster (calculated according to syntactic clustering) as a separate object
	'''
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

	'''
	Select next example from the cluster to present to expert for expansion
	'''
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

	'''
	Once an expert provides an example, save it 
	'''
	def addNewExample(self, point, desc):
		self.ep.addNewExample(point, desc)
		self.examples.append(point)
		print >> sys.stderr, "Cluster : %d . Example added : %s " % (self.clusternum, point)

	'''
	Apply the rules learned on all points
	'''
	def applyOnPoints(self):
		self.ep.applyOnPoints( self.points)
	
	'''
	RequiredPoints are the points which are required for a specific application.
	E.g the required points for a Rogue Zone application are only the zone temperature sensors and zone temperature setpoints
	If you want to expand and normalize all points, then this is simply the list of all points	
	'''	
	def addRequiredPoints(self, points):
		self.requiredPoints = list(points)

	'''
	Add all the points and ground-truth information
	'''
	def addPoints(self, points, groundtruth, correctTags):
		for point in points:
			self.points.append(point)
			self.gt[point] = groundtruth[point]
			self.correctTags[point] = correctTags[point]

		self.ep.init()
		self.incorrectQualifications = len(points)

	'''
	Setting the threshold of when this code should consider itself done.
	threshold can be 90%, 99% etc
	'''
	def setThreshold(self, threshold):
		self.threshold = threshold

	'''
	Applies the program synthesis and gets back the expanded normalized metadata
	We also store it in this object
	'''
	def getExpandedResults(self):
		[expandedPoints, keyPredicates, examples] =  self.ep.getData()
		self.expandedPoints = {}
		for point in self.points:
			if point not in expandedPoints:
				self.expandedPoints[point] = ""
				continue
			self.expandedPoints[point] = expandedPoints[point]

	'''
	Compute how many points remain to be normalized. Compare with ground truth.
	'''
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

	'''
	Check if you have expanded/normalized the required threshold of points
	'''
	def done(self):
		if self.correct > self.threshold * len(self.points):
			return True
		else:
			return False	
	
	'''
	Pick a random point from the remaining points to be expanded, to present to the expert
	'''
	def randomize(self):
		l = len(self.notDone)	
		if l == 0:
			return None
		randNumber = random.randint(0,l-1)
		newExample = self.notDone[randNumber]
		return newExample


	'''
	Pick the point which has minimum number of characters left to be expanded
	'''	
	def minLeft(self):
	
		for point in sorted(percentDone, key=percentDone.get, reverse=True):
			if point not in existingExamples and percentDone[point] < 99.0:
				exampleType.append("minLeft")
				return point

		return None

	'''
	Pick the point which has maximum number of characters left to be expanded
	'''	
	def maxLeft(self):
		for point in sorted(percentDone, key=percentDone.get):
			if point not in existingExamples and percentDone[point] < 99.0:
				exampleType.append("maxLeft")
				return point

		return None


	'''
	A more complex algorithm to select the next example.
	It tries to pick a point which has the most common unexpanded substring
	E.g if a substring VAV is unexplained in a lot of points, choose a point with that substring.
	The paper shows that this does not really give any significant advantage
	'''
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

