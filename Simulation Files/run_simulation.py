import csv
import time
import re  
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.log import setLogLevel, info
from mininet.clean import cleanup
from backhaul_topo import BackhaulTopo 

# --- Configuration ---
HOUR_TO_SIMULATE = 0     # Which hour (row) to read from the CSV 
SIMULATION_TIME_SEC = 10 # How long to run traffic
TRAFFIC_CSV = 'hourly_traffic.csv' 
SERVER_LOG = '/tmp/iperf_server.csv' 

def get_traffic_for_hour(hour_index):
    """Reads a specific row from the traffic CSV."""
    try:
        with open(TRAFFIC_CSV) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i == hour_index:
                    rates_kbps = []
                    for h in range(1, 13):
                        # Get rate from CSV (as kbps)
                        rate = float(row.get(f"h{h}", 100) or 100)
                        rates_kbps.append(rate)
                    info(f"Loaded traffic for Hour {hour_index} (kbps): {rates_kbps}\n")
                    return rates_kbps, row.get('time_slot', hour_index)
            info(f"Could not find Hour {hour_index} in CSV.\n")
            return None, None
    except Exception as e:
        info(f"Error reading {TRAFFIC_CSV}: {e}\n")
        return None, None

def calculate_system_throughput_iperf(h_core):
    """
    Calculate system throughput using iperf server CSV output.
    """
    try:
        csv_content = h_core.cmd(f'cat {SERVER_LOG}')
        total_throughput_mbps = 0.0
        flow_count = 0
        
        for line in csv_content.strip().split('\n'):
            if line and not line.startswith('#'):
                parts = line.split(',')
                if len(parts) >= 9:
                    try:
                        interval = parts[6]
                        if '-' not in interval or float(interval.split('-')[0]) != 0.0:
                            continue
                            
                        bits_per_second = float(parts[8])
                        throughput_mbps = bits_per_second / 1e6 # Convert bps to Mbps
                        
                        if throughput_mbps > 0:
                            total_throughput_mbps += throughput_mbps
                            flow_count += 1
                    except (ValueError, IndexError):
                        continue
        
        if flow_count > 0:
            info(f"*** Total throughput of the Network: {total_throughput_mbps:.2f} Mbps\n")
            return total_throughput_mbps
        else:
            info("*** No valid iperf summary lines found in log.\n")
            info(f"Log content:\n{csv_content}\n")
            return 0.0
            
    except Exception as e:
        info(f"*** Error calculating throughput with iperf CSV: {e}\n")
        return 0.0

def run_single_simulation():
    setLogLevel('info')

    # --- Setup network and controller ---
    info('*** Setting up network topology\n')
    topo = BackhaulTopo()
    net = Mininet(topo=topo, controller=None)

    controller_ip = '127.0.0.1'
    c0 = net.addController('c0', controller=RemoteController, ip=controller_ip, port=6633) 

    net.start()
    info('*** Waiting for Network to Initialize...\n')
    time.sleep(33) 

    # --- Hosts ---
    hlist = [net.get(f"h{i}") for i in range(1, 13)]
    h_core = net.get('h_core')

    # --- Get Traffic Rates ---
    rates_kbps, slot = get_traffic_for_hour(HOUR_TO_SIMULATE)
    if not rates_kbps:
        info("No traffic rates found. Stopping.\n")
        net.stop()
        return

    # --- MEASURE LATENCY ---
    info("*** Measuring latency\n")
    latency_results = []
    total_rtt = 0
    successful_pings = 0
    for i, host in enumerate(hlist, 1):
        result = host.cmd(f'ping -c 3 -i 0.5 -W 1 {h_core.IP()} 2>/dev/null')
        for line in result.split('\n'):
            if 'min/avg/max' in line:
                parts = line.split('=')[1].split('/')
                avg_latency = float(parts[1])
                latency_results.append(avg_latency)
                total_rtt += avg_latency
                successful_pings += 1
                info(f"  h{i} -> h_core: {avg_latency:.2f} ms\n")
                break
        else:
            info(f"  h{i} -> h_core: ✗ Failed\n")
    
    avg_latency = total_rtt / successful_pings if successful_pings > 0 else 0

    # --- Start iperf server on core host ---
    h_core.cmd('pkill iperf 2>/dev/null')
    h_core.cmd(f'iperf -s -u -y C > {SERVER_LOG} 2>&1 &')
    time.sleep(1)

    # --- Start iperf flows from all base stations to core ---
    info(f"*** Starting simultaneous traffic for {SIMULATION_TIME_SEC} seconds\n")
    total_requested_kbps = 0
    for i, rate in enumerate(rates_kbps, start=1):
        src = hlist[i - 1]
        
        cmd = f"iperf -u -c {h_core.IP()} -b {rate}K -t {SIMULATION_TIME_SEC} &"
        
        info(f"  h{i} -> h_core : {rate} kbps\n")
        src.cmd(cmd)
        total_requested_kbps += rate

    total_requested_mbps = total_requested_kbps / 1000.0
    info(f"*** Waiting for traffic to complete... ***\n")
    time.sleep(SIMULATION_TIME_SEC + 3) # Wait for simulation + 3s buffer

    # --- Stop iperf and calculate throughput ---
    info("*** Calculating system throughput\n")
    h_core.cmd('pkill iperf 2>/dev/null')
    time.sleep(1) 
    
    system_throughput_mbps = calculate_system_throughput_iperf(h_core)

    # --- Log results ---
    info(f"\n" + "="*40)
    info(f"\n=== SIMULATION RESULTS ===")
    info(f"\n  MEASURED System Throughput: {system_throughput_mbps:.2f} Mbps")
    info(f"\n  Average Latency: {avg_latency:.2f} ms")
    info(f"\n  Successful Pings: {successful_pings}/12 \n")
    info("="*40 + "\n\n")

    info('*** Simulation finished. Stopping network.\n')
    net.stop()

if __name__ == '__main__':
    run_single_simulation()