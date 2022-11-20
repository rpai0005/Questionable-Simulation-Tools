'''
Copyright 2022 Abigail Harrison

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

from Election_Simulation import Election
from election_files import *
from shutil import rmtree

def pollingSetup(E1):
    '''
    Summary: Creates a ballot manifest and election tabulation file for the given election object. In a normal audit, this would be input
    by the audit administrator.
    Parameters: Election object
    '''
    #Comment out this function in a real audit
    pollingFiles(E1)

def readFiles():
    '''
    Summary: Reads election data from ballot manifest and tabulation
    Parameters: Ballot manifest named 'electionManifest.csv' and tabulation named 'electionTabulation.csv'
    Returns: Number of ballots in the election, number of votes for winner and runnerup, manifest/tabulation file paths
    '''
    #Read election data from the tabulation file
    tabulation_file = str(os.path.join(sys.path[0], 'electionTabulation.csv'))
    numBallots, winnerBallots, runnerupBallots, margin = readTabulation(tabulation_file)
    #Read election data from the manifest file
    manifest_file = str(os.path.join(sys.path[0], 'electionManifest.csv'))
    return numBallots, winnerBallots, runnerupBallots, tabulation_file, manifest_file

def roundSample(numBallots, winnerBallots, runnerupBallots):
    '''
    Summary: Uses _pollingSample() function from Election_Simulation.py to return a sample size based on the ballot observations
    Parameters: Number of ballots in the election, and number for the winner and runner-up
    Returns: An audit sample size
    '''
    E1 = Election(numBallots, 0, 0, 0, 0, 0)
    size = E1._pollingSample(numBallots, winnerBallots, runnerupBallots)
    print("Ballots to audit this round:", size)
    return size

def removeWorkingDir():
    #remove files from previous run if dir exists 
    path =  'ballot_polling_pull_list'
    isdir = os.path.isdir(path) 
    if isdir:
        rmtree(path)

def ballotSelect(size, seed, manifest_file):
    '''
    Summary: Uses batch sizes as weights to determine which batches to pull from, and then which ballots from the batches to pull
    Parameters: Sample size (to know how many ballots to pull), seed for randomness, and manifest file path
    Returns: A CSV file with a list of ballots to pull to audit
    '''
    random.seed(seed)
    pullList = {} #batch name: list of ballot positions
    #Read data from the manifest file
    numBallots, batchNames, batchSizes, ballotsPerBatchTotal = readManifest(manifest_file)
    batchWeight = []

    #Create batch weights
    for i in range(len(batchSizes)): 
        batchWeight.append(batchSizes[i]/numBallots) 

    #Select ballot batches based on weights, then select random ballot from the batch
    ballotBatches = random.choices(batchNames, weights = batchWeight, k = size)
    ballotBatches.sort()
    for batch in ballotBatches:
        #Checks if the batch is already in the dict
        if batch not in pullList:
            pullList[batch] = []
        #Pulls ballot
        ballotID = random.randint(1, int(ballotsPerBatchTotal[batch]))
        #Ensure no duplicate ballots are added to list since sampling with replacement
        if ballotID not in pullList[batch]:
            pullList[batch].append(ballotID)

    #Removes current directory and makes new one
    removeWorkingDir()
    save_path =  'ballot_polling_pull_list'
    isdir = os.path.isdir(save_path) 
    if not isdir:
        os.mkdir(save_path)

    #Creates pull sheets for each batch
    numToAudit = 0
    print("Making ballot pull sheets now.")
    for batch in pullList:
        fileName = batch + "_Pull_Sheet.csv"
        completeName = os.path.join(sys.path[0], save_path, fileName)
        pullsheet = open(completeName, mode = 'w', newline = '')
        pullsheet_writer = csv.writer(pullsheet)
        pullsheet_writer.writerow(["Batch Name", "Ballot Position in Batch"])
        pullList[batch].sort()
        for ballot in pullList[batch]:
            numToAudit += 1
            pullsheet_writer.writerow([batch, ballot])
        pullsheet.close()

    print("After sampling, there are", numToAudit, "ballots to pull. Check ballot_polling_pull_list folder for the list of ballots.")

def roundInput():
    '''
    Summary: Input for number of Winner and Runnerup votes from sample
    Returns: Sampled Winner and Runnerup votes
    '''
    sampledWinner = input("Please enter the number of winner ballots: ")
    sampledRunnerup = input("Please enter the number of runnerup ballots: ")
    return sampledWinner, sampledRunnerup

def calculateRisk(sw, T, sampledWinner, sampledRunnerup):
    '''
    Summary: Uses math from Stark's A Gentle Introduction to calculate the risk limit for the round
    Parameters: sw and T, the number of Winner votes and the number of Runnerup votes in the sample
    Returns: Test statistic T
    '''
    while (sampledWinner > 0):
        T *= sw/.5
        sampledWinner -= 1
    while (sampledRunnerup > 0):
        T *= (1 - sw)/.5
        sampledRunnerup -= 1
    return T

def pollingAudit(E1 = None, flag = 0):
    '''
    Summary: Run a ballot polling audit.
    Parameters: An election object
    Returns: The observed risk limit
    '''
    if (flag == 1):
        #This creates a ballot manifest and tabulation. In a real audit, flag = 0 so this is not run
        pollingSetup(E1)
    #Reads in data from the tabulation and ballot manifest
    numBallots, winnerBallots, runnerupBallots, tabulation_file, manifest_file = readFiles()
    seed = 2368607141
    T = 1 #Test statistic for ballot polling risk limit
    #Continues running rounds until risk limit is met
    while True:
        #Calculate a sample size
        sampleSize = roundSample(numBallots, winnerBallots, runnerupBallots)
        #Select the ballots from the sample size
        ballotSelect(sampleSize, seed, manifest_file)
        #Enter the number of Winner ballots and Runnerup ballots observed in the sample
        sampledWinner, sampledRunnerup = roundInput()
        sampledWinner = int(sampledWinner)
        sampledRunnerup = int(sampledRunnerup)
        #Calculate the observed risk limit
        sw = winnerBallots/numBallots
        T = calculateRisk(sw, T, sampledWinner, sampledRunnerup)
        #Determine if more auditing is necessary
        if (T >= 1/E1.riskLimit):
            print("Audit complete. You may stop auditing. Observed risk limit = ", 1/T)
            break
        elif (1/T > 1): #How to actually get this value?
            raise ValueError("A full hand recount is necessary to determine the winner.")
        else:
            print("Another round is necessary. Observed risk limit for the round =", 1/T)
            winnerBallots = sampledWinner
            runnerupBallots = sampledRunnerup
            numBallots = sampleSize
