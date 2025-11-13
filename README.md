# 5g-backhaul-energy-optimization
This research project implements an intelligent energy management system for 5G backhaul networks using Software-Defined Networking (SDN) and Machine Learning. 

## Abstract
The evolution of fifth-generation (5G) networks has substantially increased traffic demands on backhaul infrastructures, emphasizing the need for intelligent and energy-efficient management strategies. This work presents an SDN-based energy optimization framework that integrates time-series traffic prediction and topology reconfiguration to reduce power consumption in 5G backhaul networks. Using an LSTM model, link-level traffic is forecasted for successive time intervals, enabling the identification of underutilized connections. The Mininet–Ryu simulation environment is then employed to emulate the backhaul topology and evaluate performance metrics such as latency, throughput, and energy consumption under different link activation scenarios. Experimental results demonstrate that proactive, prediction-driven link management can achieve significant energy savings while maintaining acceptable Quality of Service.

## File Structure

Here is an explanation of the repository file structure:
'''
├── Data CSVs --> Contain all the CSV data related to ML Model Training, Predictions etc
│
├── Images --> Contains all the final results + output images including topology visualizations
│
├── Simulation Files --> Contains files to test and validate the traffic data in a mininet-emulated environment
│
├── checkpoints --> Contains the trained LSTM model
│
├── energy_manager.py --> 
│
├── lstm.ipynb --> The Jupyter Notebook used to design, train, and validate the LSTM model.
│
├── ml_predictor_service.py --> Intermediates the service of sending the next hour ML model predictions to 'energy_manager.py'
│
├── ryu_controller.py --> SDN Controller for the mininet-emulated topology
│
├── synthetic_train_data_generator.py --> Generates synthetic 5G traffic data to train our LSTM Model
│
├── topology.py --> Creates a close-to-real-life 5G backhaul structure in Mininet
│
└── visualize_topo.py --> Code to generate topology visualization images.
'''

## How to Replicate This Project

### Requirements

- Environment: A Linux environment is recommended (e.g., 'Ubuntu').
- 'Mininet': Recommended Version 2.3.0
- 'Ryu': Version 4.34 (or any 4.x version).
- 'OpenFlow': The controllers use OpenFlow 1.3.
- Python Libraries: All Python code is written for Python 3.8+.
'''
pip install ryu pandas networkx matplotlib scikit-learn tensorflow flask requests
'''

### Important Setup

File Location: All .py scripts and .csv files must be in the same root directory. 
Permissions: You will need sudo access to run Mininet.

### Project Workflow

Phase 1: This phase runs your decoupled 4-terminal system to generate your energy-saving metrics and the "Sleep Plan" for Phase 2.

In terminal 1, start the SDN RYU controller:
'''
ryu-manager ryu_controller.py
'''

In terminal 2, start by creating the topology on mininet:
'''
sudo python3 topology.py
'''

In terminal 3 start the ml_predictor_service file so as to receive the next hour ML predictions:
'''
sudo python3 ml_predictor_service.py
'''

Finally, in terminal 4 start the energy_manager:
'''
sudo python3 energy_manager.py
'''

At the end of this phase, you have your Energy Saved metrics from energy_metrics.csv and your 24-hour "Sleep Plan" from the logs. We can calculate the predicted energy utilization and % energy saved using this data.

Phase 2: Now we emulate the decisions from Phase 1 to measure their real-world impact on throughput and latency.

In terminal 1, start by running the SDN RYU controller:
'''
ryu-manager ryu.py
'''

In terminal 2, start the traffic simulation by running the run_simulation file, which creates a Mininet topology and calculates metrics like end-to-end throughput and average system latency:
'''
sudo python3 run_simulation.py
'''

Stop both processes (Ctrl+C) and run sudo mn -c.

## Conclusion
This project presented a simulation-based framework for reducing energy consumption in a 5G backhaul network using SDN and machine learning. By combining Mininet emulation, the Ryu controller, and an LSTM-based traffic prediction model, the system predicts per-link utilization and selectively puts underutilized links into sleep mode while maintaining throughput and connectivity. The results indicate that intelligent link management can significantly reduce network energy usage without major impact on latency or packet delivery, demonstrating the potential of predictive control in energy-aware network design.
