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
import numpy as np
import random
import json
import os.path
import sys
from math import log, ceil 
import csv
from adaptive_backend import *


class Ballot(object):
    '''
    Summary: Ballot object containing values necessary to conduct an audit
    '''
    def __init__(self, id = None):
        self.number = id  
        self.error = "normal" #normal, undervote1, undervote2, overvote1, overvote2 for no error, 1/2-vote understatements, 1/2-vote overstatments
        self.vote = "waiting" #waiting, winner, runnerup
        self.batch = None #_setTownAndBatch
        self.town = None #_setTownAndBatch  
        
        
class Election(object):
    def __init__(self, numBallots, margin, o1, u1, o2, u2, riskLimit = 0.05, gamma = 1.1, simulationType = 1, jsonFile = None):
        self.numBallots = numBallots
        self.margin = margin
        self.overvotes1 = o1
        self.undervotes1 = u1
        self.overvotes2 = o2
        self.undervotes2 = u2
        self.riskLimit = riskLimit 
        self.gamma = gamma
        self.simulationType = simulationType
            
        self.winnerBallots = self.runnerupBallots = 0 #Number of ballots the winner/runnerup receives; set with _marginOfVictory
        self.ballotList = {} #ID: ballot object; set with _distributeBallots
        self.ballotPolling, self.ballotComparison = [], [] #List of ballots pulled in ballot polling/ballot comparison audit
        
        #Initializes lists/dictionaries using data from the JSON file
        #Functions that require this data: _setTownAndBatch, _getBatchNumbers, _ballotsPerTown
        if jsonFile is not None:
            self.numPollingPerTown, self.numComparisonPerTown = {}, {} #Town: num of ballots to audit for polling/comparison
            self.tabulatorBatch = {} #Tracks current number of ballots flagged for audit per batch; Town: [# of ballots in batch 1, batch 2, ...]
            self.batchMaxSize = {} #Track maximum ballots per batch; Town: [# of batches in the town, max size of batch 1, batch 2, ..., absentee batch]
            self.townList = [] #List of town names
            self.townPopulation = [] #List of town population (used for weight distribution)
            self.staticVotersPerTown = {} #Town: number of voters in the town
            for townName in jsonFile:
                town = townName["Town"]
                townVoters = int(townName["Voter Population"])
                pollingPlaces = int(townName["Polling Places"])
                self.numPollingPerTown[town] = self.numComparisonPerTown[town] = 0 #Initializes int in dict
                self.townList.append(town)
                self.townPopulation.append(townVoters)
                self.staticVotersPerTown[town] = townVoters
                #Initializes dictionaries for batches; one batch for each polling place and an additional absentee batch
                self.tabulatorBatch[town], self.batchMaxSize[town] = [], []
                self.batchMaxSize[town].append(pollingPlaces + 1) #Indicates number of batches per town
                absentee = .05 * townVoters #Batch for absentee ballots; about 5% of town's population
                nonAbsentee = townVoters - absentee
                #Records data per polling place/precinct
                for i in range(0, pollingPlaces):
                    self.tabulatorBatch[town].append(0) #Initializes int
                    self.batchMaxSize[town].append(round(nonAbsentee/pollingPlaces)) #Records the maximum number of voters per precinct
                #Absentee batches
                self.tabulatorBatch[town].append(0)
                self.batchMaxSize[town].append(absentee)
            self.staticBatchSize = self.batchMaxSize #Total number of voters in a precinct; also static
        
    def _marginOfVictory(self):
        '''
        Summary: Calculates the number of ballots each candidate will receive depending on the margin-of-victory
        Parameters: The total number of ballots and the input margin
        Returns: The number of ballots for the winner and the number of ballots for the runner-up
        
        Example: ballots = 200,000; margin = 5%
        self.winnerBallots = 105,000
        self.runnerupBallots = 95,000
        Sometimes may be a ballot off of the total due to rounding 
        '''
        ballots = self.numBallots - self.overvotes1 - self.undervotes1 - self.overvotes2 - self.undervotes2 #Number of ballots with valid votes
        #Gives the winner margin% more votes than runner-up
        ballotsInMargin = ballots * float(self.margin/100)
        self.winnerBallots = round(1/2 * (ballots + ballotsInMargin))
        self.runnerupBallots = round(1/2 * (ballots - ballotsInMargin))
           
    def _distributeBallots(self):
        '''
        Summary: Randomly distributes the ballots by ID between overstatements, understatements, winner, and runner-up
        Does this by iterating through the number of ballots, assigning values, then shuffling the ballots and assigning IDs
        Parameters: Number of ballots the winner/runner-up received, number of overstatements and understatements
        Returns: Dict ballotList full of ballot IDs and ballot objects
        '''
        #Counter variables
        winnerCounter = self.winnerBallots
        runnerupCounter = self.runnerupBallots
        overvoteCounter = self.overvotes1
        undervoteCounter = self.undervotes1
        overvote2Counter = self.overvotes2
        undervote2Counter = self.undervotes2
        ballots = []
        #Initializes ballots with vote and type, appends to ballots
        for ID in range(self.numBallots):
            b = Ballot()
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
        #Shuffles the list of ballots for "randomness"
        #TO DO: seed randomness
        random.shuffle(ballots)
        #Assigns ballot IDs to the now shuffled-order of ballots and adds to ballotList dict
        i = 0
        for ballot in ballots:
            ballot.number = i
            self.ballotList[i] = ballot
            i += 1
            
    def _setTownAndBatch(self, auditID):
        '''
        Summary: Uses the random.choices to distribute ballots across towns based on their population (weights). Once a town is chosen for a ballot, 
        the distribution is updated. A batch is selected within the town; each town has number of polling places + 1 batch for absentee ballots.
        For example, if a town has 4 polling places, it has 5 batches - 5% of the ballots in a town are set aside for the absentee batch, and the
        rest are distributed evenly between the 4 polling places.
        Parameters: Type of audit (only distributes batches for comparison audits), JSON file information
        Returns: The town and batch a ballot belongs to
        '''
        #Selects random town then updates the distribution
        #TO DO: seed randomness
        batchID = None
        ballotTown = random.choices(self.townList, weights = self.townPopulation, k = 1)
        ballotTown = ballotTown[0]
        townIndex = self.townList.index(ballotTown)
        self.townPopulation[townIndex] -= 1
        if (auditID == "Comparison"):
            while 1:
                numBatches = self.batchMaxSize[ballotTown][0] #Finds the number of batches in the town
                #TO DO: seed randomness
                #Issue with seed randomness - what if the batch gets full? Not sure how to implement in a way to prevent that
                #Possible solution: make a list of Batch IDs and use random to find index? Then remove Batch ID from list when full
                batchID = random.randint(0, numBatches - 1) #Selects a random batch
                if (self.batchMaxSize[ballotTown][batchID + 1] > 0): #Checks that the random batch isn't full already
                    self.batchMaxSize[ballotTown][batchID + 1] -= 1 #Adjusts the remaining ballots that can be added to the batch
                    self.tabulatorBatch[ballotTown][batchID] += 1 #Adds one ballot to that batch
                    break
        return ballotTown, batchID
    
    def _getBatchNumbers(self):
        '''
        Summary: For simplicity purposes, one batch = one precinct. Finds the number of ballots that need to be rescanned across all precincts 
        in a town for Lazy CVR. Looks at all the batches that has a ballot flagged for audit, then records the number of batches per town and 
        the total number of voters in that town. Primarily used for Lazy CVR efficiency calculations.
        Parameters: self.staticBatchSize and self.tabulatorBatch, JSON file information
        Returns: A dict that contains the number of precincts per town flagged for audit and the total population of these precincts
        '''
        lazyBallots = {} #Town: [number of precincts flagged for audit, total population of flagged precincts]
        for town in self.tabulatorBatch:
            lazyBallots[town] = [0, 0] #Initializes each town to 0 precincts to audit 
            #Iterates through each batch/precinct within a town. If there is a ballot to audit in that batch, add 1 to the number of precincts
            #flagged for audit and add the population size of that precinct to the total
            for i in range(0, len(self.tabulatorBatch[town]) - 1):
                if (self.tabulatorBatch[town][i] > 0):
                    lazyBallots[town][0] += 1
                    lazyBallots[town][1] += self.staticBatchSize[town][i + 1]
        return lazyBallots

    def _pollingSample(self, numBallots = -1, winnerBallots = -1, runnerupBallots = -1):
        '''
        Summary: Uses BRAVO math to from https://www.stat.berkeley.edu/~stark/Vote/ballotPollTools.htm to create an initial sample size for
        ballot polling audit 
        Parameters: Number of ballots, number of winner ballots, and number of runnerup ballots
        Returns: The initial sample size for a ballot polling audit
        TO DO: Verify math for multiple rounds
        '''
        if (numBallots == -1):
            numBallots = self.numBallots
        if (winnerBallots == -1):
            winnerBallots = self.winnerBallots
        if (runnerupBallots == -1):
            runnerupBallots = self.runnerupBallots
        N = numBallots
        Nwl = winnerBallots + runnerupBallots
        pw = winnerBallots/Nwl
        pl = runnerupBallots/Nwl
        sw = pw/(pw + pl)

        numer = np.log(1/self.riskLimit) + np.log(2 * sw)/2
        denom = pw * np.log(2*sw) + pl * np.log(2 - 2 * sw)
        ASN = (N/Nwl) * numer/denom

        if (ASN > self.numBallots):
            ASN = self.numBallots

        return ceil(ASN)
    
    def _ballotPolling(self, maxBallots = -1, minBallots = 1):
        '''
        Summary: Follows the steps to conduct a ballot polling audit utilizing the steps described in
        BRAVO: Ballot-polling Risk-limiting Audits to Verify Outcomes
        Mark Lindeman, Philip B. Stark, Vincent S. Yates
        https://www.usenix.org/system/files/conference/evtwote12/evtwote12-final27.pdf
        (page 5 section 6, Special Case: Contests with two candidates (and majority contests))
        Parameters: A list of ballots 
        Returns: Number of ballots that need to be looked at in a ballot polling audit and if the risk limit was met (only important
        if utilizing a minimum and maximum number of ballots; otherwise, the success rate will be 100 as the simulation continues the audit until 
        the risk limit is met)
        '''
        if (maxBallots == -1):
            maxBallots = self.numBallots
        numToAudit = 0
        prvRound = 0 #Number of ballots examined in the previous rounds, if doing multiple rounds
        winnerCounter = 0
        runnerupCounter = 0
        roundCounter = 0
        successTracker = 0 #100 when the risk limit is met, 0 otherwise
        T = 1 #Test statistic
        sw = self.winnerBallots/self.numBallots #Proportion of valid votes cast for winner
        while 1:
            numToAudit += 1
            #Sampling with replacement, then add the pulled ballot to the list of ballots for ballot polling
            #TO DO: seed randomness
            pullID = random.randint(0, self.numBallots - 1)
            randomBallot = self.ballotList[pullID]
            self.ballotPolling.append(randomBallot)
            #Checks that ballot isn't an understatement or overstatement; then check the vote and adjust T accordingly
            if (randomBallot.error == "normal"):
                if (randomBallot.vote == "winner"):
                    T *= sw/.5
                    winnerCounter += 1
                else:
                    T *= (1 - sw)/.5
                    runnerupCounter += 1
            #Returns when either the entered sample size is examined, the maximum number of ballots is examined, or the risk limit is met
            if (minBallots == maxBallots and numToAudit == minBallots or numToAudit == maxBallots):
                if (T >= 1/self.riskLimit):
                    successTracker = 100
                    return numToAudit + prvRound, successTracker
                if (self.simulationType == 1): #return audited number and % of times risk limit was met if doing incremental auditing
                    return numToAudit + prvRound, successTracker
                #If doing rounds, update maxBallots and start over
                else: 
                    prvRound += numToAudit
                    roundCounter += 1
                    if (roundCounter > 10):
                        raise RuntimeError("Excessive Number of Rounds. Please run the simulation with less discrepancies.")
                    numToAudit = 0
                    if (winnerCounter >= runnerupCounter):
                        #Note: using cumulative results from previous rounds
                        #TO DO: Verify if correct method
                        maxBallots = self._pollingSample(prvRound, winnerCounter, runnerupCounter)
                    else:
                        print("Audit found more votes for the runner-up candidate than reported winner. Please conduct a full-hand recount.")
                        print("Force quitting ballot polling audit. Please note that simulation results are inaccurate.")
                        return numToAudit + prvRound, successTracker
                    print("Risk limit was not met for ballot polling audit, starting new round. New sample size =", maxBallots)
            elif (T >= 1/self.riskLimit and numToAudit >= minBallots and self.simulationType == 1): 
                successTracker = 100
                return numToAudit + prvRound, successTracker

    def _comparisonSample(self, overvotes1 = -1, undervotes1 = -1, overvotes2 = -1, undervotes2 = -1, numBallots = -1):
        '''
        Summary: Uses Kaplan-Markov sample sizes to create an initial sample size for ballot comparsion audit 
        Parameters: Number of one- and two-vote over- and understatements, risk limit, and gamma
        Returns: The initial sample size for a ballot comparison audit
        '''
        if (overvotes1 == -1):
            overvotes1 = self.overvotes1
        if (overvotes2 == -1):
            overvotes2 = self.overvotes2
        if (undervotes1 == -1):
            undervotes1 = self.undervotes1
        if (undervotes2 == -1):
            undervotes2 = self.undervotes2
        if (numBallots == -1):
            numBallots = self.numBallots

        margin = float(self.margin/100)
        
        #Overstatement/understatement rates
        or1 = overvotes1/numBallots
        ur1 = undervotes1/numBallots
        or2 = overvotes2/numBallots
        ur2 = undervotes2/numBallots

        est = float('nan')

        #Kaplan-Markov
        denom = log( 1 - margin / (2 * self.gamma) ) -\
                or1 * log(1 - 1 /(2 * self.gamma)) -\
                or2 * log(1 - 1 / self.gamma) -\
                ur1 * log(1 + 1 /(2 * self.gamma)) -\
                ur2 * log(1 + 1 / self.gamma)

        if (denom < 0):
            est = ceil((log(self.riskLimit)/denom))
        else:
            raise ValueError("The number of overstatements show a change in the election winner. This results in an infinite sample size.")
        
        return est
            
    def _ballotComparison(self, maxBallots = -1, minBallots = 1):
        '''
        Summary: Follows the steps to conduct a ballot comparison audit.
        TO DO: Add citation
        Parameters: ballot list
        Returns: Number of ballots that need to be looked at in a ballot comparison audit and if the risk limit was met (only important
        if utilizing a minimum and maximum number of ballots; otherwise, the success rate will be 100 as the simulation continues the audit until 
        the risk limit is met)
        '''
        if (maxBallots == -1):
            maxBallots = self.numBallots
        dilutedMargin = (self.winnerBallots - self.runnerupBallots)/self.numBallots
        alpha = self.riskLimit
        numToAudit = 0
        observedrisk = 1
        successTracker = 0 #100 when the risk limit is met, 0 otherwise
        gamma = self.gamma
        prvRound = 0 #Number of ballots examined in the previous rounds, if doing multiple rounds
        o1Counter = 0
        o2Counter = 0
        u1Counter = 0
        u2Counter = 0
        roundCounter = 0
        #Checks if the initial batch of ballots is enough to audit; if not then add another ballot and keep checking
        while 1:
            numToAudit += 1
            #Sampling with replacement, then add the pulled ballot to the list of ballots for ballot comparison
            #TO DO: seed randomness
            pullID = random.randint(0, self.numBallots - 1)
            randomBallot = self.ballotList[pullID]
            self.ballotComparison.append(randomBallot)
            #Determines if one- or two-vote over/understatement, then updates the discrepancy counter
            discCounter = 0
            if (randomBallot.error == "overvote"):
                discCounter = discCounter + 1
                o1Counter += 1
            elif (randomBallot.error == "overvote2"):
                discCounter = discCounter + 2
                o2Counter += 1
            elif (randomBallot.error == "undervote"):
                discCounter = discCounter - 1
                u1Counter += 1
            elif (randomBallot.error == "undervote2"):
                discCounter = discCounter - 2
                u2Counter += 1
            #Calculates the current risk limit
            observedrisk = observedrisk * (1-(dilutedMargin/(2*gamma)))/(1-(discCounter/(2*gamma)))
            #Returns when either the entered sample size is examined, the maximum number of ballots is examined, or the risk limit is met
            if (minBallots == maxBallots and numToAudit == minBallots or numToAudit == maxBallots):
                if (observedrisk < alpha):
                    successTracker = 100
                    return numToAudit + prvRound, successTracker
                if (self.simulationType == 1): #return audited number and % of times risk limit was met if doing incremental auditing
                    return numToAudit + prvRound, successTracker
                #If doing rounds, update maxBallots and start over
                else:
                    prvRound += numToAudit
                    roundCounter += 1
                    if (roundCounter > 10):
                        raise RuntimeError("Excessive Number of Rounds. Please run the simulation with less discrepancies.")
                    maxBallots = self._comparisonSample(o1Counter, o2Counter, u1Counter, u2Counter, numToAudit)
                    print("Risk limit was not met for ballot comparison audit, starting new round. New sample size =", maxBallots)
                    numToAudit, o1Counter, o2Counter, u1Counter, u2Counter = 0, 0, 0, 0, 0
            elif (observedrisk < alpha and numToAudit >= minBallots and self.simulationType == 1):
                successTracker = 100
                return numToAudit + prvRound, successTracker
            
    def _ballotsPerTown(self):
        '''
        Summary: Iterates through the list of ballots for each method and calls _setTownAndBatch for every ballot that does not yet have a town
        and batchID. Note that it does not assign batches to ballot polling ballots, as that functionality is used to determine the batches that
        need CVRs when using the lazy CVR method (which uses ballot comparison math)
        Parameters: List of ballots from the risk-limiting audits and list of ballots per batch, JSON file information
        Returns: Number of ballots pulled from each town
        '''
        #Ballots for ballot comparison audit; if a total hand recount, then return all the town information
        if (len(self.ballotComparison) == self.numBallots):
            self.numComparisonPerTown = self.staticVotersPerTown
        else:
            for ballot in self.ballotComparison:
                if (ballot.town is None):
                    ballot.town, ballot.batch = self._setTownAndBatch("Comparison")
                self.numComparisonPerTown[ballot.town] += 1
        #Ballots for ballot polling audit; if a total hand recount, then return all the town information
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


def readInput():
    '''
    Summary: Reads data from input file to be used in simulation. The file must be named Simulation_Input.txt and contain the following fields:
    Ballots=100000             #number of ballots in the election
    Overvotes1=1               #number of one-vote overstatements
    Undervotes1=1              #number of one-vote understatements
    Overvotes2=1               #number of two-vote overstatements
    Undervotes2=1              #number of two-vote understatements
    Risk Limit=0.05            #risk limit, or alpha
    Simulations per margin=1   #number of simulation runs (data is averaged at the end)
    Gamma=1.1                  #gamma (used in ballot comparison calculations, generally 1.1)
    Margin=1                   #margin of victory, each new margin must be a new line (as shown)
    Margin=2
    ...                   
    TO DO: CHANGE FUNCTIONALITY, currently disabled
    Alternatively, the margin lines can be written as so: Margin=MOV, minimum number of ballots you wish to audit, maximum number of ballots you
    wish to audit. Ex:
    Margin=5, 20, 100
    means there is a 5% margin of victory, you want the simulation to look at a minimum of 20 ballots and a maximum of 100 ballots. If you wish
    to do a set sample size, the minimum and maximum ballots must be the same number (ex. Margin=5, 100, 100)
    
    This file is necessary to conduct a simulation from scratch with no premade CVRs or manifests. It is also necessary to generate mock files.
    Parameters: Simulation_Input.txt
    Returns: Variables necessary to create the Election object
    '''
    #Open txt file
    f = open(os.path.join(sys.path[0], "Simulation_Input.txt"), "r")
    if f is None:
        print("Invalid Input Data: Please make sure the TXT file is in the directory!")
        return
    electionData = [] #List to read txt file into
    simulationData = [] #List to hold the data values as the txt file is read
    for i in range(8):
        electionData.append(f.readline())
        #Anything after = is read as a value
        for j in range(0, len(electionData[i])):
            if (electionData[i][j] == "="):
                try:
                    simulationData.append(float(electionData[i][(j + 1):]))
                    break
                except ValueError:
                    simulationData.append(None)
    numBallots = int(simulationData[0])
    overvotes1 = int(simulationData[1])
    undervotes1 = int(simulationData[2])
    overvotes2 = int(simulationData[3])
    undervotes2 = int(simulationData[4])
    riskLimit = float(simulationData[5])
    num = int(simulationData[6])
    gamma = float(simulationData[7])
    margins = [] #0: margin, 1: minBallots, 2: maxBallots
    #Reads the margin lines into the margins list
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
    #Checks to ensure data was entered properly
    if (num < 1):
        raise ValueError("The number of simulations must be greater than or equal to 1.")
    elif (numBallots is None or overvotes1 is None or undervotes1 is None or overvotes2 is None or undervotes2 is None or riskLimit is None or num is None or margins is None):
        raise ValueError("There is missing data in Simulation_Input.txt. Please check the file and try again.")
    for lst in margins:
        if (len(lst) > 1):
            if (lst[1] > numBallots):
                raise ValueError("The minimum number of ballots you wish to audit is larger than the total number of ballots.")
        if (len(lst) > 2):
            if (lst[1] > lst [2]):
                raise ValueError("The minimum number of ballots you wish to audit is larger than the maximum number of ballots.")
    #Close txt file and return the variables
    f.close()
    return simulationData, margins

def dataToValues(simulationData):
    numBallots = int(simulationData[0])
    overvotes1 = int(simulationData[1])
    undervotes1 = int(simulationData[2])
    overvotes2 = int(simulationData[3])
    undervotes2 = int(simulationData[4])
    riskLimit = float(simulationData[5])
    num = int(simulationData[6])
    gamma = float(simulationData[7])
    return numBallots, overvotes1, undervotes1, overvotes2, undervotes2, riskLimit, num, gamma

def statisticsData(dataList):
    mean = round(np.mean(dataList), 2)
    stdev = round(np.std(dataList), 2)
    variance = round(np.var(dataList), 2)
    return mean, stdev, variance

def collectData(jsonFile, simulationData, margins, flag = 0, simulationType = 2):
    '''
    Summary: Runs the simulation num number of times and averages the data. Records all data in one file: 
    Lazy_CVR_Data.csv - includes number of ballots pulled, ballots per town, number of precincts flagged for audit, etc.
    Variables contain C if they track data for comparison audits, and P if they track data for polling audits
    Flag parameter set to 0 by default to only conduct a ballot comparison audit; other options is 1 to conduct both polling and comparison audit
    Type 1 for incremental ballot audit, type 2 for rounds
    Parameters: Data from readInput() function
    '''
    #Simulation Data from readInput()
    numBallots, overvotes1, undervotes1, overvotes2, undervotes2, riskLimit, num, gamma = dataToValues(simulationData)

    #Create CSV file and write header
    simulation = open('Lazy_CVR_Data.csv', mode = 'w', newline='')
    simulation_writer = csv.writer(simulation)
    simulation_writer.writerow(["Number of ballots", numBallots, "Overvotes", overvotes1 + overvotes2, "Undervotes", undervotes1 + undervotes2, "Number of Simulations", num, "Risk Limit", riskLimit])

    #Run the simulation for each margin
    for run in range(0, len(margins)):
        townP, townPlist, townPdata = {}, {}, {} #Polling data: ballots per town, collection of townP (to average), average data per town
        townC, townClist, townCdata = {}, {}, {} #Comparison data: ballots per town, collection of townC (to average), average data per town
        #Fill in dictionaries with town names
        for town in jsonFile:
            townPlist[town["Town"]], townClist[town["Town"]], townPdata[town["Town"]], townCdata[town["Town"]] = [], [], [], []
        tabulatorSize, tabulatorAverage = {}, {} #Tabulator batches audited for Lazy CVR, average tabulated batch data per town
        tabulatorList = [] #List of tabulatorSize
        numPolling, numComparison, countPtown, countCtown = [], [], [], [] #List of ballot polling/comparison numbers, non-zero towns for polling/comparison
        observedCSuccess = observedPSuccess = 0 #Times the risk limit was met
        margin = margins[run][0]
        #minBallots = margins[run][1]
        #maxBallots = margins[run][2]
        
        #Initial sample sizes; set below
        initialCSample = numBallots
        initalPSample = numBallots

        #Run the simulation num number of times
        for i in range(1, num + 1):
            print("Running Simulation #", i, "for", margin, "%")
            townPcount = townCcount = 0 #Tracks the number of towns with a ballot pulled from it
            E1 = Election(numBallots, margin, overvotes1, undervotes1, overvotes2, undervotes2, riskLimit, gamma, simulationType, jsonFile) 
            #Distribute ballots between winner and runnerup
            E1._marginOfVictory() 
            E1._distributeBallots()
            #Set up initial sample if done in rounds
            if (simulationType == 2):
                initialCSample = E1._comparisonSample()
                initialPSample = E1._pollingSample() 
            #Run ballot polling audit
            if (flag == 1):
                ballots, success = E1._ballotPolling(initialPSample)
                numPolling.append(ballots)
                observedPSuccess += success
            else:
                numPolling.append(0)
            #Run ballot comparison audit
            ballots, success = E1._ballotComparison()
            numComparison.append(ballots)
            observedCSuccess += success
            #Get the number of ballots and batches per town and record it into townPlist, townClist, and tabulatorList
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
        pollingMean, pollingStdev, pollingVariance = statisticsData(numPolling)
        pollingTownCount = round(np.mean(countPtown), 2)
        pollingSuccess = round(observedPSuccess/num, 2)
        comparisonMean, comparisonStdev, comparisonVariance = statisticsData(numComparison)
        comparisonTownCount = round(np.mean(countCtown), 2)
        comparisonSuccess = round(observedCSuccess/num, 2)
        #Gets mean, stdev, and variance per town and stores it in a list; 0: Average ballots, 1: standard deviation, 2: variance
        for town in townPlist:
            tabulatorAverage[town] = [0, 0] #Initialize tabulator average per town
            townMean, townStdev, townVariance = statisticsData(townPlist[town])
            townPdata[town] = [townMean, townStdev, townVariance]
            townMean, townStdev, townVariance = statisticsData(townClist[town])
            townCdata[town] = [townMean, townStdev, townVariance]
        
        #Lazy CVR data
        flagForCVR = {} #town: [number of precincts flagged, population for CVR]
        #Organizes data into flagForCVR
        for dct in tabulatorList:
            for town in dct:
                tabulatorAverage[town][0] += dct[town][0]
                tabulatorAverage[town][1] += dct[town][1]
        for town in tabulatorAverage:
            flagForCVR[town] = [0, 0]
            flagForCVR[town][0] = round(tabulatorAverage[town][0]/num, 2)
            flagForCVR[town][1] = round(tabulatorAverage[town][1]/num, 2)
            
        #Write data to CSV
        if (flag == 1):
            simulation_writer.writerow([''])
            simulation_writer.writerow(["Margin of Victory", margin])
            simulation_writer.writerow(['', "Ballot Comparison", '', '', '', '', '', '', '', '', "Ballot Polling"])
            simulation_writer.writerow(['', "Number of Ballots", "Stdev", "Variance", "Risk Limit Success", "Average Non-Zero Towns", '', '', '', '', "Number of Ballots", "Stdev", "Variance", "Risk Limit Success", "Average Non-Zero Towns"])
            simulation_writer.writerow(['', comparisonMean, comparisonStdev, comparisonVariance, str(comparisonSuccess) + "%", comparisonTownCount, '', '', '', '', pollingMean, pollingStdev, pollingVariance, str(pollingSuccess) + "%", pollingTownCount])
            simulation_writer.writerow(["Per Town:", '', '', '', "Precincts Flagged to Audit", "Population of Flagged Precincts", '', '', '', "Per Town:"])
            #Per town data
            for town in townPdata:
                simulation_writer.writerow([town, townCdata[town][0], townCdata[town][1], townCdata[town][2], flagForCVR[town][0], flagForCVR[town][1], '', '', '', town, townPdata[town][0], townPdata[town][1], townPdata[town][2]])
        #Exclude polling data if flag = 0
        if (flag == 0):
            simulation_writer.writerow([''])
            simulation_writer.writerow(["Margin of Victory", margin])
            simulation_writer.writerow(['', "Ballot Comparison"])
            simulation_writer.writerow(['', "Number of Ballots", "Stdev", "Variance", "Risk Limit Success", "Average Non-Zero Towns"])
            simulation_writer.writerow(['', comparisonMean, comparisonStdev, comparisonVariance, str(comparisonSuccess) + "%", comparisonTownCount])
            simulation_writer.writerow(["Per Town:", '', '', '', "Precincts Flagged to Audit", "Population of Flagged Precincts"])
            #Per town data
            for town in townPdata:
                simulation_writer.writerow([town, townCdata[town][0], townCdata[town][1], townCdata[town][2], flagForCVR[town][0], flagForCVR[town][1]])

    simulation.close()  
    print("Simulation complete, check Adaptive_CVR_Data.csv for the simulation data.")

def main():
    if (os.path.exists("2020_CT_Election_Data.json")):
        #Imports JSON file with election population
        inputFile = open(os.path.join(sys.path[0], "2020_CT_Election_Data.json"), "r")
        jsonFile = json.load(inputFile)
        if jsonFile is None:
            raise SyntaxError("Something is wrong with the JSON file. Please check it and try again.")
    else:
        jsonFile = None

    tests(jsonFile)
    
    inputFile.close()

        
if __name__ == "__main__":
    main()
