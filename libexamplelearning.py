import os
import re
import sys
import numpy
import itertools


'''
given a point, a key and its value , e.g key:zone temp sensor , value:ART, valueType: v or c (depending on whether it is a constant or variable acc. to the paper),
 the starting position of the key in the point string, 
and the keys to its left and keys to its right, find all possible regular expressions which according to our language can extract
that substring
''' 
def generateAllPossibleOptions(point, key, value, valueType, startPos, leftKeys, rightKeys):
	possibilities = {}

	knownKeys = []
	knownKeys.extend(leftKeys)
	knownKeys.extend(rightKeys)
	if valueType == "c":
		knownKeys.append((key, startPos))
	knownKeys.sort(key=lambda x:x[1])

	y1 = GeneratePosition(point, startPos, knownKeys)
	y2 = GeneratePosition(point, startPos + len(value) , knownKeys, len(value))
	
	possibilities["left"] = y1
	possibilities["right"] = y2
	
	return possibilities

'''
according to our language, generate all possible regular expressions which extract the position 'k' in the 'inString'
'''		
def GeneratePosition(inString, k, knownKeys, length=None ):

	result = [ ("cpos",k) ]
	if (-len(inString) + k ) < 0:
		result.append(("cpos", (-len(inString) + k )))
	else:
		result.append(("cpos", ""))

	if length!= None:
		result.append(("l",length))
	allResults = []
	for i in range(k):
		if inTheMiddle(inString, knownKeys, i) == True:
			continue 

		r1 = getTokenSequence(inString,i,k, knownKeys)
		for j in range(k,len(inString)):
			if inTheMiddle(inString, knownKeys, j+1) == True:
				continue

			r2 = getTokenSequence(inString, k, j+1, knownKeys)
			allResults.append((r1,r2))
			#print "all results : ",r1,r2
			c = getMatchNumber(inString,r1,r2, k)
			if c == None:
				print "Something wrong", inString, r1, r2, k
			result.append(("Pos",r1,r2,c))

	deduplicatedResult = sorted(set(result))
	return deduplicatedResult


'''
Get which nummber match it is ; i.e the value of 'c' in PrecedeSucceed(r1, r2, c)
'''
def getMatchNumber(inString, r1,r2, pos):

	#print "Trying to match ", inString, r1, r2, "pos = ", pos
	matchNumber = 0
	for i in range(len(inString)):
		flag = 0
		for match in re.finditer("(?=(" + r1 + "))",inString[:i]):
			if (match.span()[0] + len(match.group(1))) == i :
				flag = 1
				break
		if flag == 0:
			continue

		flag = 0
		for match in re.finditer(r2,inString[i:]):
			if match.span()[0] != 0:
				flag = 0
				break
			else:
				flag = 1
				break

		if flag == 0:
			continue

		matchNumber += 1
		if i == pos:
			#print "Returning match number : ",matchNumber
			return matchNumber
			
			
	#print "returning None"
	return None

'''
check to see that the Position p1 or p2 (refer to paper) is not in the middle of substring which has another expansion
'''
def inTheMiddle(inString, knownKeys, startPos):
	knownKeyValues = [ k[0].split('=')[-1].strip() for k in knownKeys ]
	knownKeyIndices = [ k[1] for k in knownKeys ]

	for i in range(len(knownKeyIndices)):
		if startPos <= knownKeyIndices[i] or startPos >= knownKeyIndices[i] + len(knownKeyValues[i]):
			continue
		else:
			return True
	return False

'''
get token sequence (acc to our language) to represent the characters between startPos and endPos
'''
def getTokenSequence(inString, startPos, endPos, knownKeys):

	knownKeyValues = [ k[0].split('=')[-1].strip() for k in knownKeys ]
	knownKeyIndices = [ k[1] for k in knownKeys ]
	regex = []
	i = startPos
	while i < endPos:
		if i in knownKeyIndices:
			regex.append('(' + knownKeyValues[ knownKeyIndices.index(i) ] + ')' ) 
			i += len(knownKeyValues[ knownKeyIndices.index(i) ])
		elif len(re.compile('[A-Za-z]').findall(inString[i])) == 1:
			regex.append('[A-Za-z]')
			i += 1
		elif len(re.compile('[0-9]').findall(inString[i])) == 1:
			regex.append('[0-9]')
			i += 1
		else:
			regex.append('\\' + inString[i])
			i += 1

	i = 0
	ending = len(regex)
	regexString = ""
	prevRegex = ""

	while i < ending:
		regexString += regex[i]
		i += 1

	return regexString

'''
merge the regular expression rules created for a particular key with other rules for that key created from other examples.
traceSets = the list of rules for a particular example
key = the key for which to merge the regular expressions
examplePointList = the examples supplied by the expert till now which have that key
The algorithm is taken from the paper "S.Gulwani 'Automating string processing in spreadsheets using input-output examples", POPL 2011'
'''
def mergeKeyPossibilities(key, traceSets, examplePointList):

	remainingPointLists = examplePointList[:]
	remainingTraceSets = traceSets[:]


	while True:
		l = len(remainingTraceSets)
		if l == 1:
			break
		C1_scores = numpy.zeros( (l , l ) )
		C2_scores = numpy.zeros( (l, l ) )
	

		for i in range(l):
			for j in range( i+1, l):
				#print "INTERSECTION 1", i, j
				( c, intersectedSet ) = common( remainingTraceSets[i], remainingTraceSets[j] , True, False)
				if c >= 1:	
					C1_scores[i,j] = 1
					for k in range(l):
						if k == i or k==j:
							continue
						#print "INTERSECTION 2 : "
						(c2, s) = common(remainingTraceSets[i], remainingTraceSets[k], False, False)
						(c3, s) = common(remainingTraceSets[j], remainingTraceSets[k], False, False)
						if c2 >= 1 and c3 >= 1 :
							(c4, s) = common(intersectedSet, remainingTraceSets[k], False, False)
							if c4 == 1:
								C1_scores[i,j] += 1
						elif c2 == 0 and c3 == 0:
							C1_scores[i,j] += 1
							#print C1_scores[i,j]
	
					numEleIntersectedSet = len(intersectedSet['left']) * len(intersectedSet['right'])
					numEleSetI = len(remainingTraceSets[i]['left']) * len(remainingTraceSets[i]['right'])
					numEleSetJ = len(remainingTraceSets[j]['left']) * len(remainingTraceSets[j]['right'])
					C2_scores[i,j] = float( numEleIntersectedSet ) / float( max( numEleSetI, numEleSetJ )) 


		max_i = 0
		max_j = 1
		for i in range(l):
			for j in range(i+1,l):
				if C1_scores[i,j] < C1_scores[max_i, max_j]:
					continue
				if C1_scores[i,j] > C1_scores[max_i, max_j]:
					max_i = i
					max_j = j
				elif C1_scores[i,j] == C1_scores[max_i, max_j]:
					if C2_scores[i,j] > C2_scores[max_i, max_j]:
						max_i = i
						max_j = j


		newRemainingTraceSets = []
		newRemainingPointLists = []
		
		if C1_scores[max_i, max_j] >= 1.0:

			(c, intersectedSet) = common(remainingTraceSets[max_i], remainingTraceSets[max_j], True, False)
			for i in range(len(remainingTraceSets)):
				if i != max_i and i != max_j:
					newRemainingTraceSets.append(remainingTraceSets[i])
					newRemainingPointLists.append(remainingPointLists[i])

				elif i == max_i:
					newRemainingTraceSets.append(intersectedSet)
					newRemainingPointLists.append(remainingPointLists[i] + ";" + remainingPointLists[max_j])
				elif i == max_j:
					continue					
			

			remainingPointLists = newRemainingPointLists[:]
			remainingTraceSets = newRemainingTraceSets[:]
			
			
			continue
		else:
			break

	return (remainingPointLists, remainingTraceSets)	
			
'''
Find the common regular expressions between two sets
allResults indicates whether to return all common regular expressions or whether to only return 1 result
'''
def common(set1, set2, allResults=True, p=False):
	intersection = {}
	left_intersection = []
	right_intersection = []
	for ele1 in set1['left']:
		if ele1 in set2['left']:
			left_intersection.append(ele1)
			if allResults == False:
				break
	intersection['left'] = left_intersection
	if len(left_intersection) == 0:
		return ( 0, { 'left' : [], 'right' : [] } )
	for ele1 in set1['right']:
		if ele1 in set2['right']:
			right_intersection.append(ele1)
			if allResults == False:
				break


	intersection['right'] = right_intersection

	if p == True:
		print "Received : "
		print set1
		print set2
		print "Intersection : "
		print intersection

	l = len(left_intersection) * len(right_intersection)
	return ( l , intersection)
	

'''
find the boolean expressions which match list of points1 and points2 .
This step is to figure out the Boolean classifier conjuntcs in our language
'''	
def findBooleanExpression(points1, points2, examples, value=None):
	#print "Finding common bool expression for : ",points1, points2
	tempPoints1 = points1[:]
	b = []
	while len(tempPoints1) > 0:
		prevTempPoints1 = tempPoints1[:]
		d = []
		tempPoints2 = points2[:]
		copyTempPoints1 = tempPoints1[:]
		
		flag = 0
		while len(tempPoints2) > 0:
			prevTempPoints2 = tempPoints2[:]
			if value != None and flag == 0:
				( preds, matching1, notMatching2 ) = generatePredicate(copyTempPoints1, tempPoints2, examples, value)
				flag = 1
				if preds == None:
					print value, "Something seriously wrong !!"
			else:
				( preds, matching1, notMatching2 ) = generatePredicate(copyTempPoints1, tempPoints2, examples, None)

			
			d.append( preds )
			copyTempPoints1 = [ p for p in copyTempPoints1 if p in matching1 ]
			tempPoints2 = [ p for p in tempPoints2 if p not in notMatching2 ]
	
			#print "Remaining points in list 1", copyTempPoints1
			#print "Remaining points in list 2", tempPoints2 

			if len(tempPoints2) == len(prevTempPoints2):
				#print "Returning None 1"
				return None

		tempPoints1 = [ p for p in tempPoints1 if p not in copyTempPoints1 ]

		#print "list1 size : ",len(tempPoints1)
		b.append(d)
		if len(prevTempPoints1) == len(tempPoints1):
			#print "Returning None 2"
			return None

	return b

'''
Generate the predicates in our language. 
Algorithm once again taken from "S.Gulwani 'Automating string processing in spreadsheets using input-output examples", POPL 2011'
'''
def generatePredicate(list1, list2, examples, value, shouldPrint=False):
	examplePoint = list1[0]
	exampleKey = [ k for k in examples[examplePoint] ][0]
	knownKeys = examples[examplePoint][exampleKey]["allKeys"]
	maxCSP = 0
	bestPredicate = None
	matching1 = []
	notMatching2 = []
		
		
	for i in range(len(examplePoint)):
		#print "Trying this"
		for j in range(i+1, len(examplePoint)+1):
			if inTheMiddle(examplePoint, knownKeys, i ) == True or inTheMiddle(examplePoint, knownKeys, j ) == True :
				continue
			tokenSequence = getTokenSequence(examplePoint, i, j, knownKeys)
			if value != None:
				if "(" + value + ")" not in tokenSequence:
					continue
			[ score, m1, nm2 ] = computeCSPPos(list1, list2, tokenSequence, i)
			if score == 0:
				continue
			elif score > maxCSP :
				maxCSP = score
				matching1 = m1[:]
				notMatching2 = nm2[:]
				bestPredicate = (tokenSequence,"p",i)

			elif score == maxCSP and len(tokenSequence) < len(bestPredicate[0]):
				maxCSP = score
				matching1 = m1[:]
				notMatching2 = nm2[:]
				bestPredicate = (tokenSequence,"p", i)

			
	#print "DEBUG1 : best predicate 1: ",bestPredicate, value

	for i in range(len(examplePoint)):
		for j in range(i+1, len(examplePoint)+1):
			if inTheMiddle(examplePoint, knownKeys, i ) == True or inTheMiddle(examplePoint, knownKeys, j ) == True :
				continue
			tokenSequence = getTokenSequence(examplePoint, i, j, knownKeys)
			if value != None:
				if "(" + value + ")" not in tokenSequence:
					continue
			[ score, m1, nm2 ] = computeCSPPos(list1, list2, tokenSequence, -len(examplePoint) + i)
			if score == 0:
				continue
			elif score > maxCSP :
				maxCSP = score
				matching1 = m1[:]
				notMatching2 = nm2[:]
				bestPredicate = (tokenSequence, "p", i)

			elif score == maxCSP and len(tokenSequence) < len(bestPredicate[0]):
				maxCSP = score
				matching1 = m1[:]
				notMatching2 = nm2[:]
				bestPredicate = (tokenSequence, "p", i)

	#print "DEBUG1 : best predicate 2", bestPredicate, value
		
	for i in range(len(examplePoint)):
		for j in range(i+1, len(examplePoint)+1):
			if inTheMiddle(examplePoint, knownKeys, i ) == True or inTheMiddle(examplePoint, knownKeys, j ) == True :
				continue
			tokenSequence = getTokenSequence(examplePoint, i, j, knownKeys)
			if value != None:
				if "(" + value + ")" not in tokenSequence:
					continue
			numOcc = len(re.findall("(?=(" + tokenSequence + "))" , examplePoint ))
			[ score, m1, nm2 ] = computeCSP(list1, list2, tokenSequence, numOcc)
			if score == 0:
				continue
			elif score > maxCSP :
				maxCSP = score
				matching1 = m1[:]
				notMatching2 = nm2[:]
				bestPredicate = (tokenSequence,numOcc)

			elif score == maxCSP and len(tokenSequence) < len(bestPredicate[0]):
				maxCSP = score
				matching1 = m1[:]
				notMatching2 = nm2[:]
				bestPredicate = (tokenSequence,numOcc)


	if shouldPrint == True or bestPredicate == None:
		print "generatePredicate"
		print "Returning - "
		print bestPredicate
		print matching1
		print notMatching2
	return ( bestPredicate, matching1, notMatching2 )

'''
A helper function to compute efficient boolean classifiers.
To find out the utility of the score returned by this function , 
refer to "S.Gulwani 'Automating string processing in spreadsheets using input-output examples", POPL 2011'
'''

def computeCSPPos(list1, list2, tokenSequence, position):
	c1 = 0
	c2 = 0
	matching1 = []
	notMatching2 = []
	for point in list1:
		pos = position
		if position < 0 :
			pos = len(point) + position
		for match in re.finditer(tokenSequence, point[pos:]):
			if match.span()[0] != 0:
				break
			else:
				c1 += 1
				matching1.append(point)
				break

	for point in list2:
		pos = position
		if position < 0:
			pos = len(point) + position
		flag = 0
		for match in re.finditer(tokenSequence, point[pos:]):
			if match.span()[0] != 0:
				break
			else:
				flag = 1
				break
		if flag == 0:
			c2 += 1
			notMatching2.append(point)
			
	#print "DEBUG 3 : ", tokenSequence, position, c1, c2, list1, list2	
	return [ c1*c2, matching1, notMatching2 ]

'''
A helper function to compute efficient boolean classifiers.
To find out the utility of the score returned by this function , 
refer to "S.Gulwani 'Automating string processing in spreadsheets using input-output examples", POPL 2011'
'''
def computeCSP(list1, list2, tokenSequence, numOcc):
	c1 = 0
	c2 = 0
	matching1 = []
	notMatching2 = []
	for point in list1:
		if len( re.findall("(?=(" + tokenSequence + "))", point) ) == numOcc:
			c1 += 1
			matching1.append(point)

	for point in list2:
		if len( re.findall("(?=(" + tokenSequence + "))", point) ) == numOcc:
			continue
		else:
			c2 += 1
			notMatching2.append(point)
				
	return [ c1*c2, matching1, notMatching2 ]

'''
tries to match the boolean classifers in Disjunctive Normal Form (DNF) to a point.
Refer to "S.Gulwani 'Automating string processing in spreadsheets using input-output examples", POPL 2011' for more details
'''	
def match(dnf, point):
	if dnf == None:
		return True
	if len(dnf) == 0:
		return True
	for i in range(len(dnf)):
		flag2 = 1
		for j in range(len(dnf[i])):	
			if len(dnf[i]) == 0:
				return True
			#print dnf[i][j], point
			if len(dnf[i][j]) == 2 and len(re.findall( "(?=(" + dnf[i][j][0] + "))", point )) == dnf[i][j][1]:
				continue
			elif len(dnf[i][j]) == 3 :
				flag = 0
				pos = dnf[i][j][2]
				if pos < 0:
					pos = len(point) - pos	

				for match in re.finditer(dnf[i][j][0] , point[pos:]):
					if match.span()[0] == 0:
						flag = 1
						break
					else:
						break
				if flag == 1:
					continue
				else:
					flag2 = 0
					break
			else:
				flag2 = 0
				break

		if flag2 == 1:
			return True
	
	print "Match", dnf, point , "returned False"
	return False		

'''
applies the learned regular expression on a point
fail if it cannot apply the learned expression
'''
def applyTransform(regex, point, key):
	
	# finding left point
	leftIndex = None
	rightIndex = None
	for i in range(len(regex['left'])):
		if regex['left'][i][0] == 'cpos':
			if regex['left'][i][1] == "":
				leftIndex = len(point)
				break
			else:
				leftIndex = regex['left'][i][1] 
				break	   	

		for j in range(len(point)):
			c = getMatchNumber(point, regex['left'][i][1], regex['left'][i][2], j)
			if c == None:
				#print "Not matching"
				continue
			if c != regex['left'][i][3]:
				#print "Not matching 2"
				continue

			leftIndex = j
			break
		
		if leftIndex == None:
			continue
		else:
			break

	print "Done left index",leftIndex
	if leftIndex == None:
		return "XXX1" 

	for i in range(len(regex['right'])):
		if regex['right'][i][0] == 'cpos':
			if regex['right'][i][1] == "":
				rightIndex = len(point)
				break
			else:
				rightIndex = regex['right'][i][1]
				break	
		elif regex['right'][i][0] == 'l':
			rightIndex = leftIndex + regex['right'][i][1]
			if rightIndex == 0:
				rightIndex = len(point)
			break

		for j in range(len(point)):
			c = getMatchNumber(point, regex['right'][i][1], regex['right'][i][2], j)
			if c == None:
				continue
			if c != regex['right'][i][3]:
				continue

			rightIndex = j
			break
		
		if rightIndex == None:
			continue
		else:
			break

	print "Done right index",rightIndex

	if rightIndex == None:
		return "XXX2" 

	if "=" in key and "&" not in key :
		value = key.split('=')[-1].strip()
		if point[leftIndex:rightIndex] == value:
			return value
		else:
			print value, point[leftIndex:rightIndex]
			return "XXX3"

	return point[leftIndex:rightIndex]


