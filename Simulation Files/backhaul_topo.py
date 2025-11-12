from mininet.topo import Topo

class BackhaulTopo(Topo):
    """5G Backhaul Topology with Core Host"""
    
    def __init__(self):
        Topo.__init__(self)

        # --- Create Core Host (Internet Gateway) ---
        core_host = self.addHost('h_core')

        # --- Create Core Switches (3) ---
        core_switches = []
        for i in range(1, 4):
            core_switches.append(self.addSwitch(f's{i}'))

        # --- Create Aggregation Switches (6) ---
        aggregation_switches = []
        for i in range(4, 10):
            aggregation_switches.append(self.addSwitch(f's{i}'))

        # --- Create Base Station Hosts (12) ---
        base_hosts = []
        for i in range(1, 13):
            base_hosts.append(self.addHost(f'h{i}'))

        # --- Connect Core Host to ALL Core Switches ---
        for switch in core_switches:
            self.addLink(core_host, switch, bw=50, delay='0.1ms')

        # --- Core Layer Connections (3 links) ---
        self.addLink(core_switches[0], core_switches[1], bw=50, delay='0.1ms')  # s1-s2
        self.addLink(core_switches[0], core_switches[2], bw=50, delay='0.1ms')  # s1-s3  
        self.addLink(core_switches[1], core_switches[2], bw=50, delay='0.1ms')  # s2-s3

        # --- Core to Aggregation Connections (12 links) ---
        core_agg_links = [
            ('s1', 's4'), ('s2', 's4'),  # to agg4
            ('s1', 's5'), ('s3', 's5'),  # to agg5
            ('s2', 's6'), ('s3', 's6'),  # to agg6
            ('s1', 's7'), ('s2', 's7'),  # to agg7
            ('s1', 's8'), ('s3', 's8'),  # to agg8
            ('s2', 's9'), ('s3', 's9')   # to agg9
        ]
        for switch_a, switch_b in core_agg_links:
            self.addLink(switch_a, switch_b, bw=20, delay='1ms')

        # --- Aggregation to Host Connections (24 links) ---
        agg_host_links = [
            # Each host connected to 2 aggregation switches
            ('s4', 'h1'), ('s5', 'h1'),  # h1
            ('s4', 'h2'), ('s6', 'h2'),  # h2
            ('s5', 'h3'), ('s7', 'h3'),  # h3
            ('s6', 'h4'), ('s8', 'h4'),  # h4
            ('s7', 'h5'), ('s9', 'h5'),  # h5
            ('s6', 'h6'), ('s8', 'h6'),  # h6
            ('s9', 'h7'), ('s5', 'h7'),  # h7
            ('s4', 'h8'), ('s6', 'h8'),  # h8
            ('s5', 'h9'), ('s7', 'h9'),  # h9
            ('s6', 'h10'), ('s8', 'h10'), # h10
            ('s7', 'h11'), ('s9', 'h11'), # h11
            ('s8', 'h12'), ('s9', 'h12')  # h12
        ]
        for switch, host in agg_host_links:
            self.addLink(switch, host, bw=5, delay='2ms')

if __name__ == '__main__':
    topo = BackhaulTopo()
    print("✅ Backhaul topology with core host created successfully!")
    print(f"Total switches: {len(topo.switches())}")
    print(f"Total hosts: {len(topo.hosts())}")
    print(f"Total links: {len(topo.links())}")