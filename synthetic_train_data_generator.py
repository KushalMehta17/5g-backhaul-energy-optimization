import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_topology_aware_traffic(num_days=120):
    """
    Generate topology-aware traffic data for 39 links with bandwidth utilization
    """
    # Define topology mapping with capacities
    topology = {
        'hosts': {
            'h1': {'type': 'business', 'access_links': ['link_1', 'link_2'], 'aggregation': 's4'},
            'h2': {'type': 'residential', 'access_links': ['link_3', 'link_4'], 'aggregation': 's4'},
            'h3': {'type': 'business', 'access_links': ['link_5', 'link_6'], 'aggregation': 's5'},
            'h4': {'type': 'residential', 'access_links': ['link_7', 'link_8'], 'aggregation': 's5'},
            'h5': {'type': 'business', 'access_links': ['link_9', 'link_10'], 'aggregation': 's6'},
            'h6': {'type': 'residential', 'access_links': ['link_11', 'link_12'], 'aggregation': 's6'},
            'h7': {'type': 'business', 'access_links': ['link_13', 'link_14'], 'aggregation': 's7'},
            'h8': {'type': 'residential', 'access_links': ['link_15', 'link_16'], 'aggregation': 's7'},
            'h9': {'type': 'business', 'access_links': ['link_17', 'link_18'], 'aggregation': 's8'},
            'h10': {'type': 'residential', 'access_links': ['link_19', 'link_20'], 'aggregation': 's8'},
            'h11': {'type': 'business', 'access_links': ['link_21', 'link_22'], 'aggregation': 's9'},
            'h12': {'type': 'residential', 'access_links': ['link_23', 'link_24'], 'aggregation': 's9'}
        },
        'aggregation_links': {
            's4': {'core_links': ['link_25', 'link_26']},
            's5': {'core_links': ['link_27', 'link_28']},
            's6': {'core_links': ['link_29', 'link_30']},
            's7': {'core_links': ['link_31', 'link_32']},
            's8': {'core_links': ['link_33', 'link_34']},
            's9': {'core_links': ['link_35', 'link_36']}
        },
        'core_links': ['link_37', 'link_38', 'link_39']
    }
    
    # Define link capacities (Mbps) based on 5G backhaul hierarchy
    link_capacities = {
        **{f'link_{i}': 10000 for i in range(1, 25)}, 
        **{f'link_{i}': 30000 for i in range(25, 37)},
        **{f'link_{i}': 50000 for i in range(37, 40)}
    }
    
    # Create date range
    start_date = datetime(2024, 1, 1)
    hours = num_days * 24
    timestamps = [start_date + timedelta(hours=i) for i in range(hours)]
    
    traffic_data = []
    
    # Step 1: Generate host traffic (base station demand)
    host_traffic = {}
    for host_id, host_info in topology['hosts'].items():
        host_traffic[host_id] = generate_host_traffic(timestamps, host_info['type'])
    
    # Step 2: Generate access links (split host traffic between two access links)
    access_link_traffic = {}
    for host_id, host_info in topology['hosts'].items():
        access_links = host_info['access_links']
        host_traffic_series = host_traffic[host_id]
        
        # Split traffic 60-40 between the two access links
        for i, link_id in enumerate(access_links):
            split_ratio = 0.6 if i == 0 else 0.4
            access_link_traffic[link_id] = host_traffic_series * split_ratio
    
    # Step 3: Generate aggregation-core links
    aggregation_link_traffic = {}
    
    # Group hosts by their aggregation switch
    aggregation_hosts = {}
    for host_id, host_info in topology['hosts'].items():
        agg_switch = host_info['aggregation']
        if agg_switch not in aggregation_hosts:
            aggregation_hosts[agg_switch] = []
        aggregation_hosts[agg_switch].append(host_id)
    
    # Calculate traffic for each aggregation switch
    for agg_switch, agg_info in topology['aggregation_links'].items():
        # Sum ALL traffic from hosts connected to this aggregation switch
        total_agg_traffic = np.zeros(len(timestamps))
        
        if agg_switch in aggregation_hosts:
            for host_id in aggregation_hosts[agg_switch]:
                total_agg_traffic += host_traffic[host_id]
        
        # Split aggregation traffic between two core links
        core_links = agg_info['core_links']
        for i, link_id in enumerate(core_links):
            split_ratio = 0.55 if i == 0 else 0.45
            aggregation_link_traffic[link_id] = total_agg_traffic * split_ratio
    
    # Step 4: Generate core link traffic
    core_link_traffic = {}
    core_peaks = [0.3, 0.4, 0.3]
    for i, link_id in enumerate(topology['core_links']):
        base_traffic = generate_core_traffic(timestamps, core_peaks[i])
        core_link_traffic[link_id] = base_traffic
    
    # Combine all link traffic
    all_links = {**access_link_traffic, **aggregation_link_traffic, **core_link_traffic}
    
    # Create final dataset with bandwidth utilization
    for link_id, traffic_series in all_links.items():
        link_capacity = link_capacities[link_id]
        
        for timestamp, traffic_volume in zip(timestamps, traffic_series):
            packet_count = calculate_packet_count(traffic_volume)
            
            # Calculate bandwidth utilization (ratio of traffic to capacity)
            bandwidth_utilization = min(1.0, traffic_volume / link_capacity)  # Cap at 100%
            
            traffic_data.append({
                'timestamp': timestamp,
                'day_of_week': timestamp.strftime('%A'),
                'link_id': link_id,
                'traffic_volume': max(10, traffic_volume),
                'packet_count': packet_count,
                'bandwidth_utilization': bandwidth_utilization
            })
    
    return pd.DataFrame(traffic_data)

def generate_host_traffic(timestamps, host_type):
    """Generate traffic for a specific host type"""
    traffic = np.zeros(len(timestamps))
    
    for i, timestamp in enumerate(timestamps):
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        
        # Base pattern based on host type
        if host_type == 'business':
            if 8 <= hour <= 18:
                base = 3000 + (hour - 8) * 400
            else:
                base = 500 + abs(hour - 2) * 100
            
            if day_of_week >= 5:
                base *= 0.4
            else:
                base *= 1.2
                
        else:  # residential
            if 18 <= hour <= 23:
                base = 2000 + (hour - 18) * 300
            elif 12 <= hour <= 14:
                base = 1500 + (hour - 12) * 200
            else:
                base = 300 + abs(hour - 6) * 100
            
            if day_of_week >= 5:
                base *= 1.5
            else:
                base *= 0.8
        
        noise = np.random.normal(0, base * 0.1)
        traffic[i] = max(10000, base + noise)
    
    return traffic

def generate_core_traffic(timestamps, peak_factor):
    """Generate core link traffic"""
    traffic = np.zeros(len(timestamps))
    
    for i, timestamp in enumerate(timestamps):
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        
        if 10 <= hour <= 16:
            base = 20000 + (hour - 10) * 2000
        else:
            base = 8000 + abs(hour - 4) * 1000
        
        if day_of_week >= 5:
            base *= 0.7
        else:
            base *= 1.1
        
        base *= peak_factor
        noise = np.random.normal(0, base * 0.1)
        traffic[i] = max(50000, base + noise)
    
    return traffic

def calculate_packet_count(traffic_volume_mbps):
    """Convert traffic volume to packet count"""
    avg_packet_size_bytes = 800
    packets_per_second = (traffic_volume_mbps * 1_000_000) / (avg_packet_size_bytes * 8)
    packets_per_hour = packets_per_second * 3600
    
    variation = np.random.normal(1, 0.2)
    return int(max(1, packets_per_hour * variation))

# Generate and save the dataset
print("Generating traffic data with bandwidth utilization...")
df = generate_topology_aware_traffic(num_days=240)

df = df.rename(columns={
    'traffic_volume': 'traffic_volume (Mbps)',
    'packet_count': 'packet_count (packets/hour)',
    'bandwidth_utilization': 'bandwidth_utilization (ratio)'
})
df['link_num'] = df['link_id'].str.extract('(\d+)').astype(int)
df = df.sort_values(['timestamp', 'link_num']).reset_index(drop=True)
df = df.drop('link_num', axis=1)

print(f"Generated {len(df):,} records")
print(f"Columns: {df.columns.tolist()}")
print(f"Sample data with utilization:")
print(df.head(10))

# Save to CSV
df.to_csv('5g_backhaul_traffic.csv', index=False)
print("Dataset saved successfully!")