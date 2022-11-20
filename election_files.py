'''
Copyright 2022 Anike Braun, Abigail Harrison

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

from Election_Simulation import *

def fileSetup(E1):
    #run _marginOfVictory, _distributeBallots to create simulated ballots
    E1._marginOfVictory()   
    E1._distributeBallots()

def createEmptyDict(E1):
    #generate list of random numbers to later assign to imprintedID for each ballot, create empty dict for recordID
    recordID_dict = {}
        
    #set values for .town, .batch for each ballot
    for i in E1.ballotList:
        b = E1.ballotList[i]
        b.town, b.batch = E1._setTownAndBatch("Comparison")
        #create dictionary for recordID number
        recordID_dict[b.town+str(b.batch)] = [0,0,0]  #key: b.town+b.batch, value: [total votes, winner votes, loser votes]

    return recordID_dict

def readManifest(manifest_file):
    '''
    Function to read manifest file
    Returns: total number of ballots
    '''
    #open file, skip header
    readManifest = open(manifest_file, mode = 'r', newline = '')
    manifest_reader = csv.reader(readManifest)
    next(manifest_reader)

    numBallots = 0
    batchNames = [] #list of batch names
    batchSizes = [] #list of batch sizes 
    ballotsPerBatchTotal = {} #dict of batch names: ballots per batch

    #count number ballots
    for ballot in manifest_reader: 
        numBallots += int(ballot[3])
        batchNames.append(ballot[2])
        batchSizes.append(int(ballot[3]))
        ballotsPerBatchTotal[ballot[2]] = ballot[3]

    readManifest.close()

    return numBallots, batchNames, batchSizes, ballotsPerBatchTotal

def readTabulation(tab_file):
    '''
    Function to read tabulation file
    Returns: total number of ballots, ballots for winner, ballots for runnerup, margin
    '''
    #open file, skip header
    with open(tab_file, mode = 'r', newline = '') as readTab:
        tabReader = csv.reader(readTab)
        next(tabReader)

        numBallots = winnerBallots = runnerupBallots = 0
    
        #count number ballots total, winner, runnerup 
        for batch in tabReader: 
            numBallots += int(batch[2])
            winnerBallots += int(batch[3])
            runnerupBallots += int(batch[4])

        #calculate margin
        margin = ((winnerBallots / numBallots) - (runnerupBallots / numBallots))*100

        return numBallots, winnerBallots, runnerupBallots, margin

def createManifest(recordID_dict):
    #write to manifest csv file 
    electionManifest = open('electionManifest.csv', mode = 'w', newline = '')
    man_writer = csv.writer(electionManifest)
    man_writer.writerow(['Container', 'Tabulator', 'Batch Name', 'Number of Ballots'])
    for i in sorted(recordID_dict.keys()):
        town = ''.join((x for x in i if not x.isdigit())) #remove digits to get town name 
        man_writer.writerow(["Box 1", 'Tabulator 1', i, recordID_dict[i][0]])
    print('Manifest created')
        
    electionManifest.close()

def createTabulation(recordID_dict):
    #write tabulation file
    with open('electionTabulation.csv', mode = 'w', newline = '') as electionTabulation:
        tab_writer = csv.writer(electionTabulation)
        tab_writer.writerow(['Town', 'BatchNum', 'Size', 'Winner', 'Loser'])
        for i in sorted(recordID_dict.keys()):
            town = ''.join((x for x in i if not x.isdigit())) #remove digits to get town name 
            tab_writer.writerow([town, i, recordID_dict[i][0], recordID_dict[i][1], recordID_dict[i][2]])
    print('Tabulation created')


def createCVR1(E1, recordID_dict):
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

    imprintedID_list = random.sample(range(1, len(E1.ballotList)+1), len(E1.ballotList)) 

    #write to csv file for each ballot in ballotList
    for i in E1.ballotList:
        b = E1.ballotList[i] 
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

    createManifest(recordID_dict)

    electionCVR.close()

def createCVR2(E1, recordID_dict):
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
            
    o1 = E1.overvotes1
    u1 = E1.undervotes1 
    o2 = E1.overvotes2 
    u2 = E1.undervotes2 
        
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

    createTabulation(recordID_dict)


def lazyFiles(E1):
    #create the necessary files needed for lazy_backend
    fileSetup(E1)
    CVR1_dict = createEmptyDict(E1)
    CVR2_dict = createEmptyDict(E1)
    #Create CVR1 + Manifest
    createCVR1(E1, CVR1_dict)
    #Create CVR2 + Tabulation
    createCVR2(E1, CVR2_dict)

def pollingFiles(E1):
    #create the necessary files needed for polling_backend
    fileSetup(E1)
    recordID_dict = createEmptyDict(E1)
    #Populate recordID_dict (for lazyFiles, this is done in the createCVR1 function)
    for i in E1.ballotList:
        b = E1.ballotList[i] 
        recordID_dict[b.town+str(b.batch)][0] += 1
        if b.vote == "winner":
            recordID_dict[b.town+str(b.batch)][1] += 1 #update winner count
        elif b.vote == "runnerup":
            recordID_dict[b.town+str(b.batch)][2] += 1 #update loser count
    #Create Manifest
    createManifest(recordID_dict)
    #Create Tabulation
    createTabulation(recordID_dict)