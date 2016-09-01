import os
import re
import sys
import string
from libexamplelearning import *
import ast

class Expand:
	def __init__(self):
		self.types = {}
		self.points_not_classified = []
		self.keys = []
		self.synonyms = []
		self.sensorTypeCounts = {}
		self.oneOffs = {}

	'''
	If two groups of characters map to the same expanded string
	'''
	def putSynonyms(self, newString,syn,key):
		for group in self.synonyms:
			if (syn,key) in group:
				group.append((newString,key))


	'''
	Get synonyms for a particular key
	'''
	def getSynonyms(self, string,key):
		for group in self.synonyms:
			if (string,key) in group:
				return [ s for (s,k) in group ]


	'''
	Given a new example, learn new rules for expansion, and merge them with all the rules learned till this point
	'''
	def learnIndividualExample(self, example,point, oneOff=False):
		if oneOff == True:
			self.oneOffs[point] = {}
			self.oneOffs[point]["example"] = example
			self.oneOffs[point]["expansion"] = ""
			for i in range(len(example["keyOrder"])):
				(key, value, t) = example["keyOrder"][i]
				snippet = key
				if t == 'c':
					snippet = key + "=" + value + ":" + value
				else:
					snippet = key + ":" + value
				if i != len(example["keyOrder"]) - 1:
					self.oneOffs[point]["expansion"] += snippet + ","
				else:
					self.oneOffs[point]["expansion"] += snippet
	 
			return


		sensorType = example["sensorType"]
		if point not in self.examples:
			self.examples[point] = {}
		print example
		keyOrder = example["keyOrder"]

		for i in range(len(keyOrder)):			
			(key, v, t) = keyOrder[i] 
			if key == "sensorType" or key == "keyOrder":
				continue

			value = example[key]["value"]
			valueType = example[key]["type"]
			pos = example[key]["pos"]

			keyName = key
			if valueType == 'c':
				keyName = key + "=" + value
			elif "-id" in key and key.split('-id')[0].strip() in example:
					labelname = key.split('-id')[0].strip()
					keyName = key + "&" + labelname + ":::" + example[labelname]["value"]
			
			if keyName not in self.examples[point]:
					self.examples[point][keyName] = {}

			if keyName not in self.keys:
				self.keys.append(keyName)

			self.examples[point][keyName]["value"] = example[key]["value"]
			self.examples[point][keyName]["type"] = example[key]["type"]
			self.examples[point][keyName]["pos"] = example[key]["pos"]
			leftKeys = []
			for (k, v, t) in keyOrder:
				if k != key:
					if t == 'c':
						leftKeys.append((k + "=" + v, example[k]["pos"]))
				else:
					break

			self.examples[point][keyName]["leftKeys"] = leftKeys

			rightKeys = []
			flag = 0
			for (k, v, t) in keyOrder:
				if k != key and flag == 0:
					continue
				if k == key:
					flag = 1
					continue
				if k!= key and flag == 1:
					if t == 'c':
						rightKeys.append(( k + "=" + v, example[k]["pos"] ))
			self.examples[point][keyName]["rightKeys"] = rightKeys
			self.examples[point][keyName]["allKeys"] = []
			for (k, v, t) in keyOrder:
				if t == 'c':
					self.examples[point][keyName]["allKeys"].append(( k + "=" + v, example[k]["pos"])) 
			#print point, keyName, examples[point][keyName]


		for key in self.examples[point]:
			#print "key = ",key, 
			possibilities = generateAllPossibleOptions(point, key, self.examples[point][key]["value"], self.examples[point][key]["type"], self.examples[point][key]["pos"], self.examples[point][key]["leftKeys"], self.examples[point][key]["rightKeys"] ) 
			self.examples[point][key]["possibilities"] = possibilities
			#print key, possibilities
		#print "learned regex for point : ", point
		#print examples[point][key]["possibilities"]

		#print examples[point]
		
	'''
	Merge (intersect) the rules learned for a point with all other rules learned till now 
	'''	
	def intersectKeyPossibilitiesSingle(self, point, findClassifier):
		count = 1
		numKeys = len(self.keys)
		for key in self.examples[point]:
			#print "key : ",key
			if key not in self.keyPredicates:
				self.keyPredicates[key] = {}
				self.keyPredicates[key]["examples"] = [ point ]
				self.keyPredicates[key]["transformation"] = [ self.examples[point][key]["possibilities"] ]
				self.keyPredicates[key]["match"] = []
			else:
				traceSets = self.keyPredicates[key]["transformation"][:]
				pointList = self.keyPredicates[key]["examples"][:]
				traceSets.append( self.examples[point][key]["possibilities"])
				pointList.append(point)
				print "Came here : "
				(points, intersectedSet) = mergeKeyPossibilities(key, traceSets, pointList)

				#print "Number of intersected sets = ",len(points)
				self.keyPredicates[key]["examples"] = points
				self.keyPredicates[key]["transformation"] = self.sortSet(intersectedSet)

		if findClassifier == False:
			return

		for key in self.keys:	
			self.keyPredicates[key]["match"] = []
			print key
			for i in range(len( self.keyPredicates[key]["examples"] )):
				print "Intersected Points ", self.keyPredicates[key]["examples"][i]
				remainingPoints = [ p for p in self.examples if p not in self.keyPredicates[key]["examples"][i].split(';') ]
				pred = None
				if "=" in key:
					value = key.split('=')[-1].strip()
					pred = findBooleanExpression( self.keyPredicates[key]["examples"][i].split(';'), remainingPoints, self.examples, value)
				else:
					pred = findBooleanExpression( self.keyPredicates[key]["examples"][i].split(';'), remainingPoints, self.examples)

				print "Predicate",pred 
				print "Transformation rule : ", self.keyPredicates[key]["transformation"][i]
				self.keyPredicates[key]["match"].append(pred)

			print "Done key : ",key, count , "/", numKeys
			count += 1
			print "\n\n"
	'''
	Same as previous function: Merge (intersect) the rules learned for a point with all other rules learned till now 
	However this function assumes that you are starting from initializing.
	Bad coding. Should probably merge this with previous function
	'''	

	def intersectKeyPossibilities(self):

		self.keyPredicates = {}
		count = 1
		numKeys = len(self.keys)
		for key in self.keys:
			if key not in self.keyPredicates:
				self.keyPredicates[key] = {}
				self.keyPredicates[key]["examples"] = []
				self.keyPredicates[key]["transformation"] = []
				self.keyPredicates[key]["match"] = []

			traceSets = []
			pointList = []
			for point in self.examples:
				if key in self.examples[point]:
					traceSets.append( examples[point][key]["possibilities"])
					pointList.append(point)
			(points, intersectedSet) = mergeKeyPossibilities(key, traceSets, pointList)

			self.keyPredicates[key]["examples"] = points
			self.keyPredicates[key]["transformation"] = self.sortSet(intersectedSet)
		
			print "key : ",key
			for i in range(len( points)):
				print "Intersected Points ", points[i]
				remainingPoints = [ p for p in examples if p not in points[i].split(';') ]
				if "=" in key:
					value = key.split('=')[-1].strip()
					pred = self.findBooleanExpression( self.keyPredicates[key]["examples"][i].split(';'), remainingPoints, self.examples, value)
				else:
					pred = self.findBooleanExpression( self.keyPredicates[key]["examples"][i].split(';'), remainingPoints, self.examples)


				print "Predicate",pred 
				print "Transformation rule : ",intersectedSet[i]
				self.keyPredicates[key]["match"].append(pred)

			print "Done key : ",key, count , "/", numKeys
			count += 1
	 
			print "\n\n"

	'''
	sort a set of regular expression according to size of regular expressions
	This helps choose the simplest regular expression to apply on a point
	'''
	def sortSet(self, unsortedSet):
		print "=======UNSORTED SET ========="
		for i in range(len(unsortedSet)):
			d = unsortedSet[i]
			d['right'] = sorted(d['right'], key=lambda key:len(str(key)))
			d['left'] = sorted(d['left'], key=lambda key:len(str(key)))	
		print unsortedSet 
		return unsortedSet
		

	'''
	If there is a file write the current set of rules and state into that file.
	Is not used when running the evaluation script with ground truth files
	'''
	def writeState(self, filename):
		f = open(filename, "w")
		f.write(str(self.keys) + "\n")
		f.write(str(self.keyPredicates) + "\n")
		f.write(str(self.examples) + "\n")

	def getKeys(self):
		return self.keys
			
	'''
	Reads the state file and populates the set of rules
	Is not used when running the evaluation script with ground truth files
	'''
	def readState(self, filename):
		lines = open(filename).readlines()
		self.keys = ast.literal_eval(lines[0].strip())
		self.keyPredicates = ast.literal_eval(lines[1].strip())
		self.examples = ast.literal_eval(lines[2].strip())

	def init(self):
		self.examples = {}
		self.sensorTypeCounts = {}
		self.intersectKeyPossibilities()
		self.initializeGlobal()

	'''
	Initialize Global variables
	'''
	def initializeGlobal(self):
		print " Initializing global variables "
		self.expandedPoints = {}
		self.keyPredicates = {}
		self.examples = {}

		print "Initialized variables : ",self.expandedPoints, self.keyPredicates, self.examples


	'''
	Generates the rules and possible regular expression breakdowns of a particular new example provided by the expert
	'''	
	def learnPointExample(self, pointName, expl):
		initial_pos = 0
		example = {}
		parts = expl.split(',')
		key_order = []
		print pointName, expl
		for part in parts:
			key = part.strip().split(':')[0].strip()
			value = part.strip().split(':')[1].strip()
			example[key] = {}
			example[key]["value"] = value
			example[key]["type"] = part.strip().split(':')[-1].strip()
			#print pointName, initial_pos, value
			pos = pointName[initial_pos:].index(value)
			example[key]["pos"] = pos + initial_pos
			#print "Position of ",key," is ", example[key]["pos"]
			initial_pos += pos + len(value)

			if len(part.strip().split(':')) > 3:
				s = part.strip().split(':')[2].strip()
				example[key]["synonym"] = part.strip().split(':')[2].strip()	
				self.putSynonyms(value,s,key)
			
			key_order.append((key, example[key]["value"], example[key]["type"]))
		example["sensorType"] = parts[-1].strip()
		example["keyOrder"] = key_order
		#print example
		self.learnIndividualExample(example,pointName, False )


	'''
	Adds a new example which was just supplied by the expert
	'''
	def addNewExample(self, point, desc, findClassifier=True):
		self.sensorTypeCounts = {}
		self.learnPointExample(point, desc)
		if point in self.oneOffs:
			return
		self.intersectKeyPossibilitiesSingle(point, findClassifier)

	'''
	Applies all the rules learned till now on all the points.
	This function is called from a `pointcluster` object , so the rules are only applied to that particular cluster
	'''
	def applyOnPoints(self, points):
		print "\n\nApplying on points"
		pointInfo = {}
		for point in points:
			print "Done point ", point
			if point in self.oneOffs:
				self.expandedPoints[point] = self.oneOffs[point]["expansion"]
				continue
			pointInfo[point] = []
			expandedString = ""
			for key in self.keyPredicates:
				if "&" in key:
					constantKeyPortion = key.split('&')[-1].strip()
					constKey = constantKeyPortion.split(':::')[0].strip()
					constKeyValue = constantKeyPortion.split(':::')[-1].strip()

					if self.matchAll(constKey + "=" + constKeyValue, point) == True:
						flag = 0
						newKey = constKey + "=" + constKeyValue

						for i in range(len( self.keyPredicates[newKey]["match"])):
							if match( self.keyPredicates[newKey]["match"][i], point) == True and applyTransform( self.keyPredicates[newKey]["transformation"][i], point, newKey) == constKeyValue:
								flag = 1
								break

						if flag == 0:
							print "DEBUG 5 : constant key does not match. Match() works, but extracts wrong string ", point, key
							continue
					else:
						#print "DEBUG 5 : constant key does not match ", point, key
						continue

				for i in range(len( self.keyPredicates[key]["match"])):
					print "Matching ",point, "key : ",key
					if match( self.keyPredicates[key]["match"][i], point) == True:
						print "Matched ",point, "key : ",key  
						#print key, keyPredicates[key]
						resultString = applyTransform( self.keyPredicates[key]["transformation"][i], point, key)
						print "result string : ",resultString
						if resultString == "XXX3":
							pointInfo[point].append(('XXX3', key))
						elif resultString == "XXX2":
							pointInfo[point].append(('XXX2',key))
						elif resultString == "XXX1":
							pointInfo[point].append(('XXX1', key))
						else:
							if "&" in key:
								expandedString += "," + str(key.split('&')[0].strip()) + ":" + resultString
							else:
								expandedString += "," + str(key) + ":" + resultString
						break

			self.expandedPoints[point] = expandedString[1:]
			#print point, expandedString

		return pointInfo

	def matchAll(self, key, point):
		if key not in self.keyPredicates:
			return True
		if len( self.keyPredicates[key]["match"]) == 0:
			return True
		for i in range(len( self.keyPredicates[key]["match"])):
			if match( self.keyPredicates[key]["match"][i], point) == True:
				return True

		return False

	'''
	Returns the stored set of rules, expanded metadata and examples supplied by the expert until now
	'''
	def getData(self):
		return [ self.expandedPoints, self.keyPredicates, self.examples ]


	'''
	Apply transforms based on rules generated onto a point
	'''
	def applyAllTransforms(self, regex, point, key):
		possibleOutputs = []
		for i in range(len(regex['left'])):
			for j in range(len(regex['right'])) :
				string = applyTransform(regex['left'][i], regex['right'][j])
				if string not in possibleOutputs:
					possibleOutputs.append((string))


		if "=" in key:
			value = key.strip()

		if point not in self.keyOutputs:
			self.keyOutputs[point] = {}

		
		self.keyOutputs[point][key] = possibleOutputs
	 
if __name__ == "__main__":
	printLearntExamples(sys.argv[1],sys.argv[2])
	main()


