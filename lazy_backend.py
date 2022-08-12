'''
Copyright 2022 Anike Braun

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
from math import log, ceil
from shutil import copy2, rmtree


def readCVR(cvr_file):
    '''
    Function to read CVR file
    Returns: total number of ballots, ballots for winner, ballots for runnerup, margin
    '''
    #open file, skip headers
    readCVR = open(cvr_file, mode = 'r', newline = '')
    CVRreader = csv.reader(readCVR)

    for i in range(4):
        next(CVRreader)

    numBallots = winnerBallots = runnerupBallots = 0

    #count number ballots total, winner, runnerup 
    for ballot in CVRreader: 
        numBallots += 1
        if ballot[8] == '1' and ballot[9] == '0':
            winnerBallots += 1
        elif ballot[8] == '0' and ballot [9] == '1':
            runnerupBallots += 1
        elif ballot[8] == '1' and ballot[9] == '1':
            #is this possible?
            winnerBallots += 1
            runnerupBallots += 1

    #calculate margin
    margin = ((winnerBallots / numBallots) - (runnerupBallots / numBallots))*100

    readCVR.close()

    return numBallots, winnerBallots, runnerupBallots, margin

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


def selectBatches(manifest_file, numToAudit, seed):
    '''
    Parameters: manifest, number of ballots to audit, seed
    Summary: selects batches for audit weighted to account for num ballots per batch
    Returns: set of batches to audit, dicts with num ballots per batch total/to audit 
    '''
    numBallots, batchNames, batchSizes, ballotsPerBatchTotal = readManifest(manifest_file)
    batchWeight = [] #list with batch weights based on election size 
    ballotsPerBatchAudit = {} #key: batch name, value: num ballots in batch to audit 

    for i in range(len(batchSizes)): 
        batchWeight.append(batchSizes[i]/numBallots) #calculate weight per batch 

    #There are two different SEEDs read in by a lazy RLA, the first to select batches and the second to
    #select ballots.  This code is deterministic if one repeatedly audits an election.  However, the
    #infrastructure for setting up an election is non-deterministic.  To verify deterministic
    #behavior one needs to conduct multiple audits
    random.seed(seed)
    batchesToAudit = random.choices(batchNames, weights=batchWeight, k=round(numToAudit))


    #check to see if duplicates allowed 
    print(str(len(batchesToAudit)) + ' ballots to audit')
    print('ballots selected from ' + str(len(set(batchesToAudit))) + ' different batches')

    #intialize values at 0
    for i in batchesToAudit: 
        ballotsPerBatchAudit[i] = 0
    #determine how times batch was selected = how many ballots per batch to be audited  
    for i in batchesToAudit: 
        ballotsPerBatchAudit[i] += 1

    #store set of batches to audit, dict of ballots per batch to audit, dict of ballots per batch total 
    batchSelect = {'batchesToAudit': set(batchesToAudit), 'ballotsPerBatchAudit': ballotsPerBatchAudit, 'ballotsPerBatchTotal': ballotsPerBatchTotal}

    return batchSelect

def correctTabulation(tabulation_file, manifest_file):
    '''
    Check if tabulation consistent with manifest, if not, adjust accordingly 
    Write any changes to electionTabulationChanges.txt
    '''
    #write contents of files to lists to make changes
    tabList = []
    manList = []
    with open(tabulation_file, mode= 'r', newline = '') as readTabulation, open(manifest_file, mode = 'r', newline = '') as readManifest:
        tabulationReader = csv.reader(readTabulation)
        manifestReader = csv.reader(readManifest) 
        next(tabulationReader) #skip header
        next(manifestReader)
        for row in tabulationReader:
            tabList.append(row)
        for row in manifestReader:
            manList.append(row)
            
    #open file to write any changes to 
    with open('electionTabulationChanges.txt', 'w') as writeChanges:
        changes = False 
        #compare the lists, if total num ballots different, then change tab total to match man total 
        for row1, row2 in zip(tabList, manList):
            if row1[2] != row2[3]:
                writeChanges.write(row1[1] + ' had total ballots changed from ' + row1[2] + ' to ' + row2[3] + '\n')
                row1[2] = row2[3]
                changes = True 

        #if winner or runnerup size larger than batch size, change winner or runnerup size to batch size 
        for row in tabList:
            if int(row[3]) > int(row[2]): #check winner size 
                writeChanges.write(row[1] + ' had winner ballots changed from ' + row[3] + ' to ' + row[2] + '\n')
                row[3] = row[2]
                changes = True 

            if int(row[4]) > int(row[2]): #check runnerup size 
                writeChanges.write(row[1] + ' had runnerup ballots changed from ' + row[4] + ' to ' + row[2] + '\n')
                row[4] = row[2]
                changes = True 
        
        if not changes: 
            writeChanges.write('No changes were made to the tabulation.\n')

    #write corrected information back to tabulation file 
    with open(tabulation_file, mode='w', newline = '') as writeTabulation:
        tabulationWriter = csv.writer(writeTabulation)
        tabulationWriter.writerow(['Town', 'BatchNum', 'Size', 'Winner', 'Loser']) #write header 
        tabulationWriter.writerows(tabList)

def batchSelect(manifest_file, tabulation_file, seed, overvotes1 = 1, undervotes1 = 1, overvotes2 = 1, undervotes2 = 1):
    '''
    Summary: takes input from "user", returns batches to be audited 
    Parameters: manifest, tabulation, seed, over/undervotes (optional)
    Returns: list of batches that CVR needs to be generated for 
    '''
    #correct tabulations before tabulation is used 
    
    correctTabulation(tabulation_file, manifest_file)

    #read information from tabulation
    numBallots, winnerBallots, runnerupBallots, margin = readTabulation(tabulation_file)

    print('numBallots, winnerBallots, runnerupBallots, margin')
    print(numBallots, winnerBallots, runnerupBallots, margin) 

    gamma = 1.1 
    riskLimit = 0.05

    #determine how many ballots need to be audited
    dilutedMargin = (winnerBallots - runnerupBallots) / numBallots
    a = riskLimit
    o1 = overvotes1
    u1 = undervotes1
    o2 = overvotes2
    u2 = undervotes2
    margin = dilutedMargin 

    numToAudit = max( o1 + o2 + u1 + u1,ceil(-2.0 * gamma * ( log(a) +
                                 o1 * log(1.0 - 1.0 / (2.0 * gamma)) +
                                 o2 * log(1.0 - 1.0 / gamma) +
                                 u1 * log(1.0 + 1.0 / (2.0 * gamma)) +
                                 u2 * log(1.0 + 1.0 / gamma)) / margin ))

    #if sample size greater than election size, raise error, go to full hand recount
    if numToAudit > numBallots: 
        raise ValueError('Sample is larger than population or is negative. Go to full hand recount.')                       
    
    selectedBatches = selectBatches(manifest_file, numToAudit, seed)
    
    #returns dict:
    #'batchesToAudit': set of batches that need CVR, 'ballotsPerBatchAudit': dict w num ballots per batch to audit, 
    #'ballotsPerBatchTotal': dict w num ballots per batch total 
    return(selectedBatches)


def lazyCVR_gen(batchesToAudit):
    '''
    Summary: generate CVRs for selected batches
             in a real audit, this wouldn't be necessary, as the files would come from user 
    Returns: Files for batches to be audited
    '''
    lazyCVR_files = set() #set of files names for lazy RLA CVRs

    #check to see if dir exists, if not, create dir 
    path =  'lazy_rla_cvr'
    isdir = os.path.isdir(path) 
    if not isdir:
        os.mkdir(path)
        
    CVR2 = str(os.path.join(sys.path[0], 'electionCVR2.csv'))

    with open(CVR2, mode = 'r', newline = '') as readCVR2:
        #open file, skip headers 
        CVR2reader = csv.reader(readCVR2)
        for i in range(4):
            next(CVR2reader) 
        
        for ballot in CVR2reader:
            batch = ballot[2]
            if batch in batchesToAudit:
                save_path = 'lazy_rla_cvr' #save files to own directory
                filename = batch + 'CVR.csv'
                completeName = os.path.join(sys.path[0], save_path, filename) 
                file_exists = os.path.exists(completeName) #check to see if file exists yet 
                lazyCVR_files.add(completeName) #add filename to set 
                writeBatchCVR = open(completeName, mode = 'a', newline = '')
                batchCVRwriter = csv.writer(writeBatchCVR)
                if not file_exists:
                    #write headers if file does not exist yet 
                    batchCVRwriter.writerow(['Test'])
                    batchCVRwriter.writerow(['','','','','','','','','Contest 1 (vote for = 1)','Contest 1 (vote for = 1)'])
                    batchCVRwriter.writerow(['','','','','','','','','Winner','Runner-Up'])
                    batchCVRwriter.writerow(['CVRNumber','TabulatorNumber', 'BatchID','RecordID', 'ImprintedID','CountingGroup','PrecinctPortion','BallotType','',''])
                batchCVRwriter.writerow(ballot) #write ballot to batch CVR 
                writeBatchCVR.close()

    return lazyCVR_files


def ballotSelect(lazyCVR_files, ballotsPerBatchAudit, ballotsPerBatchTotal, seed):
    '''
    Select ballots for audit using random seed, weighted based on batch size 
    Return blank CVR for each batch with ballots that need to be audited
    '''
    auditCVR_blank = [] #list of blank cvr filenames

    for batch in ballotsPerBatchAudit:
        path = 'lazy_rla_cvr'
        filename = str(os.path.join(sys.path[0], path, batch + 'CVR.csv'))
        new_filename_blank = str(os.path.join(sys.path[0], path, batch + 'CVR_blank.csv'))
        #add filenames to list 
        auditCVR_blank.append(new_filename_blank) 
        
        ballotsTotal = int(ballotsPerBatchTotal[batch])
        ballotsAudit = int(ballotsPerBatchAudit[batch]) 

        #determine which ballots to audit per batch using recordID (with replacement)
        #There are two different SEEDs read in by a lazy RLA, the first to select batches and the second to
        #select ballots.  This code is deterministic if one repeatedly audits an election.  However, the
        #infrastructure for setting up an election is non-deterministic.  To verify deterministic
        #behavior one needs to conduct multiple audits without setting up another election
        random.seed(seed)
        ballotsToAudit = random.choices(range(1, ballotsTotal+1), k=ballotsAudit)
 
        #open CVR for batch 
        with open(filename, mode = 'r', newline = '') as readCVR, open(new_filename_blank, mode = 'a', newline = '') as writeCVR:
            CVRreader = csv.reader(readCVR)
            #skip headers 
            for i in range(4):
                next(CVRreader)

            CVRwriter = csv.writer(writeCVR)
            #write headers 
            CVRwriter.writerow(['Test'])
            CVRwriter.writerow(['','','','','','','','','Contest 1 (vote for = 1)','Contest 1 (vote for = 1)'])
            CVRwriter.writerow(['','','','','','','','','Winner','Runner-Up'])
            CVRwriter.writerow(['CVRNumber','TabulatorNumber', 'BatchID','RecordID', 'ImprintedID','CountingGroup','PrecinctPortion','BallotType','',''])

            for ballot in CVRreader: 
                if ballot[3][0] == "n":
                    pass
                elif float(ballot[3]) in ballotsToAudit:
                    #then write to new CVR with only ballots to audit, excluding vote information 
                    CVRwriter.writerow([ballot[0], ballot[1], ballot[2], ballot[3], ballot[4], ballot[5], ballot[6], ballot[7]])
   
    return auditCVR_blank


def ballotSelect_check(lazyCVR_files, ballotsPerBatchAudit, ballotsPerBatchTotal, seed):
    '''
    Write "manual interpretation files" to be checked during audit
    if files not input by user.
    This function does not need to be called if manual interpretations
    are actually uploaded by user. 
    '''
    auditCVR_check = [] #list of correct vote cvr filenames 

    for batch in ballotsPerBatchAudit:
        path = 'lazy_rla_cvr'
        filename = str(os.path.join(sys.path[0], path, batch + 'CVR.csv'))
        new_filename_check = str(os.path.join(sys.path[0], path, batch + 'CVR_check.csv'))
        #add filenames to list 
        auditCVR_check.append(new_filename_check)

        ballotsTotal = int(ballotsPerBatchTotal[batch])
        ballotsAudit = int(ballotsPerBatchAudit[batch]) 

        #determine which ballots to audit per batch using recordID (with replacement)
        #This intentionally selects the same ballots as in ballotSelect function.  Recall
        #that this function will not be called in a real audit, as manual interpretations will
        #be input
        random.seed(seed)
        ballotsToAudit = random.choices(range(1, ballotsTotal+1), k = ballotsAudit)
 
        #this creates the cvr files the user would return with the correct/manual interpretations of votes
        CVR1 = str(os.path.join(sys.path[0], 'electionCVR1.csv'))
        with open('electionCVR1.csv', mode = 'r', newline = '') as readCVR, open(new_filename_check, mode = 'w', newline = '') as writeCVR:
            CVRreader = csv.reader(readCVR)
            #skip headers 
            for i in range(4):
                next(CVRreader)
            
            CVRwriter = csv.writer(writeCVR)
            #write headers 
            CVRwriter.writerow(['Test'])
            CVRwriter.writerow(['','','','','','','','','Contest 1 (vote for = 1)','Contest 1 (vote for = 1)'])
            CVRwriter.writerow(['','','','','','','','','Winner','Runner-Up'])
            CVRwriter.writerow(['CVRNumber','TabulatorNumber', 'BatchID','RecordID', 'ImprintedID','CountingGroup','PrecinctPortion','BallotType','',''])

            for ballot in CVRreader: 
                if ballot[2] == batch and float(ballot[3]) in ballotsToAudit:
                    CVRwriter.writerow(ballot)

    return auditCVR_check


def calculateRisk(interpretation_files, lazyCVR_files, tabulation_file, manifest_file):
    '''
    Summary: takes in files from user with manual interpretation of audited ballots, 
            compares with tabulated interpretations
    Returns: risk level
    '''
    #get values from tabulation to calculate dilutedMargin
    numBallots, winnerBallots, runnerupBallots, margin = readTabulation(tabulation_file)
    dilutedMargin = (winnerBallots - runnerupBallots)/numBallots
    observedrisk = 1
    gamma = 1.1
    o1 = u1 = o2 = u2 = 0 

    #sort files in alphabetical order so that they are compared properly
    interpretation_files.sort()
    lazy_list = list(lazyCVR_files)
    lazy_list.sort()

    #log any forceConsistent changes
    with open('forceConsistentChanges.txt', mode = 'w') as cvrChanges:
        cvrChanges.write('Batches that were forcedConsistent will be logged here. \n')
    forced = False 

    #go through each batch
    for batch1, batch2 in zip(interpretation_files, lazy_list):
        with open(batch1, mode = 'r', newline = '') as readManualVotes, open(batch2, mode ='r', newline = '') as readTabulationVotes:
            manualVotesReader = csv.reader(readManualVotes)
            tabulationVotesReader = csv.reader(readTabulationVotes)  
            #skip headers 
            for i in range(4):
                next(manualVotesReader)
                next(tabulationVotesReader)

            #returns True if consistent, False if not consistent 
            batch_name = os.path.basename(batch2)
            batch_name = batch_name.replace('CVR.csv', '')
            #batch_name = batch2.replace('lazy_rla_cvr/', '').replace('CVR.csv', '') #get batch name from filename string
            consistent = checkConsistent(manifest_file, tabulation_file, batch_name, batch2)
            #since batches forced consistent, it doesn't matter that this is where checkConisistent is called
            #because audit will always be able to run 
            if not consistent: 
                print(batch_name + ' forced consistent.')
                forceConsistent(manifest_file, tabulation_file, batch_name, batch2)
                consistent = checkConsistent(manifest_file, tabulation_file, batch_name, batch2)
                forced = True 

            #go through each ballot in each batch 
            for ballot1 in manualVotesReader: 
                for ballot2 in tabulationVotesReader:
                    #find correct ballot to compare based on CVR number 
                    if ballot1[0] == ballot2[0]:
                        randomBallotError = "none"
                        #if files consistent, proceed as normal 
                        if consistent:
                            if ballot2[8] == '0' and ballot2[9] == '0': #tabulation shows undervote/no vote
                                if ballot1[8] == '0' and ballot1[9] == '1': #manual interpretation shows loser vote
                                    randomBallotError = "overvote"  
                                    o1 += 1              
                                elif ballot1[8] == '1' and ballot1[9] == '0': #manual interpretation shows winner vote
                                    randomBallotError = "undervote"
                                    u1 += 1
                    
                            elif ballot2[8] == '1' and ballot2[9] == '1': #tabulation shows over vote
                                if ballot1[8] == '0' and ballot1[9] == '1': #manual interpretation shows loser vote
                                    randomBallotError = "overvote"
                                    o1 += 1
                                elif ballot1[8] == '1' and ballot1[9] == '0': #manual interpretation shows winner vote
                                    randomBallotError = "undervote"
                                    u1 += 1

                            elif ballot2[8] == '1' and ballot2[9] == '0': #tabulation shows winner vote
                                if ballot1[8] == '0' and ballot1[9] == '1': #manual interpretation shows loser vote
                                    randomBallotError = "overvote2"
                                    o2 += 1
                                elif ballot1[8] == '1' and ballot1[9] == '1': #manual interpretation shows overvote
                                    randomBallotError = "overvote"
                                    o1 += 1
                            
                            elif ballot2[8] == '0' and ballot2[9] == '1': #tabulation shows loser vote
                                if ballot1[8] == '1' and ballot1[9] == '0': #manual interpretation shows winner vote
                                    randomBallotError = "undervote2"
                                    u2 += 1

                        #if files not consistent, every ballot in batch has dicsrepancy 2 
                        elif not consistent:
                            print(batch_name + ' ' + 'not consistent')
                            randomBallotError = "overvote2"

                        #calculate risk 
                        discCounter=0
                        if (randomBallotError == "overvote"):
                            discCounter=discCounter+1
                        elif (randomBallotError == "overvote2"):
                            discCounter=discCounter+2
                        elif (randomBallotError == "undervote"):
                            discCounter=discCounter-1
                        elif (randomBallotError == "undervote2"):
                            discCounter=discCounter-2
                        observedrisk = observedrisk * (1-(dilutedMargin/(2*gamma)))/(1-(discCounter/(2*gamma)))

    #if no batches were inconsistent, log in file 
    if forced == False: 
        with open('forceConsistentChanges.txt', mode = 'a') as cvrChanges:
          cvrChanges.write('No batches were forced consistent.')

    return observedrisk


def checkConsistent(manifest_file, tabulation_file, batch_name, batch_file):
    '''
    Check that manifest, tabulation, and cvr are all consistent in size,
    check that cvr has unique identifiers
    '''
  
    #check that manifest, tabulation, cvr all have same batch size 
    manBatchSize = getManInfo(manifest_file, batch_name)
    tabBatchSize = getTabInfo(tabulation_file, batch_name, 'batch size')
    cvrBatchSize, cvrWinnerBallots, cvrRunnerupBallots, margin = readCVR(batch_file)

    if manBatchSize != cvrBatchSize or manBatchSize != tabBatchSize:
        print("Size mismatch "+str(manBatchSize)+", "+str(cvrBatchSize)+", "+str(tabBatchSize))
        return False 

    #check that CVR winner == tab winner, CVR loser == tab loser
    tabWinnerBallots = getTabInfo(tabulation_file, batch_name, 'winner size')
    tabRunnerupBallots = getTabInfo(tabulation_file, batch_name, 'runnerup size')
    
    if tabWinnerBallots != int(cvrWinnerBallots) or tabRunnerupBallots != int(cvrRunnerupBallots): 
        print("Tabulation mismatch "+str(tabWinnerBallots)+", "+str(cvrWinnerBallots)+", "+str(tabRunnerupBallots)+", "+str(cvrRunnerupBallots))
        return False 

    #check to make sure all identifiers unique in CVR 
    unique = uniqueCVR(batch_file)
    if not unique: 
        print("Identifiers are not unique")
        return False 

    return True 

def forceConsistent(manifest_file, tabulation_file, batch_name, batch_file):
    '''
    Fix any failures found in CVR in checkConisistent so that audit can run
    '''
    #log forceConsistent changes
    with open('forceConsistentChanges.txt', mode = 'a') as cvrChanges:
        cvrChanges.write(batch_name + 'CVR.csv was forced consistent. \nCheck ' + batch_name + 'CVR_original.csv to see CVR before forced consistent. \n\n')
    #copy inconsistent CVR to new file
    batch_name = os.path.basename(batch_name)
    #batch_name = batch_name[13:]
    copy2(batch_file,os.path.join('lazy_rla_cvr', batch_name+'CVR_original.csv'))
    
    #read contents of cvr into list to make changes
    cvrList = []
    addedBallots = 0
    with open(batch_file, mode= 'r', newline = '') as read_cvr:
        cvrReader = csv.reader(read_cvr)
        for i in range(4):
            next(cvrReader) #skip headers
        for row in cvrReader:
            cvrList.append(row)

    #if manifest, tabulation, cvr don't have same batch size, make equal 
    manBatchSize = getManInfo(manifest_file, batch_name)
    tabBatchSize = getTabInfo(tabulation_file, batch_name, 'batch size')
    cvrBatchSize, cvrWinnerBallots, cvrRunnerupBallots, margin = readCVR(batch_file)
    
    if manBatchSize != cvrBatchSize or manBatchSize != tabBatchSize:
        addedBallots = forceTotal(cvrList, manBatchSize, cvrBatchSize)

    #if CVR winner != tab winner, change to make equal
    tabWinnerBallots = getTabInfo(tabulation_file, batch_name, 'winner size')
    tabRunnerupBallots = getTabInfo(tabulation_file, batch_name, 'runnerup size')
    
    if tabWinnerBallots != int(cvrWinnerBallots):
        forceWinner(cvrList, tabWinnerBallots, int(cvrWinnerBallots))
    
    # if CVR loser != tab loser, change to make equal 
    if tabRunnerupBallots != int(cvrRunnerupBallots): 
        forceRunnerup(cvrList, tabRunnerupBallots, cvrRunnerupBallots)

    #if all identifiers not unique in CVR, change to make unique 
    unique = uniqueCVR(batch_file)
    if not unique: 
        addedBallots = forceUnique(cvrList, addedBallots)

    #write corrected information back to cvr file 
    with open(batch_file, mode='w', newline = '') as writeCVR:
        cvrWriter = csv.writer(writeCVR)
        cvrWriter.writerow(['Test'])
        cvrWriter.writerow(['','','','','','','','','Contest 1 (vote for = 1)','Contest 1 (vote for = 1)'])
        cvrWriter.writerow(['','','','','','','','','Winner','Runner-Up'])
        cvrWriter.writerow(['CVRNumber','TabulatorNumber', 'BatchID','RecordID', 'ImprintedID','CountingGroup','PrecinctPortion','BallotType','',''])
        for i in range(len(cvrList)):
            cvrWriter.writerow(cvrList[i])

def forceTotal(cvrList, manBatchSize, cvrBatchSize):
    '''
    Change cvrList so that manBatchSize = cvrBatchSize
    '''
    #while cvrBatchSize greater than manBatchSize, delete last row in CVR 
    if cvrBatchSize > manBatchSize:
        while len(cvrList) > manBatchSize:
            del cvrList[-1]

    addedBallots = 0
    #add ballot with null identifiers, 0-0 vote until cvr batch size matches manifest batch size 
    if cvrBatchSize < manBatchSize:
        while len(cvrList) < manBatchSize:
            addedBallots += 1
            cvrList.append(['nullBallot'+str(addedBallots), 'TABULATOR1', 'Avon0', 'nullRecordID'+str(addedBallots), 'nullImprintedID'+str(addedBallots), 'Pilot', 'Avon', 'BallotType', '0', '0'])

    return addedBallots

def forceWinner(cvrList, tabWinnerBallots, cvrWinnerBallots):
    '''
    If cvr winner not equal to tabulation winner, change until equal 
    '''
    #if cvr winner greater than tabulated winner, change winner votes to 0 until equal 
    if cvrWinnerBallots > tabWinnerBallots:
        for ballot in cvrList:
            if cvrWinnerBallots > tabWinnerBallots: 
                if ballot[8] == '1':
                    ballot[8] = '0'
                    cvrWinnerBallots -= 1

    #if cvr winner less than tabulated winner, change 0 votes to winner votes until equal 
    if cvrWinnerBallots < tabWinnerBallots:
        for ballot in cvrList: 
            if cvrWinnerBallots < tabWinnerBallots:
                if ballot[8] == '0':
                    ballot[8] = '1'
                    cvrWinnerBallots += 1


def forceRunnerup(cvrList, tabRunnerupBallots, cvrRunnerupBallots):
    '''
    If cvr runnerup not equal to tabulation runnerup, change until equal 
    '''
    #if cvr runnerup greater than tabulated runnerup, change runnerup votes to 0 until equal 
    if cvrRunnerupBallots > tabRunnerupBallots:
        for ballot in cvrList: 
            if cvrRunnerupBallots > tabRunnerupBallots:
                if ballot[9] == '1':
                    ballot[9] = '0'
                    cvrRunnerupBallots -= 1

    #if cvr runnerup less than tabulated runnerup, change 0 votes to runnerup votes until equal 
    if cvrRunnerupBallots < tabRunnerupBallots:
        for ballot in cvrList: 
            if cvrRunnerupBallots < tabRunnerupBallots:
                if ballot[9] == '0':
                    ballot[9] = '1'
                    cvrRunnerupBallots += 1 

def forceUnique(cvrList, addedBallots):
    '''
    Change any repeated identifiers so that all are unique 
    Any repeated IDs get assigned 'null' + number 
    '''
    recordID_set = set()
    imprintedID_set = set()

    #check to see if any recordID or imprintedID is repeated
    for ballot in cvrList:
        unique = True 
        if ballot[3] in recordID_set:
            ballot[3] = 'nullRecordID'+str(addedBallots)
            unique = False
        if ballot[4] in imprintedID_set:
            ballot[4] = 'nullImprintedID'+str(addedBallots)
            unique = False 
        if not unique:
            addedBallots += 1
        recordID_set.add(ballot[3])
        imprintedID_set.add(ballot[4])
    
    return addedBallots
        

def uniqueCVR(cvr_file):
    '''
    Check that each ballot in batch has unique recordID, imprintedID 
    '''
    with open(cvr_file, mode = 'r', newline = '') as readCVR:
        cvrReader = csv.reader(readCVR)
        #skip headers
        for i in range(4):
            next(cvrReader)

        recordID_list = []
        recordID_set = set()
        imprintedID_list = []
        imprintedID_set = set()

        #add each ballot's recordID and imprintedID to respective list, set 
        for ballot in cvrReader:
            recordID_list.append(ballot[3])
            recordID_set.add(ballot[3])
            imprintedID_list.append(ballot[4])
            imprintedID_set.add(ballot[4])

        #list containing repeats would be longer than set 
        if len(recordID_list) != len(recordID_set) or len(imprintedID_list) != len(imprintedID_set):
            return False 

    return True     

def getManInfo(manifest_file, batch_name):
    '''
    Returns number of ballots in specified batch from manifest  
    '''
    #open file, skip header
    with open(manifest_file, mode = 'r', newline = '') as readManifest:
        manifest_reader = csv.reader(readManifest)
        next(manifest_reader)

        for ballot in manifest_reader: 
            if ballot[2] == batch_name:
                numBallots = int(ballot[3])
                return numBallots
        
def getTabInfo(tabulation_file, batch_name, info_needed):
    '''
    Returns number of ballots total, winner, or loser in specified batch from tabulation  
    '''
    #open file, skip header
    with open(tabulation_file, mode = 'r', newline = '') as readTabulation:
        tabulation_reader = csv.reader(readTabulation)
        next(tabulation_reader)

        if info_needed == 'batch size':
            for ballot in tabulation_reader: 
                if ballot[1] == batch_name:
                    numBallotsTotal = int(ballot[2])
                    return numBallotsTotal

        if info_needed == 'winner size':
            for ballot in tabulation_reader: 
                if ballot[1] == batch_name:
                    numBallotsWinner = int(ballot[3])
                    return numBallotsWinner

        if info_needed == 'runnerup size':
            for ballot in tabulation_reader: 
                if ballot[1] == batch_name:
                    numBallotsRunnerup = int(ballot[4])
                    return numBallotsRunnerup


def tests(jsonFile):
    '''
    Control setup/audit/simulation from terminal 
    '''
    #call readInput (needed for any audit/simulation run)
    numBallots, overvotes1, undervotes1, overvotes2, undervotes2, riskLimit, num, margins, gamma = readInput()
    
    print('Select using number: \n 1) set up election \n 2) audit election \n 3) set up and audit election \n 4) run simulation')
    input1 = input()
    if input1 == '1':
        electionSetup(numBallots, margins, overvotes1, undervotes1, overvotes2, undervotes2, riskLimit, gamma, jsonFile)
    elif input1 == '2':
        electionAudit()
    elif input1 == '3':
        electionSetup(numBallots, margins, overvotes1, undervotes1, overvotes2, undervotes2, riskLimit, gamma, jsonFile)
        electionAudit()
    elif input1 == '4':
        collectData(jsonFile, numBallots, overvotes1, undervotes1, overvotes2, undervotes2, riskLimit, num, margins, gamma)
    else: 
        print('Invalid input. Try again.')

def electionSetup(numBallots, margins, overvotes1, undervotes1, overvotes2, undervotes2, riskLimit, gamma, jsonFile):
    '''
    Set up files for audit 
    '''
    #set margin manually 
    margin = 5
    print('Election setup:')
    #create election object to base files on 
    E1 = Election(numBallots, margin, overvotes1, undervotes1, overvotes2, undervotes2, riskLimit, gamma, jsonFile)
    #call _createCVR1, _createCVR2 to write cvr1, cvr2, manifest, tabulation files 
    E1._createCVR1()
    E1._createCVR2(overvotes1, undervotes1, overvotes2, undervotes2)

def removeWorkingDir():
    #remove files from previous run if dir exists 
    path =  'lazy_rla_cvr/'
    isdir = os.path.isdir(path) 
    if isdir:
        rmtree(path)

def electionAudit():
    '''
    Audit election
    '''
    print('Election audit:')

    removeWorkingDir()
    #manifest, tabulation and seed will be given by user on Michael's end
    seed1 = 2368607141
    tabulation_file = str(os.path.join(sys.path[0], 'electionTabulation.csv'))
    manifest_file = str(os.path.join(sys.path[0], 'electionManifest.csv'))
    selectedBatches = batchSelect(manifest_file, tabulation_file, seed1)
    #returns a dictionary: 
    #'batchesToAudit': set of batches that need CVR, 'ballotsPerBatch': dict w num ballots per batch to audit, 
    # 'ballotsPerBatchTotal': dict w num ballots per batch total 
    
    #in a normal election this would not be needed as the CVRs would come from user 
    lazyCVR_files = lazyCVR_gen(selectedBatches['batchesToAudit'])
    #returns set of CVR filenames to pull batches from 

    #function to make sure all requested files are present
    fileMissing, missingFiles = checkInputFiles(selectedBatches['batchesToAudit'], lazyCVR_files)
    if fileMissing: 
        #if any files missing/incorrectly named, print message, then stop audit 
        print('The following files are missing or incorrectly named. Please fix, then start audit again.')
        for i in missingFiles: 
            print(i)
        return 

    seed2 = 9113645654
    #seed should actually be generated by user in a real invocation, this is just test code
    auditCVR_blank = ballotSelect(lazyCVR_files, selectedBatches['ballotsPerBatchAudit'], selectedBatches['ballotsPerBatchTotal'], seed2)
    #auditCVR_blank is list of files for user to enter manual vote interpretations into 

    auditCVR_check = ballotSelect_check(lazyCVR_files, selectedBatches['ballotsPerBatchAudit'], selectedBatches['ballotsPerBatchTotal'], seed2)
    #auditCVR_check is list of files with correct 'manual interpretations' filled out 
    #this step not needed if user inputs own files 
    
    #this is needed to pause audit halfway to alter files if desired 
    #for example, to test forceConsistent
    #if files are coming from user (not generated by program), comment this out
    pause = input('If desired, make changes to files now. \nThen press ENTER to continue. ')

    #give manual interpretations, set of CVR files, tabulation and manifest 
    riskLevel = calculateRisk(auditCVR_check, lazyCVR_files, tabulation_file, manifest_file)
    #get back risk level 

    print('risk level: ' + str(riskLevel))

def checkInputFiles(filesRequested, filesReceived):
    '''
    Check that all requested files are received
    '''
    missingFiles = []
    fileMissing = False

    for cvr in filesRequested: 
        #filename = expected name of CVR file 
        filename = str(os.path.join(sys.path[0], 'lazy_rla_cvr', cvr + 'CVR.csv'))
        if filename not in filesReceived:
            missingFiles.append(cvr)
            fileMissing = True 

    return fileMissing, missingFiles

