from mininet.net import Mininet
from mininet.node import Controller, RemoteController, Host
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.clean import cleanup

def create_5g_backhaul_topology():
    cleanup()

    info("\n=== Initializing 5G Backhaul Topology ===\n")
    # We MUST use RemoteController to connect to Ryu
    net = Mininet(controller=RemoteController, link=TCLink, host=BondedHost)
    
    info("-> Adding Remote Controller (Ryu)\n")
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    
    info("-> Creating Core Switches\n")
    core_switches = [net.addSwitch(f's{i}') for i in range(1, 4)]
    
    info("-> Creating Aggregation Switches\n")
    aggregation_switches = [net.addSwitch(f's{i}') for i in range(4, 10)]
    
    info("-> Creating Host Nodes (Base Stations)\n")
    hosts = [net.addHost(f'h{i}', id=i) for i in range(1, 13)]  
    
    info("\n-> Establishing Core Interconnections (50Gbps, 0.1ms)\n")
    net.addLink(core_switches[0], core_switches[1], bw=50, delay='0.1ms')
    net.addLink(core_switches[0], core_switches[2], bw=50, delay='0.1ms')
    net.addLink(core_switches[1], core_switches[2], bw=50, delay='0.1ms')
    
    info("\n-> Connecting Core to Aggregation Layer (20Gbps, 1ms)\n")
    core_agg_links = [
        (1,4), (2,4),
        (1,5), (3,5),
        (2,6), (3,6),
        (1,7), (2,7),
        (1,8), (3,8),
        (2,9), (3,9)
    ]
    for core_id, agg_id in core_agg_links:
        net.addLink(net.get(f's{core_id}'), net.get(f's{agg_id}'), bw=20, delay='1ms')
    
    info("\n-> Connecting Aggregation to Host Layer (5Gbps, 2ms)\n")
    agg_host_mapping = [
        (4,1), (5,1), (4,2), (6,2),
        (5,3), (7,3), (6,4), (8,4),
        (7,5), (9,5), (8,6), (6,6),
        (9,7), (5,7), (4,8), (6,8),
        (5,9), (7,9), (6,10), (8,10),
        (7,11), (9,11), (8,12), (9,12)
    ]

    host_links = {}
    for agg_id, host_id in agg_host_mapping:
        host_name = f'h{host_id}'
        switch_name = f's{agg_id}'
        
        iface_num = host_links.get(host_name, 0)
        
        # Add the link
        net.addLink(net.get(switch_name), net.get(host_name), 
                    intfName1=f'{switch_name}-h{host_id}-{iface_num}',
                    intfName2=f'{host_name}-eth{iface_num}',
                    bw=5, delay='2ms')

        host_links[host_name] = iface_num + 1

    
    info("-> Building Network\n")
    net.build()
    
    info("\n-> Starting Core and Aggregation Switches\n")
    for switch in core_switches + aggregation_switches:
        switch.start([c0])
    
    info("\n\n=== 5G Backhaul Topology Successfully Deployed ===\n")
    return net

class BondedHost(Host):
    def config(self, **params):
        super(BondedHost, self).config(**params)

        if 'eth1' not in self.intfs:
            return

        self.cmd('modprobe bonding')
        self.cmd('ip link add bond0 type bond mode 802.3ad')
        self.cmd('ip link set eth0 master bond0')
        self.cmd('ip link set eth1 master bond0')
        self.cmd('ip link set bond0 up')
        
        # 1. Get IP from params or assign default
        ip_addr = params.get('ip')
        if not ip_addr:
             # Mininet default IP
             ip_addr = '10.0.0.%d/8' % self.id
        
        # 2. Clear IP from eth0 and eth1
        self.cmd(f'ip addr flush dev {self.name}-eth0')
        self.cmd(f'ip addr flush dev {self.name}-eth1')
        
        # 3. Add IP to bond0
        self.cmd(f'ip addr add {ip_addr} dev bond0')
        
        # 4. Turn up the enslaved interfaces
        self.cmd(f'ip link set {self.name}-eth0 up')
        self.cmd(f'ip link set {self.name}-eth1 up')
        
        self.cmd(f'echo "--- Host {self.name}: Bonded eth0 and eth1 to bond0 with IP {ip_addr} ---"')

    def terminate(self):
        # Cleanup
        self.cmd('ip link set bond0 down')
        self.cmd('ip link delete bond0')
        super(BondedHost, self).terminate()


if __name__ == '__main__':
    setLogLevel('info')
    net = create_5g_backhaul_topology()
    print("\n--------------------------------------------")
    print("    5G BACKHAUL TOPOLOGY SIMULATION STARTED")
    print("    (Connected to Ryu Remote Controller)")
    print("--------------------------------------------\n")
    CLI(net)
    print("\n--------------------------------------------")
    print("    5G BACKHAUL TOPOLOGY SIMULATION ENDED")
    print("--------------------------------------------\n")
    net.stop()