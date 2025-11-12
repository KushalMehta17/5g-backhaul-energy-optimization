"""
ENERGY MANAGER - (The "Brain" Service)

This is a standalone Python script, NOT a Ryu app.
It runs your entire simulation and produces clean logs.

Its job:
1. Poll the LSTM service (port 5000) for predictions.
2. Poll our Ryu controller (port 8080) for the topology map.
3. Run the simulation, safety checks, and metric calculations.
4. Print CLEAN logs and export the final CSV.
"""
import requests
import networkx as nx
import time
import csv
import logging
import sys
from collections import OrderedDict

# --- Helper for clean logging ---
def setup_logger():
    logger = logging.getLogger("EnergyManager")
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

class EnergyManager:
    
    def __init__(self, logger):
        self.logger = logger
        self.switch_graph = nx.Graph()
        self.link_states = {}
        self.link_index_to_edge = OrderedDict()
        self.link_bandwidths = {}
        self.sleep_threshold = 0.10

        self.metrics = {
            'hourly_energy': [],
            'active_links_history': [],
            'timestamp': []
        }
        
        self.lstm_api_url = 'http://localhost:5000/predictions/next_hour'
        self.ryu_api_url = 'http://localhost:8080/topology'

    def get_topology_from_ryu(self):
        """Polls the Ryu controller for the hardcoded link map."""
        self.logger.info(f"Attempting to fetch topology from {self.ryu_api_url}...")
        while True:
            try:
                response = requests.get(self.ryu_api_url, timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    # Handle the JSON response structure
                    topology_data = data.get('topology', {})
                    
                    for link_id, link_tuple in topology_data.items():
                        # link_tuple is (dpid_a, port_a, hw_a, dpid_b, port_b, hw_b)
                        self.link_index_to_edge[link_id] = tuple(link_tuple)
                    
                    # Initialize link states and switch graph
                    for link_id, (dpid_a, _, _, dpid_b, _, _) in self.link_index_to_edge.items():
                        self.link_states[link_id] = {'active': True, 'utilization': 0.0}
                        if dpid_a > 0 and dpid_b > 0: # Is a switch-to-switch link
                            self.switch_graph.add_edge(int(dpid_a), int(dpid_b), link_id=link_id)
                    
                    self.logger.info(f"✅ Got topology with {len(self.link_index_to_edge)} links.")
                    return True
            except requests.exceptions.RequestException as e:
                self.logger.debug(f"Ryu API not ready ({e}). Retrying in 5s...")
                time.sleep(5)

    def run_simulation(self):
        """Main simulation loop"""
        
        # 1. Get topology map (runs once)
        self.get_topology_from_ryu()
        
        # 2. Build bandwidth map (runs once)
        self._build_bandwidths()
        
        # 3. Start the main simulation loop
        hour = 0
        while True:
            self.logger.info(f"--- Starting Simulated Hour {hour} ---")
            
            # 3a. Get predictions
            predictions = self._get_predictions()
            if predictions:
                self._update_predictions(predictions)
            
            # 3b. Run sleep/wake logic
            self._link_management()
            
            # 3c. Calculate and log metrics
            self._metrics_collector(hour)
            
            # 3d. Export periodically
            if hour > 0 and hour % 6 == 0:
                self.export_metrics()
                
            hour += 1
            time.sleep(10) # 10 seconds = 1 "hour"
            
    # --- All logic below is COPIED from your working controller ---

    def _get_predictions(self):
        """Polls the LSTM service for predictions."""
        try:
            response = requests.get(self.lstm_api_url, timeout=2)
            if response.status_code == 200:
                predictions = response.json().get('predictions', [])
                self.logger.info(f"✅ Received {len(predictions)} predictions from LSTM")
                return predictions
            else:
                self.logger.warning(f"LSTM service returned status {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"LSTM service unavailable: {e}")
        return []

    def _update_predictions(self, predictions):
        updated_count = 0
        for pred in predictions:
            link_id = pred.get('link_id')
            if link_id in self.link_states:
                raw_util = pred.get('bandwidth_utilization (ratio)', 0.0)
                self.link_states[link_id]['utilization'] = float(raw_util)
                updated_count += 1
        self.logger.info(f"✅ Updated {updated_count} link states from predictions")

    def _link_management(self):
        self.logger.info("--- Running Link Management ---")
        all_link_ids = list(self.link_states.keys())
        
        active_links = []
        sleeping_links = []
        
        for link_id in all_link_ids:
            state = self.link_states.get(link_id)
            if not state: continue
            
            util = state['utilization']

            if not state['active'] and util >= self.sleep_threshold:
                self._set_link_state(link_id, True)
            elif state['active'] and util < self.sleep_threshold:
                if self._is_safe_to_sleep(link_id):
                    self._set_link_state(link_id, False)

            # Build summary lists
            if self.link_states[link_id]['active']:
                active_links.append(link_id)
            else:
                sleeping_links.append(link_id)
        
        self.logger.info(f"--- Link Status Summary ---")
        self.logger.info(f">> ACTIVE ({len(active_links)}): {active_links}")
        self.logger.info(f">> SLEEPING ({len(sleeping_links)}): {sleeping_links}")

    def _is_safe_to_sleep(self, link_id):
        if link_id not in self.link_index_to_edge:
            return False
            
        dpid_a, _, _, dpid_b, _, _ = self.link_index_to_edge[link_id]
        
        # 1. Host link safety check
        if dpid_b < 0:
            return self._is_safe_to_sleep_host_link(link_id, -dpid_b)
        
        # 2. Core-Core link safety 
        if link_id in ['link_37', 'link_38', 'link_39']:
            return True
        
        # 3. Aggregation-Core link safety
        if 25 <= int(link_id.split('_')[1]) <= 36:
            return self._is_safe_to_sleep_aggregation_core_link(link_id)
        
        return False
        
        return nx.is_connected(temp_graph)

    def _is_safe_to_sleep_host_link(self, link_id, host_id):
        host_name = f'h{host_id}'
        host_to_links = {
            'h1': ['link_1', 'link_2'], 'h2': ['link_3', 'link_4'], 
            'h3': ['link_5', 'link_6'], 'h4': ['link_7', 'link_8'],
            'h5': ['link_9', 'link_10'], 'h6': ['link_11', 'link_12'],
            'h7': ['link_13', 'link_14'], 'h8': ['link_15', 'link_16'],
            'h9': ['link_17', 'link_18'], 'h10': ['link_19', 'link_20'],
            'h11': ['link_21', 'link_22'], 'h12': ['link_23', 'link_24'],
        }
        
        if host_name not in host_to_links: return False
        host_links = host_to_links[host_name]
        if link_id not in host_links: return False
        
        for other_link in host_links:
            if other_link != link_id and self.link_states[other_link]['active']:
                return True
        return False
    
    def _is_safe_to_sleep_aggregation_core_link(self, link_id):
        """Ensure each aggregation switch has at least one active core link"""
        agg_switch_to_core_links = {
            4: ['link_25', 'link_26'],  # agg4 to core1, core2
            5: ['link_27', 'link_28'],  # agg5 to core1, core3  
            6: ['link_29', 'link_30'],  # agg6 to core2, core3
            7: ['link_31', 'link_32'],  # agg7 to core1, core2
            8: ['link_33', 'link_34'],  # agg8 to core1, core3
            9: ['link_35', 'link_36']   # agg9 to core2, core3
        }
        
        # Find which aggregation switch this link belongs to
        for agg_switch, links in agg_switch_to_core_links.items():
            if link_id in links:
                # Check if any other core link for this agg switch is active
                for other_link in links:
                    if other_link != link_id and self.link_states[other_link]['active']:
                        return True
                return False
        return True

    def _set_link_state(self, link_id, up):
        if link_id not in self.link_states:
            return False
            
        old_state = self.link_states[link_id]['active']
        self.link_states[link_id]['active'] = up
        
        if old_state != up:
            self.logger.info("%s: %s (util: %.1f%%)", 
                             "WOKE" if up else "SLEPT", 
                             link_id, 
                             self.link_states[link_id]['utilization'] * 100)
        return True
    
    def _metrics_collector(self, hour):
        energy, active_links, sleeping_links = self.calculate_energy_consumption()
        
        self.metrics['hourly_energy'].append(energy)
        self.metrics['active_links_history'].append(active_links)
        self.metrics['timestamp'].append(hour)
        
        self.log_metrics(hour)

    def calculate_energy_consumption(self):
        total_energy = 0
        active_links = 0
        sleeping_links = 0
        for link_id, state in self.link_states.items():
            if state['active']:
                total_energy += 100
                active_links += 1
            else:
                total_energy += 10
                sleeping_links += 1
        return total_energy, active_links, sleeping_links
        
    def _build_bandwidths(self):
        for i in range(1, 25): self.link_bandwidths[f'link_{i}'] = 5
        for i in range(25, 37): self.link_bandwidths[f'link_{i}'] = 20
        # --- FIX: Your numbering was 25-36 (core-agg) and 37-39 (core-core) ---
        for i in range(37, 40): self.link_bandwidths[f'link_{i}'] = 50

    def log_metrics(self, hour):
        energy = self.metrics['hourly_energy'][-1]
        active_links = self.metrics['active_links_history'][-1]
        
        self.logger.info(f"""\n
    HOUR {hour} METRICS:
    Energy: {energy}W
    >> Active Links: {active_links}/39
    >> Sleeping Links: {39 - active_links}/39
    \n""")

    def export_metrics(self):
        try:
            with open('energy_metrics.csv', 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Hour', 'Energy_W', 'Active_Links'])
                for i in range(len(self.metrics['timestamp'])):
                    writer.writerow([
                        self.metrics['timestamp'][i],
                        self.metrics['hourly_energy'][i],
                        self.metrics['active_links_history'][i]
                    ])
            self.logger.info("*** Metrics exported to energy_metrics.csv")
        except Exception as e:
            self.logger.error(f"Export failed: {e}")

# --- Main entry point ---
if __name__ == '__main__':
    logger = setup_logger()
    try:
        manager = EnergyManager(logger)
        manager.run_simulation()
    except KeyboardInterrupt:
        logger.info("\nSimulation stopped by user. Exporting final metrics...")
        manager.export_metrics()
    except Exception as e:
        logger.error(f"FATAL ERROR: {e}")