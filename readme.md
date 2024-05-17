**This is a forked version of [Adaptive Risk Limiting Audits](https://arxiv.org/pdf/2202.02607) and [Adaptive-RLA-Tools](https://github.com/aeharrison815/Adaptive-RLA-Tools).**


## Introduction
**Questionable Simulation Tools** provides the function to simulate an adaptive risk-limiting audit containing ballots with marginal or ambiguous marks. In the simulation, we consider and simulate the case where the probability the CVR (namely p_cvr) reports marginal ballots as votes for the winner, and the probability that the auditor(p_a) reports marginally marked ballots as votes for the winner differ. 

Here, we run this case with a margin of 1%. We run through probabilities of 0 to 100% in 10% increments for the value of p_cvr, and test auditor rates, p_a, of 20% and 40% lower and higher than current value of p_cvr. In each case, we calculate discrepancy accordingly and output the number of ballots needed for the Kaplan Markov comparison audit with the corresponding auditor and cvr probability pair. 

## Installation

This section provides instructions on how to run the Quetionable Simulation. 

First, install the necessary packages:

	python3 -m pip install numpy==1.20.3

## How to Run Simulation
### Prepare Necessary Files

First ensure that the necessary files are within the same directory as the primary simulation files. The files are as follows:
1) `2020_CT_Election_Data.json`
2) `Election_Simulation.py`
3) `adaptive_backend.py`
4) `election_files.py`

Primary Simulation Files:
1) `Questionable_Simulation.py`
2) `Questionable_Input.txt`

### Run simulation

Run `Questionable_Simulation.py`. This file requires the files mentioned above. In order to change any paramaters, such as the number of ballots, the risk limit, number of overvotes, undervotes, etc, refer to the `Questionable_Input.txt` file, and make necessary modifications there. The `Questionable_Simulation.py` file prints, by default, the 95th percentile of ballots needed to sample for each CVR and auditor probability pair (pair of values for p_cvr and p_a). Moreover, it outputs a single csv file called `Adaptive_CVR_Data2.csv` that provides the average number of ballots needed. By default, ballot polling is disabled. 

