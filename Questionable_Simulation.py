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

    def __init__(self, id=None):
        self.number = id
        self.error = "normal"  # normal, undervote1, undervote2, overvote1, overvote2 for no error, 1/2-vote understatements, 1/2-vote overstatments
        self.vote = "waiting"  # waiting, winner, runnerup
        self.batch = None  # _setTownAndBatch
        self.town = None  # _setTownAndBatch


class Election(object):
    def __init__(self, numBallots, margin, o1, u1, o2, u2, q, riskLimit=0.05, gamma=1.1, simulationType=1,
                 questionableMath=0, qOverStateRate =1, qAuditorRate = 1, jsonFile=None):
        self.numBallots = numBallots
        self.margin = margin
        self.overvotes1 = o1
        self.undervotes1 = u1
        self.overvotes2 = o2
        self.undervotes2 = u2
        self.questionable = q
        self.riskLimit = riskLimit
        self.gamma = gamma
        self.simulationType = simulationType
        self.questionableMath = questionableMath
        self.qAsMark = qOverStateRate
        self.qAuditorRate = qAuditorRate

        self.winnerBallots = self.runnerupBallots = 0  # Number of ballots the winner/runnerup receives; set with _marginOfVictory
        self.ballotList = {}  # ID: ballot object; set with _distributeBallots
        self.ballotPolling, self.ballotComparison = [], []  # List of ballots pulled in ballot polling/ballot comparison audit

        # Initializes lists/dictionaries using data from the JSON file
        # Functions that require this data: _setTownAndBatch, _getBatchNumbers, _ballotsPerTown
        if jsonFile is not None:
            self.numPollingPerTown, self.numComparisonPerTown = {}, {}  # Town: num of ballots to audit for polling/comparison
            self.tabulatorBatch = {}  # Tracks current number of ballots flagged for audit per batch; Town: [# of ballots in batch 1, batch 2, ...]
            self.batchMaxSize = {}  # Track maximum ballots per batch; Town: [# of batches in the town, max size of batch 1, batch 2, ..., absentee batch]
            self.townList = []  # List of town names
            self.townPopulation = []  # List of town population (used for weight distribution)
            self.staticVotersPerTown = {}  # Town: number of voters in the town
            for townName in jsonFile:
                town = townName["Town"]
                townVoters = int(townName["Voter Population"])
                pollingPlaces = int(townName["Polling Places"])
                self.numPollingPerTown[town] = self.numComparisonPerTown[town] = 0  # Initializes int in dict
                self.townList.append(town)
                self.townPopulation.append(townVoters)
                self.staticVotersPerTown[town] = townVoters
                # Initializes dictionaries for batches; one batch for each polling place and an additional absentee batch
                self.tabulatorBatch[town], self.batchMaxSize[town] = [], []
                self.batchMaxSize[town].append(pollingPlaces + 1)  # Indicates number of batches per town
                absentee = .05 * townVoters  # Batch for absentee ballots; about 5% of town's population
                nonAbsentee = townVoters - absentee
                # Records data per polling place/precinct
                for i in range(0, pollingPlaces):
                    self.tabulatorBatch[town].append(0)  # Initializes int
                    self.batchMaxSize[town].append(
                        round(nonAbsentee / pollingPlaces))  # Records the maximum number of voters per precinct
                # Absentee batches
                self.tabulatorBatch[town].append(0)
                self.batchMaxSize[town].append(absentee)
            self.staticBatchSize = self.batchMaxSize  # Total number of voters in a precinct; also static

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
        ballots = self.numBallots - self.overvotes1 - self.undervotes1 - self.overvotes2 - self.undervotes2 - self.questionable # Number of ballots with valid votes
        # Gives the winner margin% more votes than runner-up
        ballotsInMargin = ballots * float(self.margin / 100)
        self.winnerBallots = round(1 / 2 * (ballots + ballotsInMargin))
        self.runnerupBallots = round(1 / 2 * (ballots - ballotsInMargin))

    def _distributeBallots(self):
        '''
        Summary: Randomly distributes the ballots by ID between overstatements, understatements, winner, and runner-up
        Does this by iterating through the number of ballots, assigning values, then shuffling the ballots and assigning IDs
        Parameters: Number of ballots the winner/runner-up received, number of overstatements and understatements
        Returns: Dict ballotList full of ballot IDs and ballot objects
        '''
        # Counter variables
        winnerCounter = self.winnerBallots
        runnerupCounter = self.runnerupBallots
        overvoteCounter = self.overvotes1
        undervoteCounter = self.undervotes1
        overvote2Counter = self.overvotes2
        undervote2Counter = self.undervotes2
        qCounter = self.questionable
        ballots = []
        # Initializes ballots with vote and type, appends to ballots
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
            elif (qCounter > 0):
                b.vote = "questionable"
                b.error = "questionable"
                qCounter -= 1
            ballots.append(b)
        # Shuffles the list of ballots for "randomness"
        # TO DO: seed randomness
        random.shuffle(ballots)
        # Assigns ballot IDs to the now shuffled-order of ballots and adds to ballotList dict
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
        # Selects random town then updates the distribution
        # TO DO: seed randomness
        batchID = None
        ballotTown = random.choices(self.townList, weights=self.townPopulation, k=1)
        ballotTown = ballotTown[0]
        townIndex = self.townList.index(ballotTown)
        self.townPopulation[townIndex] -= 1
        if (auditID == "Comparison"):
            while 1:
                numBatches = self.batchMaxSize[ballotTown][0]  # Finds the number of batches in the town
                # TO DO: seed randomness
                # Issue with seed randomness - what if the batch gets full? Not sure how to implement in a way to prevent that
                # Possible solution: make a list of Batch IDs and use random to find index? Then remove Batch ID from list when full
                batchID = random.randint(0, numBatches - 1)  # Selects a random batch
                if (self.batchMaxSize[ballotTown][batchID + 1] > 0):  # Checks that the random batch isn't full already
                    self.batchMaxSize[ballotTown][
                        batchID + 1] -= 1  # Adjusts the remaining ballots that can be added to the batch
                    self.tabulatorBatch[ballotTown][batchID] += 1  # Adds one ballot to that batch
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
        lazyBallots = {}  # Town: [number of precincts flagged for audit, total population of flagged precincts]
        for town in self.tabulatorBatch:
            lazyBallots[town] = [0, 0]  # Initializes each town to 0 precincts to audit
            # Iterates through each batch/precinct within a town. If there is a ballot to audit in that batch, add 1 to the number of precincts
            # flagged for audit and add the population size of that precinct to the total
            for i in range(0, len(self.tabulatorBatch[town]) - 1):
                if (self.tabulatorBatch[town][i] > 0):
                    lazyBallots[town][0] += 1
                    lazyBallots[town][1] += self.staticBatchSize[town][i + 1]
        return lazyBallots

    def _ballotComparison(self, maxBallots=-1, minBallots=1):
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
        #dilutedMargin = (self.winnerBallots - self.runnerupBallots) / self.numBallots
        dilutedMargin = self.margin/100
        alpha = self.riskLimit
        numToAudit = 0
        observedrisk = 1
        successTracker = 0  # 100 when the risk limit is met, 0 otherwise
        gamma = self.gamma
        prvRound = 0  # Number of ballots examined in the previous rounds, if doing multiple rounds
        o1Counter = 0
        o2Counter = 0
        u1Counter = 0
        u2Counter = 0
        roundCounter = 0
        qCounter = 0

        # Checks if the initial batch of ballots is enough to audit; if not then add another ballot and keep checking
        while 1:
            numToAudit += 1
            # Sampling with replacement, then add the pulled ballot to the list of ballots for ballot comparison
            # TODO: seed randomness
            pullID = random.randint(0, self.numBallots - 1)
            randomBallot = self.ballotList[pullID]
            self.ballotComparison.append(randomBallot)
            # Determines if one- or two-vote over/understatement, then updates the discrepancy counter
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
            elif (randomBallot.error == "questionable"):
                choice = random.random()
                qCounter+=1
                if self.questionableMath == 0:    #Baseline Approach
                    if choice <= self.qAsMark*(1-self.qAuditorRate):
                        discCounter += 1
                    elif choice >= (1-self.qAuditorRate*(1-self.qAsMark)):
                        discCounter -= 1
                elif self.questionableMath ==1:    #Bayesian Approach  
                    if choice <= self.qAuditorRate:
                        discCounter +=1-self.qAsMark
                    else:
                        discCounter -= self.qAsMark
                elif self.questionableMath == 2 and choice <= self.qAsMark:    #Conservative Approach
                    discCounter -= 1

            # Calculates the current risk limit
            observedrisk = observedrisk * (1 - (dilutedMargin / (2 * gamma))) / (1 - (discCounter / (2 * gamma)))
            # Returns when either the entered sample size is examined, the maximum number of ballots is examined, or the risk limit is met
            if (minBallots == maxBallots and numToAudit == minBallots or numToAudit == maxBallots):
                if (observedrisk < alpha):
                    successTracker = 100
                    return numToAudit + prvRound, successTracker
                if (
                        self.simulationType == 1):  # return audited number and % of times risk limit was met if doing incremental auditing
                    return numToAudit + prvRound, successTracker
                # If doing rounds, update maxBallots and start over
                else:
                    prvRound += numToAudit
                    roundCounter += 1
                    if (roundCounter > 10):
                        raise RuntimeError(
                            "Excessive Number of Rounds. Please run the simulation with less discrepancies.")
                    maxBallots = self._comparisonSample(o1Counter, o2Counter, u1Counter, u2Counter, numToAudit)
                    print("Risk limit was not met for ballot comparison audit, starting new round. New sample size =",
                          maxBallots)
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
        # Ballots for ballot comparison audit; if a total hand recount, then return all the town information
        if (len(self.ballotComparison) == self.numBallots):
            self.numComparisonPerTown = self.staticVotersPerTown
        else:
            for ballot in self.ballotComparison:
                if (ballot.town is None):
                    ballot.town, ballot.batch = self._setTownAndBatch("Comparison")
                self.numComparisonPerTown[ballot.town] += 1
        # Ballots for ballot polling audit; if a total hand recount, then return all the town information
        if (len(self.ballotPolling) == self.numBallots):
            self.numPollingPerTown = self.staticVotersPerTown
        else:
            for ballot in self.ballotPolling:
                if (ballot.town is None):
                    ballot.town, ballot.batch = self._setTownAndBatch("Polling")
                self.numPollingPerTown[ballot.town] += 1
        # Get precinct totals for LazyCVR
        lazyBallots = self._getBatchNumbers()
        return self.numPollingPerTown, self.numComparisonPerTown, lazyBallots


def tests(jsonFile):
    '''
    Control setup/audit/simulation from terminal

    Questionable Math = 0 = Baeline Approach
                      = 1 = Bayesian Approach 
                      = 2 = Conservative Approach
    '''
    # call readInput (needed for any audit/simulation run)
    numBallots, overvotes1, undervotes1, overvotes2, undervotes2, questionableVotes, riskLimit, num, gamma, margin = readInput()

    print("Margin, q_CVR_Rate, q_auditor_rate, QMath, Mean, stdev, median, 95%")
    for margin in [1,2,3]:
        qMark=.5
        auditorRate=.5
        largeMargin = 100 * (margin / 100 + questionableVotes / numBallots * qMark)
        numComparisonNormal = collectData(jsonFile, numBallots, overvotes1,undervotes1, overvotes2, undervotes2,questionableVotes, riskLimit, num, gamma, largeMargin, 0, 1, 0, qMark, auditorRate)
        numComparisonNormal.sort()
        numComparisonQuestionableProb = collectData(jsonFile, numBallots, overvotes1, undervotes1, overvotes2,undervotes2,questionableVotes, riskLimit, num, gamma, largeMargin, 0, 1, 1, qMark, auditorRate)
        numComparisonQuestionableProb.sort()
        numComparisonQuestionable = collectData(jsonFile, numBallots, overvotes1, undervotes1, overvotes2, undervotes2,questionableVotes, riskLimit, num, gamma, margin, 0, 1, 2, qMark, auditorRate)
        numComparisonQuestionable.sort()

        print(str(margin)+", "+str(qMark)+", "+str(auditorRate)+", "+str(0)+", "+str(np.mean(numComparisonNormal))+", "+str(np.std(numComparisonNormal))+", "+str(np.median(numComparisonNormal))+", "+str(numComparisonNormal[round(len(numComparisonNormal) * .95)]))
        print(str(margin) + ", "+str(qMark)+", "+str(auditorRate)+", "+ str(1) + ", " + str(np.mean(numComparisonQuestionableProb)) + ", " + str(np.std(numComparisonQuestionableProb)) + ", "+ str(np.median(numComparisonQuestionableProb)) + ", " + str(numComparisonQuestionableProb[round(len(numComparisonQuestionableProb) * .95)]))
        print(str(margin)+", "+str(qMark)+", "+str(auditorRate)+", "+str(2)+", "+str(np.mean(numComparisonQuestionable)) + ", " + str(np.std(numComparisonQuestionable)) + ", " + str(np.median(numComparisonQuestionable)) + ", " + str(numComparisonQuestionable[round(len(numComparisonQuestionable) * .95)]))

    margin=1
    for qMark in [1,.9,.8,.7,.6,.5,.4,.3,.2,.1,0]:
        for auditorRate in [qMark-.4, qMark-.2, qMark, qMark+.2, qMark+0.4]:
            if not(auditorRate < 0) and not(auditorRate > 1):
                largeMargin = 100 * (margin / 100 + questionableVotes / numBallots * qMark)
                numComparisonNormal = collectData(jsonFile, numBallots, overvotes1,undervotes1, overvotes2, undervotes2,questionableVotes, riskLimit, num, gamma, largeMargin, 0, 1, 0, qMark, auditorRate)
                numComparisonNormal.sort()
                numComparisonQuestionableProb = collectData(jsonFile, numBallots, overvotes1, undervotes1, overvotes2, undervotes2,questionableVotes, riskLimit, num, gamma, largeMargin, 0, 1, 1, qMark, auditorRate)
                numComparisonQuestionableProb.sort()
                numComparisonQuestionable = collectData(jsonFile, numBallots, overvotes1, undervotes1, overvotes2, undervotes2,questionableVotes, riskLimit, num, gamma, margin, 0, 1, 2, qMark, auditorRate)
                numComparisonQuestionable.sort()
                print(str(margin)+", "+str(qMark)+", "+str(auditorRate)+", "+str(0)+", "+str(np.mean(numComparisonNormal))+", "+str(np.std(numComparisonNormal))+", "+str(np.median(numComparisonNormal))+", "+str(numComparisonNormal[round(len(numComparisonNormal) * .95)]))
                print(str(margin) + ", "+str(qMark)+", "+str(auditorRate)+", "+ str(1) + ", " + str(np.mean(numComparisonQuestionableProb)) + ", " + str(np.std(numComparisonQuestionableProb)) + ", "+ str(np.median(numComparisonQuestionableProb)) + ", " + str(numComparisonQuestionableProb[round(len(numComparisonQuestionableProb) * .95)]))
                print(str(margin)+", "+str(qMark)+", "+str(auditorRate)+", "+str(2)+", "+str(np.mean(numComparisonQuestionable)) + ", " + str(np.std(numComparisonQuestionable)) + ", " + str(np.median(numComparisonQuestionable)) + ", " + str(numComparisonQuestionable[round(len(numComparisonQuestionable) * .95)]))

def readInput():
    '''
    Summary: Reads data from input file to be used in simulation. The file must be named Questionable_Input.txt and contain the following fields:
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
    Parameters: Questionable_Input.txt
    Returns: Variables necessary to create the Election object
    '''
    # Open txt file
    f = open(os.path.join(sys.path[0], "Questionable_Input.txt"), "r")
    if f is None:
        print("Invalid Input Data: Please make sure the TXT file is in the directory!")
        return
    electionData = []  # List to read txt file into
    simulationData = {}  # List to hold the data values as the txt file is read
    file_line = f.readline()
    while len(file_line) > 0:
        (tag, value) = file_line.split("=")
        simulationData[tag] = float(value)
        file_line = f.readline()
    numBallots = int(simulationData["Ballots"])
    overvotes1 = int(simulationData["Overvotes1"])
    undervotes1 = int(simulationData["Undervotes1"])
    overvotes2 = int(simulationData["Overvotes2"])
    undervotes2 = int(simulationData["Undervotes2"])
    riskLimit = float(simulationData["Risk Limit"])
    num = int(simulationData["Simulations per margin"])
    questionableVotes = int(simulationData["QuestionableVotes"])
    gamma = float(simulationData["Gamma"])
    margin = int(simulationData["Margin"])
    if (numBallots is None or overvotes1 is None or undervotes1 is None or overvotes2 is None or undervotes2 is None
            or riskLimit is None or num is None or margin is None or questionableVotes is None):
        raise ValueError("There is missing data in Simulation_Input.txt. Please check the file and try again.")
    # Close txt file and return the variables
    f.close()
    return numBallots, overvotes1, undervotes1, overvotes2, undervotes2, questionableVotes, riskLimit, num, gamma, margin


def statisticsData(dataList):
    mean = round(np.mean(dataList), 2)
    stdev = round(np.std(dataList), 2)
    variance = round(np.var(dataList), 2)
    return mean, stdev, variance


def collectData(jsonFile, numBallots, overvotes1, undervotes1, overvotes2, undervotes2, questionable,
                riskLimit, num, gamma, margin, flag=0, simulationType=2, questionableMath=0, qAsMark=1, qAuditor=0):
    '''
    Summary: Runs the simulation num number of times and averages the data. Records all data in one file: 
    Adaptive_CVR_Data.csv - includes number of ballots pulled, ballots per town, number of precincts flagged for audit, etc.
    Variables contain C if they track data for comparison audits, and P if they track data for polling audits
    Flag parameter set to 0 by default to only conduct a ballot comparison audit; other options is 1 to conduct both polling and comparison audit
    Type 1 for incremental ballot audit, type 2 for rounds
    Parameters: Data from readInput() function
    '''

    # Create CSV file and write header
    simulation = open('Adaptive_CVR_Data'+str(questionableMath)+'.csv', mode='w', newline='')
    simulation_writer = csv.writer(simulation)
    simulation_writer.writerow(
        ["Number of ballots", numBallots, "Overvotes", overvotes1 + overvotes2, "Undervotes", undervotes1 + undervotes2,
         "Number of Simulations", num, "Risk Limit", riskLimit, "Questionable", questionable])

    townP, townPlist, townPdata = {}, {}, {}  # Polling data: ballots per town, collection of townP (to average), average data per town
    townC, townClist, townCdata = {}, {}, {}  # Comparison data: ballots per town, collection of townC (to average), average data per town
    # Fill in dictionaries with town names
    for town in jsonFile:
        townPlist[town["Town"]], townClist[town["Town"]], townPdata[town["Town"]], townCdata[
            town["Town"]] = [], [], [], []
    tabulatorSize, tabulatorAverage = {}, {}  # Tabulator batches audited for Lazy CVR, average tabulated batch data per town
    tabulatorList = []  # List of tabulatorSize
    numPolling, numComparison, countPtown, countCtown = [], [], [], []  # List of ballot polling/comparison numbers, non-zero towns for polling/comparison
    observedCSuccess = observedPSuccess = 0  # Times the risk limit was met

    # Initial sample sizes; set below
    initialCSample = numBallots
    initalPSample = numBallots

    # Run the simulation num number of times
    for i in range(0, num):
        # print("Running Simulation #", i, "for", margin, "%")
        townPcount = townCcount = 0  # Tracks the number of towns with a ballot pulled from it
        E1 = Election(numBallots, margin, overvotes1, undervotes1, overvotes2, undervotes2, questionable, riskLimit,
                      gamma, simulationType, questionableMath, qAsMark, qAuditor, jsonFile)
        # Distribute ballots between winner and runnerup
        E1._marginOfVictory()
        E1._distributeBallots()
        # Set up initial sample if done in rounds

        ballots, success = E1._ballotComparison()
        numComparison.append(ballots)
        observedCSuccess += success
        # Get the number of ballots and batches per town and record it into townPlist, townClist, and tabulatorList
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

    # Averages the simulations and calculates stdev and variance
    pollingMean, pollingStdev, pollingVariance = statisticsData(numPolling)
    pollingTownCount = round(np.mean(countPtown), 2)
    pollingSuccess = round(observedPSuccess / num, 2)
    comparisonMean, comparisonStdev, comparisonVariance = statisticsData(numComparison)
    comparisonTownCount = round(np.mean(countCtown), 2)
    comparisonSuccess = round(observedCSuccess / num, 2)
    # Gets mean, stdev, and variance per town and stores it in a list; 0: Average ballots, 1: standard deviation, 2: variance
    for town in townPlist:
        tabulatorAverage[town] = [0, 0]  # Initialize tabulator average per town
        townMean, townStdev, townVariance = statisticsData(townPlist[town])
        townPdata[town] = [townMean, townStdev, townVariance]
        townMean, townStdev, townVariance = statisticsData(townClist[town])
        townCdata[town] = [townMean, townStdev, townVariance]

    # Lazy CVR data
    flagForCVR = {}  # town: [number of precincts flagged, population for CVR]
    # Organizes data into flagForCVR
    for dct in tabulatorList:
        for town in dct:
            tabulatorAverage[town][0] += dct[town][0]
            tabulatorAverage[town][1] += dct[town][1]
    for town in tabulatorAverage:
        flagForCVR[town] = [0, 0]
        flagForCVR[town][0] = round(tabulatorAverage[town][0] / num, 2)
        flagForCVR[town][1] = round(tabulatorAverage[town][1] / num, 2)

    # Write data to CSV
    # print(numComparison)
    if (flag == 1):
        simulation_writer.writerow([''])
        simulation_writer.writerow(["Margin of Victory", margin])
        simulation_writer.writerow(['', "Ballot Comparison", '', '', '', '', '', '', '', '', "Ballot Polling"])
        simulation_writer.writerow(
            ['', "Number of Ballots", "Stdev", "Variance", "Risk Limit Success", "Average Non-Zero Towns", '', '', '',
             '', "Number of Ballots", "Stdev", "Variance", "Risk Limit Success", "Average Non-Zero Towns"])
        simulation_writer.writerow(
            ['', comparisonMean, comparisonStdev, comparisonVariance, str(comparisonSuccess) + "%", comparisonTownCount,
             '', '', '', '', pollingMean, pollingStdev, pollingVariance, str(pollingSuccess) + "%", pollingTownCount])
        print(np.histogram(numComparison, bins=[0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200]))
    #            simulation_writer.writerow(["Per Town:", '', '', '', "Precincts Flagged to Audit", "Population of Flagged Precincts", '', '', '', "Per Town:"])
    # Per town data
    #            for town in townPdata:
    #                simulation_writer.writerow([town, townCdata[town][0], townCdata[town][1], townCdata[town][2], flagForCVR[town][0], flagForCVR[town][1], '', '', '', town, townPdata[town][0], townPdata[town][1], townPdata[town][2]])
    # Exclude polling data if flag = 0
    if (flag == 0):
        simulation_writer.writerow([''])
        simulation_writer.writerow(["Margin of Victory", margin])
        simulation_writer.writerow(['', "Ballot Comparison"])
        simulation_writer.writerow(
            ['', "Number of Ballots", "Stdev", "Variance", "Risk Limit Success", "Average Non-Zero Towns"])
        simulation_writer.writerow(
            ['', comparisonMean, comparisonStdev, comparisonVariance, str(comparisonSuccess) + "%",
             comparisonTownCount])
        simulation_writer.writerow(
            ["Per Town:", '', '', '', "Precincts Flagged to Audit", "Population of Flagged Precincts"])
        # print(np.histogram(numComparison,
        #                    bins=[0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500,
        #                          2000, 3000]))
        # Per town data
    #           for town in townPdata:
    #               simulation_writer.writerow([town, townCdata[town][0], townCdata[town][1], townCdata[town][2], flagForCVR[town][0], flagForCVR[town][1]])

    return numComparison
    simulation.close()
    print("Simulation complete, check Adaptive_CVR_Data.csv for the simulation data.")


def main():
    if (os.path.exists("2020_CT_Election_Data.json")):
        # Imports JSON file with election population
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
