import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D 

def get_bandwidth(link_id_num):
    if 1 <= link_id_num <= 24:
        return "5Gbps"
    elif 25 <= link_id_num <= 36:
        return "20Gbps"
    elif 37 <= link_id_num <= 39:
        return "50Gbps"
    return ""

def draw_topology():
    print("Generating topology graph...")
    G = nx.Graph()

    # --- Define Node Groups ---
    core_nodes = ['s1', 's2', 's3']
    agg_nodes = ['s4', 's5', 's6', 's7', 's8', 's9']
    host_nodes = [f'h{i}' for i in range(1, 13)]

    # Add all nodes to the graph
    G.add_nodes_from(core_nodes)
    G.add_nodes_from(agg_nodes)
    G.add_nodes_from(host_nodes)
    
    # (link_id, switch_node, host_node)
    host_links = [
        (1, 's4', 'h1'), 
        (4, 's6', 'h2'),
        (6, 's7', 'h3'),
        (8, 's8', 'h4'),
        (10, 's9', 'h5'),
        (12, 's8', 'h6'),
        (14, 's5', 'h7'),
        (15, 's4', 'h8'),
        (18, 's7', 'h9'),
        (20, 's8', 'h10'),
        (22, 's9', 'h11'),
        (24, 's9', 'h12')
    ]

    core_agg_links = [
        (26, 's2', 's4'),
        (28, 's3', 's5'),
        (30, 's3', 's6'),
        (32, 's2', 's7'),
        (34, 's3', 's8'),
        (36, 's3', 's9')
    ]
    
    # (link_id, switch_a, switch_b)
    core_links = [
        (37, 's1', 's2'),
        (38, 's1', 's3'),
        (39, 's2', 's3'),
    ]
    
    # --- Add Edges to Graph ---
    edge_labels = {}
    
    for link_id, switch_node, host_node in host_links:
        edge = (host_node, switch_node)
        G.add_edge(*edge)
        edge_labels[edge] = f"L{link_id}\n{get_bandwidth(link_id)}"

    for link_id, dpid_a, dpid_b in core_agg_links:
        edge = (dpid_a, dpid_b)
        G.add_edge(*edge)
        edge_labels[edge] = f"L{link_id}\n{get_bandwidth(link_id)}"
    
    # Define node colors
    core_color = '#e63946'
    agg_color = '#fca311' 
    host_color = '#4c956c' 
    
    pos = {}
    # Core layer (y=3)
    pos['s1'] = (3, 3)
    pos['s2'] = (6.0, 3.2) 
    pos['s3'] = (9, 3)
    
    # Aggregation layer (y=2)
    agg_x = [2.5, 4, 5.5, 7, 8.5, 10]
    for i, node in enumerate(agg_nodes):
        pos[node] = (agg_x[i], 2)
        
    # Host layer (y=1)
    host_x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    for i, node in enumerate(host_nodes):
        pos[node] = (host_x[i], 1)
        
    sub_labels = {}
    for i, n in enumerate(core_nodes): sub_labels[n] = f"Core {i+1}"
    for i, n in enumerate(agg_nodes): sub_labels[n] = f"Agg {i+1}"
    for i, n in enumerate(host_nodes): sub_labels[n] = f"Host {i+1}"

    plt.figure(figsize=(24, 18))

    nx.draw_networkx_nodes(
        G, pos, nodelist=core_nodes, node_shape='o', node_size=3000,
        node_color=core_color
    )
    nx.draw_networkx_nodes(
        G, pos, nodelist=agg_nodes, node_shape='s', node_size=2500,
        node_color=agg_color
    )
    nx.draw_networkx_nodes(
        G, pos, nodelist=host_nodes, node_shape='^', node_size=2500,
        node_color=host_color
    )

    nx.draw_networkx_edges(
        G, pos,
        edge_color='#555555', 
        width=1.5
    )

    nx.draw_networkx_labels(
        G, pos,
        font_size=12,
        font_weight='bold',
        font_color='black'
    )
    
    for node, (x, y) in pos.items():
        plt.text(
            x, y - 0.15, # Offset below the node
            s=sub_labels[node],
            horizontalalignment='center',
            fontsize=16
        )

    nx.draw_networkx_edge_labels(
        G,
        pos,
        edge_labels=edge_labels,
        font_size=16,
        font_color='#111111',
        bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', boxstyle='round,pad=0.2')
    )
    
    # Create the legend 
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Core Switches (s1-s3)',
               markerfacecolor=core_color, markersize=22),
        Line2D([0], [0], marker='s', color='w', label='Aggregation Switches (s4-s9)',
               markerfacecolor=agg_color, markersize=22),
        Line2D([0], [0], marker='^', color='w', label='Hosts/Base Stations (h1-h12)',
               markerfacecolor=host_color, markersize=22)
    ]
    plt.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 1.01),
             ncol=3, fontsize=25, frameon=False)

    
    plt.title("5G Backhaul Network Hierarchy", size=30, y=1.02) 
    plt.axis('off') 
    plt.tight_layout()
    
    # Save the PNG 
    output_file = "5G_backhaul_topology.png"
    plt.savefig(output_file, format="PNG", dpi=200)
    print(f"Success! Topology saved to {output_file}")

if __name__ == '__main__':
    draw_topology()
