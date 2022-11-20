## Introduction

**Adapative RLA Tools** provides multiple functions to simulate an adaptive risk-limiting audit, as detailed in [Adaptive Risk-Limiting Ballot Comparison Audits](https://arxiv.org/abs/2202.02607). There are four main options for this tool: 
1) Set up an election audit. This uses the name of a town, number of voters, and number of polling places in a town to create sample files used in an adaptive RLA comparison audit. It outputs two sets of CVR files (one 'trusted' and one 'untrusted'), a ballot manifest, and ballot tabulation in csv format. 
2) Audit election. This uses either the files from option 1) or user-inputted files to conduct a adaptive RLA comparison audit. It chooses a number of ballots to audit (using [Kaplan-Markov expected sample sizes](https://ucb-stat-159-s21.github.io/site/Notes/audit.html)), creates mock CVR files for each batch that a ballot is chosen from, and outputs the calculated risk limit based on the discrepancies found in the files. 
3) Set up and audit election. Runs option 1) and 2) detailed above.
4) Run simulation. This simulates both an election and an incremental ballot comparison audit. It creates a user-inputted number of ballots, distributes them to towns, then runs a ballot comparison audit and collects the data on a town level. It averages and outpus the data in a single csv file. This data is used for the efficiency argument of the adaptive RLA comparison audit. 

This tool also provides a Jupyter notebook to act as a frontend for option 3), called `adaptive_notebook.ipynb`. 

Additonally, there is a separate Jupyter notebook to run a ballot polling audit. The only way to run this ballot polling audit is through the Jupyter notebook, called `polling_notebook.ipynb`.

## Installation

This section provides instructions on how to run the python version of Adapative RLA Tools. To see how to set up a working Jupyter notebook, look at the following section.

First, install the necessary packages:

	python3 -m pip install numpy==1.20.3

### Jupyter Notebook

To install the Jupyter Notebook package in python, use this command:

	python3 -m pip install notebook

## How to Use
### Set up an election audit

Run `Election_Simulation.py` and select option 1. This function requires `Simulation_Input.txt` and `2020_CT_Election_Data.json` in order to distribute the votes and errors on ballots and distribute ballots to different towns. It also requires `election_files.py` to output two CVRs: one with overstatement and understatement errors, and one "correct" CVR that follows the data from `Simulation_Input.txt`. It also outputs a "correct" ballot manifest and error-prone tabulation totals.

### Audit election

Run `Election_Simulation.py` and select option 2. This function requires either the files generated from *Set up an election* (in which case, select option 3) or manually created files. It outputs a calculated risk limit based on the discrepancy found between the "correct" batch CVRs and batch CVRs with overstatement and understatement errors. There is also functionality to correct files as detailed in the *Transform* function of [Adaptive Risk-Limiting Ballot Comparison Audits](https://arxiv.org/abs/2202.02607). 

### Run simulation

Run `Election_Simulation.py` and select option 4. This function requires `Simulation_Input.txt` and `2020_CT_Election_Data.json` in order to distribute the votes and errors on ballots and distribute ballots to different towns. It outputs a single csv file called `Adaptive_CVR_Data.csv` that provides the average results per town for the simulation. By default, ballot polling is disabled. 

### Jupyter Notebook for Adaptive Risk-Limiting Audits

To run the Jupyter notebook, use the command:
	
	python3 -m notebook

and select `adaptive_notebook.ipnyb` from the file list. It requires both `Election_Simulation.py`, `adaptive_backend.py`, and `election_files.py` in order to run. It will both setup and audit and election, so it requires all the files from "Set up an election audit." We also provide a mybinder, which can be found [here](insert link).

To conduct a adaptive risk-limiting audit with your own files, run code block 1, but do not run code block 2. Ensure you have files titled `electionManifest.csv` and `electionTabulation.csv` in the proper directory and that they follow the correct format; we have included sample files in the `sample_files` folder to show the proper format for the necessary files. Run code block 3, then upload your CVRs in the `adaptive_rla_cvr` folder in the proper directory. Ensure the CVRs are titled `batchnameCVR.csv` and that they follow the correct format; once again consult `sample_files` if necessary. Then run code block 4 to choose a ballot sample. Do not run code block 5, then run code block 6 to receive blank CVR files where you will fill out your interpretation of the sampled ballots. Once you have filled out your interpretations, run code blocks 7. In code block 8, change the flag to 1, then run code block 9. The audit will then determine if another round is necessary; if so, it will select another sample, and generate blanks CVRs for your interpretations. 

### Jupyter Notebook for Ballot Polling Audits

To run the Jupyter notebook, use the command:
	
	python3 -m notebook

and select `polling_notebook.ipnyb` from the file list. It requires `Election_Simulation.py`, `polling_backend.py`, and `election_files.py` in order to run. It will create the necessary files for a ballot pulling audit and create ballot pull lists for each batch using the information from these files (in the folder `ballot_polling_pull_list`). It will then ask for the number of votes for the winner and for the runner-up that was observed in the sampled ballots. After that, it will determine if more auditing is necessary and repeat the steps needed to do another round. If the risk limit is met, it will output the observed risk limit. We also provide a mybinder, which can be found here (insert link).

To conduct your own ballot polling audit, ensure you have files titled `electionManifest.csv` and `electionTabulation.csv` in the proper directory and that they follow the correct format. We have included sample files in the `sample_files` folder to show the proper format for the necessary files. Run code block 1, but do not run code block 2. Run the remaining code blocks, then look at the `ballot_polling_pull_list` folder for csv files for each batch. They show the ballots to examine and audit in the batch. Once you have audited all the selected ballots, enter the observed number of votes for the winner and runner-up. The audit will then determine if another round is necessary; if so, look at the `ballot_polling_pull_list` folder once again for the ballots to audit per batch and enter the observed votes.
