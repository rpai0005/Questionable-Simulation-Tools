'''
Copyright 2022 Abigail Harrison, Anike Braun

Permission is hereby granted, free of charge, to any person obtaining a copy of this software 
and associated documentation files (the "Software"), to deal in the Software without restriction, 
including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, 
and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, 
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial 
portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE 
AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, 
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

from vose_sampler import VoseAlias
from scipy.stats import norm
import numpy as np
import random
import json
import os.path
import sys
import math 
from math import ceil
import csv
from lazy_backend import *


class Ballot(object):
    '''
    Summary: Ballot object
    Parameters: ID
    Returns: Ballot object with an id and two states for vote and error
    '''
    def __init__(self, id):
        self.number = id  
        self.error = "normal" #normal/undervote/overvote
        self.vote = "waiting" #waiting/winner/runnerup
        self.batch = None #_setTownAndBatch
        self.town = None #_setTownAndBatch  
        
        
class Election(object):
    def __init__(self, numBallots, margin, o1, u1, o2, u2, riskLimit, gamma, jsonFile = None, minBallots = 0, maxBallots = 0):
        self.numBallots = numBallots
        self.margin = margin
        self.overvotes1 = o1
        self.undervotes1 = u1
        self.overvotes2 = o2
        self.undervotes2 = u2
        self.riskLimit = riskLimit 
        self.jsonFile = jsonFile
        self.gamma = gamma
        if (minBallots == 0):
            self.minBallots = 1
        else:
            self.minBallots = minBallots
        if (maxBallots == 0):
            self.maxBallots = numBallots
        else:
            self.maxBallots = maxBallots
        self.winnerBallots = self.runnerupBallots = 0 #Number of ballots the winner/runnerup receives
        self.ballotList = {} #ID: ballot object
        self.ballotPolling, self.ballotComparison = [], [] #List of ballots pulled in ballot polling/ballot comparison audit
        self.votersPerTown = {} #Town: max number of voters
        self.allVoters = 0
        self.tabulatorBatch, self.batchMaxSize = {}, {} #Town: list empty batches/max size of batches/distribution
        self.numPollingPerTown, self.numComparisonPerTown = {}, {} #Town: num of ballots to audit for polling/comparison
        if jsonFile is not None:
            #Initializes lists/dictionaries using data from the JSON file
            for townName in self.jsonFile:
                town = townName["Town"]
                townVoters = int(townName["Voter Population"])
                pollingPlaces = int(townName["Polling Places"])
                self.votersPerTown[town] = townVoters
                self.allVoters += int(townVoters) 
                self.numPollingPerTown[town] = self.numComparisonPerTown[town] = 0
                #Initializes dictionaries for batches; one batch for each polling place and an additional absentee batch
                self.tabulatorBatch[town], self.batchMaxSize[town] = [], []
                self.batchMaxSize[town].append(pollingPlaces + 1) #indicates number of batches per town
                absentee = .05 * townVoters #batch for absentee ballots; about 5% of town's population
                nonAbsentee = townVoters - absentee
                for i in range(0, pollingPlaces):
                    self.tabulatorBatch[town].append(0)
                    self.batchMaxSize[town].append(round(nonAbsentee/pollingPlaces))
                #Absentee batches
                self.tabulatorBatch[town].append(0)
                self.batchMaxSize[town].append(absentee)
                #self.batchDistribution[town].append(.05)
            self.staticVotersPerTown = self.votersPerTown
            self.staticBatchSize = self.batchMaxSize
        self.comparisonBatch = [] #[BatchID][Ballots]
        
        
    def _marginOfVictory(self):
        '''
        Summary: Calculates the number of ballots each candidate will receive depending on the margin-of-victory
        Parameters: The total number of ballots and the input margin
        Returns: The number of ballots for the winner and the number of ballots for the runner-up
        '''
        ballots = self.numBallots - self.overvotes1 - self.undervotes1 - self.overvotes2 - self.undervotes2 #number of ballots with actual votes
        #Gives the winner margin% more votes than runner-up
        ballotsInMargin = ballots/100 * float(self.margin)
        self.winnerBallots = round(1/2 * (ballots + ballotsInMargin))
        self.runnerupBallots = round(1/2 * (ballots - ballotsInMargin))
           
    def _distributeBallots(self):
        '''
        Summary: Randomly distributes the ballots by ID between overvotes, undervotes, winner, and runner-up
        Parameters: Number of ballots the winner/runner-up received, number of overvotes and undervotes
        Returns: Dict ballotList full of ballot IDs and ballot objects
        '''
        winnerCounter = self.winnerBallots
        runnerupCounter = self.runnerupBallots
        overvoteCounter = self.overvotes1
        undervoteCounter = self.undervotes1
        overvote2Counter = self.overvotes2
        undervote2Counter = self.undervotes2
        ballots = []
        #Initializes ballots with ID number and type, appends to ballots
        for ID in range(self.numBallots):
            b = Ballot(ID)
            if (winnerCounter > 0):
                b.vote = "winner"
                winnerCounter -= 1
            elif (runnerupCounter > 0):
                b.vote = "runnerup"
                runnerupCounter -= 1
            elif (overvoteCounter > 0):
                b.vote = "overvote"
                b.error = "overvote"
                overvoteCounter -= 1
            elif (undervoteCounter > 0):
                b.vote = "undervote"
                b.error = "undervote"
                undervoteCounter -= 1
            elif (overvote2Counter > 0):
                b.vote = "overvote"
                b.error = "overvote2"
                overvote2Counter -= 1
            elif (undervote2Counter > 0):
                b.vote = "undervote"
                b.error = "undervote2"
                undervote2Counter -= 1
            ballots.append(b)
        #Shuffles the list of ballots and re-assigns ID numbers to add to ballotList dict
        random.shuffle(ballots)
        i = 0
        for ballot in ballots:
            b = Ballot(i)
            b.vote = ballot.vote
            b.error = ballot.error
            self.ballotList[i] = b 
            i += 1
            
    def _setTownAndBatch(self, auditID):
        '''
        Summary: Uses the Vose-Alias method to distribute ballots across towns. Once town is chosen for ballot, the distribution is updated
        Also sets batch within town; batch determined to be by polling place
        Parameters: Type of audit, total voter population (minus number of ballots pulled) and most recent distribution
        Returns: The town a ballot belongs to
        '''
        #Establishes distribution of ballots across towns and ballots across batches; variables updated as ballots are pulled
        townDistribution = {}
        batchID = None
        for town in self.votersPerTown:
            townDistribution[town] = self.votersPerTown[town]/self.allVoters
        #Pick a town for the ballot based on the distribution
        VA = VoseAlias(townDistribution)
        ballotTown = ''.join(VA.sample_n(size = 1))
        self.votersPerTown[ballotTown] -= 1
        self.allVoters -= 1
        #Only assigns batches for ballots in ballot comparison; update with lazy CVR method once math is complete
        if (auditID == "Comparison"):
            while 1:
                numBatches = self.batchMaxSize[ballotTown][0]
                batchID = random.randint(0, numBatches - 1)
                if (self.batchMaxSize[ballotTown][batchID + 1] > 0):
                    self.batchMaxSize[ballotTown][batchID + 1] -= 1
                    self.tabulatorBatch[ballotTown][batchID] += 1
                    break
        return ballotTown, batchID
    
    def _getBatchNumbers(self):
        '''
        Summary: Finds the number of ballots that need to be rescanned across all precincts in a town for Lazy CVR
        Parameters: self.staticBatchSize and self.tabulatorBatch
        Returns: A list that contains the number of precincts/batches pulled from in a town and the total population of these precincts/batches
        '''
        lazyBallots = {} #town: [number of precincts, total population]
        for town in self.tabulatorBatch:
            lazyBallots[town] = [0, 0]
            for i in range(0, len(self.tabulatorBatch[town]) - 1):
                if (self.tabulatorBatch[town][i] > 0):
                    lazyBallots[town][0] += 1
                    lazyBallots[town][1] += self.staticBatchSize[town][i + 1]
        return lazyBallots
    
    def _ballotPolling(self):
        '''
        Summary: Follows the steps listed in BRAVO, page 5 to simulate a ballot polling audit. For 2 candidate race
        Returns: Number of ballots that need to be looked at in a ballot polling audit
        '''
        IDList = list(range(0, self.numBallots))
        numToAudit = 0
        T = 1 #test statistic
        sw = self.winnerBallots/self.numBallots #proportion of winner votes
        while 1:
            numToAudit += 1
            if (numToAudit == self.numBallots):
                pullID = 0
            else:
                pullID = random.randint(0, self.numBallots - numToAudit)
            randomBallot = self.ballotList[IDList[pullID]]
            self.ballotPolling.append(randomBallot)
            #Checks that ballot isn't undervote or overvote; if so, add 1 to number of ballots to audit and don't change T
            if (randomBallot.error == "normal"):
                if (randomBallot.vote == "winner"):
                    T *= sw/.5
                else:
                    T *= (1 - sw)/.5
            numToAudit += 1
            if (T >= 1/self.riskLimit):
                return numToAudit
            elif (numToAudit == self.numBallots): 
                return self.numBallots
            
    def _ballotComparison(self):
        '''
        Summary: Uses the formula from Gentle Intro to RLA to simulate a ballot comparison audit. Only uses 1 vote over/under statements
        Returns: Number of ballots that need to be looked at in a ballot comparison audit
        
        '''
        minBallots = self.minBallots
        maxBallots = self.maxBallots
        dilutedMargin = (self.winnerBallots - self.runnerupBallots)/self.numBallots
        alpha = self.riskLimit
        numToAudit = 0
        observedrisk = 1
        successTracker = 0
        gamma = self.gamma
        #Checks if the initial batch of ballots is enough to audit; if not then add another ballot and keep checking
        while 1:
            numToAudit += 1
            pullID = random.randint(0, self.numBallots - 1)
            randomBallot = self.ballotList[pullID]
            self.ballotComparison.append(randomBallot)
            discCounter=0
            if (randomBallot.error == "overvote"):
                discCounter=discCounter+1
            elif (randomBallot.error == "overvote2"):
                discCounter=discCounter+2
            elif (randomBallot.error == "undervote"):
                discCounter=discCounter-1
            elif (randomBallot.error == "undervote2"):
                discCounter=discCounter-2
            observedrisk = observedrisk * (1-(dilutedMargin/(2*gamma)))/(1-(discCounter/(2*gamma)))
            if (minBallots == maxBallots and numToAudit == minBallots or numToAudit == maxBallots):
                if (observedrisk < alpha):
                    successTracker = 100
                return numToAudit, successTracker
            elif (observedrisk < alpha and numToAudit >= minBallots):
                successTracker = 100
                return numToAudit, successTracker
              
    def _ballotsPerTown(self):
        '''
        Summary: Prints the number of ballots from the audit per town
        Parameters: List of ballots from the risk-limiting audits and list of ballots per batch
        '''
        #Ballots for ballot comparison audit
        if (len(self.ballotComparison) == self.numBallots):
            self.numComparisonPerTown = self.staticVotersPerTown
        else:
            for ballot in self.ballotComparison:
                if (ballot.town is None):
                    ballot.town, ballot.batch = self._setTownAndBatch("Comparison")
                self.numComparisonPerTown[ballot.town] += 1
        #Ballots for ballot polling audit
        if (len(self.ballotPolling) == self.numBallots):
            self.numPollingPerTown = self.staticVotersPerTown
        else:
            for ballot in self.ballotPolling:
                if (ballot.town is None):
                    ballot.town, ballot.batch = self._setTownAndBatch("Polling")
                self.numPollingPerTown[ballot.town] += 1
        #Get precinct totals for LazyCVR
        lazyBallots = self._getBatchNumbers()
        return self.numPollingPerTown, self.numComparisonPerTown, lazyBallots
    
    def _modifiedBatchComparison(self):
        #Sets up batches of 50
        j = 0
        for batchID in range(ceil(self.numBallots/50)):
            self.comparisonBatch.append([])
            if (batchID == ceil(self.numBallots/50) - 1):
                for i in range(j, self.numBallots):
                    self.comparisonBatch[batchID].append(self.ballotList[i])
            else:
                for i in range(50):
                    self.comparisonBatch[batchID].append(self.ballotList[i + j])
            j += 50
        #Ballot Comparison variables, translated to batch comparison
        dilutedMargin = (self.winnerBallots - self.runnerupBallots)/self.numBallots
        o1Counter = 0
        o1 = 0
        gamma = 1.1
        alpha = self.riskLimit
        batchToAudit = 0 #Number of batches to audit
        ballotToAudit = 0 #Number of ballots to audit
        #Checks if the initial batch of ballots is enough to audit; if not then add another batch and keep checking
        observedrisk = 1
        while 1:
            flag = False #flag for batch if there is an overvote ballot in the batch
            batchToAudit += 1
            #Pulls random batch by pullID, then removes the batch from the sample of batches left to pull
            if (batchToAudit == ceil(self.numBallots/50)):
                pullID = 0
            else:
                pullID = random.randint(0, ceil(self.numBallots/50) - batchToAudit)
            randomBatch = self.comparisonBatch[pullID]
            del self.comparisonBatch[pullID]
            ballotToAudit += len(randomBatch)
            #Checks if there is an error, tracks the number of overvote ballots in a batch by o1Counter
            #And tracks if the ballot has a discrepancy with flag, o1
            discCounter=0
            for ballot in randomBatch:
                if (ballot.error == "overvote"):
                    discCounter=discCounter+.02
                if (ballot.error == "overvote2"):
                    discCounter=discCounter+.04
                if (ballot.error == "undervote"):
                    discCounter=discCounter-.02
                if (ballot.error == "undervote2"):
                    discCounter=discCounter-.04
            observedrisk = observedrisk * (1-(dilutedMargin/(2*gamma)))/(1-(discCounter/(2*gamma)))
            o1Counter=o1Counter + observedrisk
            if(observedrisk>0):
                o1+=1
            if (observedrisk<alpha):
                return batchToAudit, ballotToAudit
            #If you reach the total number of ballots without meeting the risk limit
            elif (ballotToAudit == self.numBallots):
                return ceil(self.numBallots/50), ballotToAudit

    def _createCVR1(self):
        '''
        Summary: Creates CVR and Manifest csv files for given Election object 
        '''
        #open csv file, write headers
        electionCVR = open('electionCVR1.csv', mode = 'w', newline = '')
        CVRwriter = csv.writer(electionCVR)
        CVRwriter.writerow(['Test'])
        CVRwriter.writerow(['','','','','','','','','Contest 1 (vote for = 1)','Contest 1 (vote for = 1)'])
        CVRwriter.writerow(['','','','','','','','','Winner','Runner-Up'])
        CVRwriter.writerow(['CVRNumber','TabulatorNumber', 'BatchID','RecordID', 'ImprintedID','CountingGroup','PrecinctPortion','BallotType','',''])

        #run _marginOfVictory, _distributeBallots for election
        self._marginOfVictory()   
        self._distributeBallots()
        
        #generate list of random numbers to later assign to imprintedID for each ballot, create empty dict for recordID
        imprintedID_list = random.sample(range(1, len(self.ballotList)+1), len(self.ballotList)) 
        recordID_dict = {}
        
        #set values for .town, .batch for each ballot
        for i in self.ballotList:
            b = self.ballotList[i]
            b.town, b.batch = self._setTownAndBatch("Comparison")
            #create dictionary for recordID number
            recordID_dict[b.town+str(b.batch)] = [0,0,0]  #key: b.town+b.batch, value: [total votes, winner votes, loser votes]

        #write to csv file for each ballot in ballotList
        for i in self.ballotList:
            b = self.ballotList[i] 
            recordID_dict[b.town+str(b.batch)][0] += 1 #update total count 
            if b.vote == "winner":
                CVRwriter.writerow([i+1,"TABULATOR1",b.town+str(b.batch),recordID_dict[b.town+str(b.batch)][0],"Test-"+str(b.batch)+'-'+str(imprintedID_list[i]),"Pilot",b.town,"BallotType",1,0])
                recordID_dict[b.town+str(b.batch)][1] += 1 #update winner count
            elif b.vote == "runnerup":
                CVRwriter.writerow([i+1,"TABULATOR1",b.town+str(b.batch),recordID_dict[b.town+str(b.batch)][0],"Test-"+str(b.batch)+'-'+str(imprintedID_list[i]),"Pilot",b.town,"BallotType",0,1])
                recordID_dict[b.town+str(b.batch)][2] += 1 #update loser count
            elif b.vote == "overvote":
                CVRwriter.writerow([i+1,"TABULATOR1",b.town+str(b.batch),recordID_dict[b.town+str(b.batch)][0],"Test-"+str(b.batch)+'-'+str(imprintedID_list[i]),"Pilot",b.town,"BallotType",1,1])
            elif b.vote == "undervote":
                CVRwriter.writerow([i+1,"TABULATOR1",b.town+str(b.batch),recordID_dict[b.town+str(b.batch)][0],"Test-"+str(b.batch)+'-'+str(imprintedID_list[i]),"Pilot",b.town,"BallotType",0,0])
        print('CVR1 created')

        #write to manifest csv file 
        electionManifest = open('electionManifest.csv', mode = 'w', newline = '')
        man_writer = csv.writer(electionManifest)
        man_writer.writerow(['Container', 'Tabulator', 'Batch Name', 'Number of Ballots'])
        for i in sorted(recordID_dict.keys()):
            town = ''.join((x for x in i if not x.isdigit())) #remove digits to get town name 
            man_writer.writerow(["Box 1", 'Tabulator 1', i, recordID_dict[i][0]])
        print('Manifest created')

        electionCVR.close()
        electionManifest.close()

    def _createCVR2(self, overvotes1, undervotes1, overvotes2, undervotes2):
        '''
        Alterations made for over/undervotes based on CVR1
        CVR2 and tabulation files written 
        '''

        #write contents of file to lists to make changes
        cvrList = []
        with open('electionCVR1.csv', mode= 'r', newline = '') as readCVR:
            cvrReader = csv.reader(readCVR)
            for i in range(4):
                next(cvrReader)
            cvrList = list(cvrReader)
            
        o1 = overvotes1
        u1 = undervotes1 
        o2 = overvotes2 
        u2 = undervotes2 

        #create dictionary for recordID number, num total ballots, winner votes , runnerup votes per batch
        recordID_dict = {}
        for i in self.ballotList:
            b = self.ballotList[i]
            recordID_dict[b.town+str(b.batch)] = [0,0,0]  #key: b.town+b.batch, value: [total votes, winner votes, loser votes] 
        
        #change votes according to number of over/under1/2 votes
        for row in cvrList: 
            townBatch = row[2]
            recordID_dict[townBatch][0] += 1
            if row[8] == '1' and row[9] == '0': # winner vote
                if u1 > 0: 
                    #change vote to 0-0 
                    row[8] = '0'
                    row[9] = '0'
                    u1 -= 1
                elif u2 > 0:
                    #change vote to 0-1
                    row[8] = '0'
                    row[9] = '1'
                    recordID_dict[townBatch][2] += 1 #update loser count
                    u2 -= 1
                else: 
                    recordID_dict[townBatch][1] += 1 #update winner count

            elif row[8] == '0' and row[9] == '1': # runnerup vote 
                if o1 > 0: 
                    #change vote to 1-1
                    row[8] = '1'
                    row[9] = '1'
                    recordID_dict[townBatch][1] += 1 #update winner count
                    recordID_dict[townBatch][2] += 1 #update loser count
                    o1 -= 1
                elif o2 > 0:
                    #change vote to 1-0
                    row[8] = '1'
                    row[9] = '0'
                    recordID_dict[townBatch][1] += 1 #update winner count
                    o2 -= 1
                else: 
                    recordID_dict[townBatch][2] += 1 #update runnerup count

            elif row[8] == '1' and row[9] == '1': # overvote 
                recordID_dict[townBatch][1] += 1 #update winner count
                recordID_dict[townBatch][2] += 1 #update loser count

        #write altered information to cvr2 file 
        with open('electionCVR2.csv', mode='w', newline = '') as writeCVR:
            cvrWriter = csv.writer(writeCVR)
            #write headers 
            cvrWriter.writerow(['Test'])
            cvrWriter.writerow(['','','','','','','','','Contest 1 (vote for = 1)','Contest 1 (vote for = 1)'])
            cvrWriter.writerow(['','','','','','','','','Winner','Runner-Up'])
            cvrWriter.writerow(['CVRNumber','TabulatorNumber', 'BatchID','RecordID', 'ImprintedID','CountingGroup','PrecinctPortion','BallotType','',''])

            cvrWriter.writerows(cvrList)

        print('CVR2 created')

        #write tabulation file
        with open('electionTabulation.csv', mode = 'w', newline = '') as electionTabulation:
            tab_writer = csv.writer(electionTabulation)
            tab_writer.writerow(['Town', 'BatchNum', 'Size', 'Winner', 'Loser'])
            for i in sorted(recordID_dict.keys()):
                town = ''.join((x for x in i if not x.isdigit())) #remove digits to get town name 
                tab_writer.writerow([town, i, recordID_dict[i][0], recordID_dict[i][1], recordID_dict[i][2]])

        print('Tabulation created')


def readInput():
    '''
    Summary: Reads data from input file to be used in simulation
    Parameters: Simulation_Input.txt
    Returns: Number of ballots, number of overvotes/undervotes, the risk limit, number of simulations, and list of margins
    '''
    #Election data from txt input file
    f = open(os.path.join(sys.path[0], "Simulation_Input.txt"), "r")
    if f is None:
        print("Invalid Input Data: Please make sure the TXT file is in the directory!")
        return
    #0: Number of ballots, 1: overvotes, 2: undervotes, 3: risk limit, 4: number of times for simulation to be run
    electionData = []
    dataValues = []
    for i in range(8):
        electionData.append(f.readline())
        #Anything after = is read as a value
        for j in range(0, len(electionData[i])):
            if (electionData[i][j] == "="):
                dataValues.append(float(electionData[i][(j + 1):]))
                break
    numBallots = int(dataValues[0])
    overvotes1 = int(dataValues[1])
    undervotes1 = int(dataValues[2])
    overvotes2 = int(dataValues[3])
    undervotes2 = int(dataValues[4])
    riskLimit = dataValues[5]
    num = int(dataValues[6])
    gamma = float(dataValues[7])
    margins = [] #0: margin, 1: minBallots, 2: maxBallots
    for line in f:
        index = []
        for i in range(0, len(line)):
            if (line[i] == "="):
                index.append(i + 1)
            elif (line[i] == ','):
                index.append(i)
        if (len(index) <= 1):
            margins.append([float(line[index[0]:]), 1, numBallots])
        else:
            if (len(index) <= 2):
                margins.append([float(line[index[0]:index[1]]), int(line[(index[1] + 1):]), numBallots])
            else:
                margins.append([float(line[index[0]:index[1]]), int(line[(index[1] + 1):index[2]]), int(line[(index[2] + 1):(len(line))])])
    if (num < 1):
        print("Error: Please make sure the number of simulations is greater than or equal to 1.")
        return
    elif (numBallots is None or overvotes1 is None or undervotes1 is None or riskLimit is None or num is None or margins is None):
        print("Error: Invalid data in Simulation_Input.txt. Please check the file and try again.")
        return
    f.close()
    return numBallots, overvotes1, undervotes1, overvotes2, undervotes2, riskLimit, num, margins, gamma


def collectData(jsonFile, numBallots, overvotes1, undervotes1, overvotes2, undervotes2, riskLimit, num, margins, gamma, simulation_writer, CVR_writer):
    #Summary: Runs the simulation num number of times and exports the data to a CSV file
    #Parameters: Data from readInput() function
    
    for run in range(0, len(margins)):
        townP, townPlist, townPdata = {}, {}, {} #Polling data: ballots per town, collection of townP (to average), average data per town
        townC, townClist, townCdata = {}, {}, {} #Comparison data: ballots per town, collection of townP (to average), average data per town
        for town in jsonFile:
            townPlist[town["Town"]], townClist[town["Town"]], townPdata[town["Town"]], townCdata[town["Town"]] = [], [], [], []
        tabulatorSize, tabulatorAverage = {}, {} #Tabulator batches audited for Lazy CVR, average tabulated batch data per town
        tabulatorList = [] #List of tabulatorSize
        numPolling, numComparison, countPtown, countCtown = [], [], [], [] #List of ballot polling/comparison numbers, non-zero towns for polling/comparison
        observedCSuccess, observedPSuccess = 0, 0
        #Runs the election simulation num number of times
        margin = margins[run][0]
        minBallots = margins[run][1]
        maxBallots = margins[run][2]
        for i in range(1, num + 1):
            print("Running Simulation #", i, "for", margin, "%")
            townPcount = townCcount = 0
            E1 = Election(numBallots, margin, overvotes1, undervotes1, overvotes2, undervotes2, riskLimit, gamma, jsonFile, minBallots, maxBallots) 
            E1._marginOfVictory() 
            E1._distributeBallots()
            #numPolling.append(E1._ballotPolling())
            numPolling.append(0)
            observedPSuccess += 0
            ballots, success = E1._ballotComparison()
            numComparison.append(ballots)
            observedCSuccess += success
            townP, townC, tabulatorSize = E1._ballotsPerTown()
            for town in townP:
                townPlist[town].append(townP[town])
                if (townP[town] > 0):
                    townPcount += 1
                townClist[town].append(townC[town])
                if (townC[town] > 0):
                    townCcount += 1
            countPtown.append(townPcount)
            countCtown.append(townCcount)
            tabulatorList.append(tabulatorSize)
        #Averages the simulations and calculates stdev and variance
        pollingMean = round(np.mean(numPolling), 2)
        pollingStdev = round(np.std(numPolling), 2)
        pollingVariance = round(np.var(numPolling), 2)
        pollingTownCount = round(np.mean(countPtown), 2)
        pollingSuccess = round(observedPSuccess/num, 2)
        comparisonMean = round(np.mean(numComparison), 2)
        comparisonStdev = round(np.std(numComparison), 2)
        comparisonVariance = round(np.var(numComparison), 2)
        comparisonTownCount = round(np.mean(countCtown), 2)
        comparisonSuccess = round(observedCSuccess/num, 2)
        #You pull x or less number of ballots 90%/75% of the time
        if (pollingStdev != 0):
            polling95 = round(norm.ppf(q = .95, loc = pollingMean, scale = pollingStdev), 2)
            polling90 = round(norm.ppf(q = .9, loc = pollingMean, scale = pollingStdev), 2)
            polling75 = round(norm.ppf(q = .75, loc = pollingMean, scale = pollingStdev), 2)
        else:
            polling90 = polling75 = polling95 = pollingMean
        if (comparisonStdev != 0):
            comparison95 = round(norm.ppf(q = .95, loc = comparisonMean, scale = comparisonStdev), 2)
            comparison90 = round(norm.ppf(q = .9, loc = comparisonMean, scale = comparisonStdev), 2)
            comparison75 = round(norm.ppf(q = .75, loc = comparisonMean, scale = comparisonStdev), 2)
        else:
            comparison90 = comparison75 = comparison95 = comparisonMean
        #0: Average ballots, 1: standard deviation, 2: variance
        for town in townPlist:
            tabulatorAverage[town] = [0, 0]
            townPdata[town].append(round(np.mean(townPlist[town]), 2))
            townPdata[town].append(round(np.std(townPlist[town]), 2)) 
            townPdata[town].append(round(np.var(townPlist[town]), 2))
            townCdata[town].append(round(np.mean(townClist[town]), 2))
            townCdata[town].append(round(np.std(townClist[town]), 2)) 
            townCdata[town].append(round(np.var(townClist[town]), 2))
        #CSV export
        simulation_writer.writerow([''])
        simulation_writer.writerow(["Margin of Victory", margin])
        simulation_writer.writerow(['', "Ballot Polling", '', '', '', '', "Chance of Completion", "Ballots", '', 'Polling - Non-Zero Towns', '', '', '', "Ballot Comparison", '', '', '', '', "Chance of Completion", "Ballots", '', "Comparison - Non-Zero Towns"])
        simulation_writer.writerow(['', "Number of Ballots", "Stdev", "Variance", "Risk Limit", '', "95%", polling95, '', "Average:", pollingTownCount, '', '', "Number of Ballots", "Stdev", "Variance", "Success Chance", '', "95%", comparison95, '', "Average:", comparisonTownCount])
        simulation_writer.writerow(['', pollingMean, pollingStdev, pollingVariance, str(pollingSuccess) + "%", '', "90%", polling90, '', "Per Simulation:", '', '', '', comparisonMean, comparisonStdev, comparisonVariance, str(comparisonSuccess) + "%", '', "90%", comparison90, '', "Per Simulation:"])
        simulation_writer.writerow(["Per Town:", '', '', '', '', '', "75%", polling75, '', "1", countPtown[0], '', "Per Town:", '', '', '', '', '', "75%", comparison75, '', "1", countCtown[0]])
        i = 2
        for town in townPdata:
            if (i > num):
                simulation_writer.writerow([town, townPdata[town][0], townPdata[town][1], townPdata[town][2], '', '', '', '', '', '', '', '', town, townCdata[town][0], townCdata[town][1], townCdata[town][2]])
            else:
                simulation_writer.writerow([town, townPdata[town][0], townPdata[town][1], townPdata[town][2], '', '', '', '', '', i, countPtown[i-1], '', town, townCdata[town][0], townCdata[town][1], townCdata[town][2], '', '', '', '', '', i, countCtown[i-1]])
                i += 1
        #CSV header
        CVR_writer.writerow([''])
        CVR_writer.writerow(["Margin of Victory", margin, "Ballots Pulled", comparisonMean]) 
        CVR_writer.writerow(["Town", "Average Number of Precincts Flagged for Audit", "Average Flagged Precinct Population"])
        flagForCVR = {} #town: [number of precincts flagged, population for CVR]
        totalBatch = 0
        #Organizes data into flagForCVR
        for dct in tabulatorList:
            for town in dct:
                tabulatorAverage[town][0] += dct[town][0]
                tabulatorAverage[town][1] += dct[town][1]
        for town in tabulatorAverage:
            flagForCVR[town] = [0, 0]
            flagForCVR[town][0] = round(tabulatorAverage[town][0]/num, 2)
            flagForCVR[town][1] = round(tabulatorAverage[town][1]/num, 2)
            CVR_writer.writerow([town, flagForCVR[town][0], flagForCVR[town][1]])
            totalBatch += flagForCVR[town][0]
        CVR_writer.writerow(["Total Batches", totalBatch])
        CVR_writer.writerow([''])
        print("Simulation Complete for", margin, "%")


def batchComparisonCollectData(jsonFile, numBallots, overvotes1, undervotes1, overvotes2, undervotes2, riskLimit, num, margins, batchCompar_writer):
    '''
    Same function as collectData(), but doesn't collect the data for towns
    '''
    for run in range(0, len(margins)):
        
        numBatchComparison = []
        numBallotBatch = []
        o1Counter = []
        o1Batches = []
        for i in range(1, num + 1):
            margin = margins[run]
            print("Running Simulation #", i, "for", margin, "%")
            E1 = Election(numBallots, margin, overvotes1, undervotes1, overvotes2, undervotes2, jsonFile, riskLimit) 
            E1._marginOfVictory() 
            E1._distributeBallots()
            numBatch, numBallot, o1, o1B = E1._modifiedBatchComparison()
            numBatchComparison.append(numBatch)
            numBallotBatch.append(numBallot)
            o1Counter.append(o1)
            o1Batches.append(o1B)
        batchMean = round(np.mean(numBatchComparison), 2)
        batchStdev = round(np.std(numBatchComparison), 2)
        ballotMean = round(np.mean(numBallotBatch), 2)
        ballotStdev = round(np.std(numBallotBatch), 2)
        o1Mean = round(np.mean(o1Counter), 2)
        o1Stdev = round(np.std(o1Counter), 2)
        o1BMean = round(np.mean(o1Batches), 2)
        o1BStdev = round(np.std(o1Batches), 2)
        
        batchCompar_writer.writerow([""])
        batchCompar_writer.writerow(["Margin:", str(margin) + "%"])
        batchCompar_writer.writerow(["", "Average Number", "Stdev", "Variance"])
        batchCompar_writer.writerow(["Number of Batches", batchMean, batchStdev])
        batchCompar_writer.writerow(["Number of Ballots", ballotMean, ballotStdev])
        batchCompar_writer.writerow(["Number of Overvote Ballots", o1Mean, o1Stdev])
        batchCompar_writer.writerow(["Number of Overvote Batches", o1BMean, o1BStdev])
        

def main():
    if (os.path.exists("2020_CT_Election_Data.json")):
        #Imports JSON file with election population
        inputFile = open(os.path.join(sys.path[0], "2020_CT_Election_Data.json"), "r")
        jsonFile = json.load(inputFile)
        if jsonFile is None:
            print("Invalid Input Data: Please make sure the JSON file is in the directory!")
            return
    else:
        jsonFile = None
    
    tests(jsonFile)
    
    inputFile.close()


        
if __name__ == "__main__":
    main()