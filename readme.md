## Introduction

**Lazy RLA Tools** provides multiple functions to simulate a lazy risk-limiting audit, as detailed in [Lazy Risk-Limiting Ballot Comparison Audits](https://arxiv.org/abs/2202.02607). There are four main options for this tool: 
1) Set up an election audit. This uses the name of a town, number of voters, and number of polling places in a town to create sample files used in a lazy RLA comparison audit. It outputs two sets of CVR files (one 'trusted' and one 'untrusted'), a ballot manifest, and ballot tabulation in csv format. 
2) Audit election. This uses either the files from option 1) or user-inputted files to conduct a lazy RLA comparison audit. It chooses a number of ballots to audit (using [Kaplan-Markov expected sample sizes](https://ucb-stat-159-s21.github.io/site/Notes/audit.html)), creates mock CVR files for each batch that a ballot is chosen from, and outputs the calculated risk limit based on the discrepancies found in the files. 
3) Set up and audit election. Runs option 1) and 2) detailed above.
4) Run simulation. This simulates both an election and an incremental ballot comparison audit. It creates a user-inputted number of ballots, distributes them to towns, then runs a ballot comparison audit and collects the data on a town level. It averages and outpus the data in a single csv file. This data is used for the efficiency argument of the lazy RLA comparison audit. 

This tool also provides a Jupyter notebook to act as a frontend for option 3). 

## Installation

This section provides instructions on how to run the python version of Lazy RLA Tools. To see how to set up a working Jupyter notebook, look at the following section.

First, install the necessary packages:

	python3 -m pip install numpy==1.20.3

### Jupyter Notebook

To install the Jupyter Notebook package in python, use this command:

	python3 -m pip install notebook

## How to Use
### Set up an election audit

Run `Election_Simulation.py` and select option 1. This function requires `Simulation_Input.txt` and `2020_CT_Election_Data.json` in order to distribute the votes and errors on ballots and distribute ballots to different towns. It outputs two CVRs: one with overstatement and understatement errors, and one "correct" CVR that follows the data from `Simulation_Input.txt`. It also outputs a "correct" ballot manifest and error-prone tabulation totals.

### Audit election

Run `Election_Simulation.py` and select option 2. This function requires either the files generated from *Set up an election* (in which case, select option 3) or manually created files. It outputs a calculated risk limit based on the discrepancy found between the "correct" batch CVRs and batch CVRs with overstatement and understatement errors. There is also functionality to correct files as detailed in the *Transform* function of [Lazy Risk-Limiting Ballot Comparison Audits](https://arxiv.org/abs/2202.02607). 

### Run simulation

Run `Election_Simulation.py` and select option 4. This function requires `Simulation_Input.txt` and `2020_CT_Election_Data.json` in order to distribute the votes and errors on ballots and distribute ballots to different towns. It outputs a single csv file called `Lazy_CVR_Data.csv` that provides the average results per town for the simulation. By default, ballot polling is disabled. 

### Jupyter Notebook

To run the Jupyter notebook, use the command:
	
	python3 -m notebook

and select `frontend_prototype.ipnyb` from the file list. It requires both `Election_Simulation.py` and `lazy_backend.py` in order to run. It will both setup and audit and election, so it requires all the files from "Set up an election audit." We also have a mybinder, which turns Git repos into interactable environments. It can be found [here](https://mybinder.org/v2/git/https%3A%2F%2Fgithub.com%2Faeharrison815%2FLazy-RLA-Too[…]3e34a8c3a35a0989?urlpath=lab%2Ftree%2Ffrontend_prototype.ipynb).
