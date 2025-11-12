"""
RYU SDN CONTROLLER 
"""
from ryu.app.simple_switch_stp_13 import SimpleSwitch13
from collections import OrderedDict
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, set_ev_cls
from ryu.app.wsgi import WSGIApplication, ControllerBase, route
from webob import Response
import json
from ryu.lib import stplib

class EnergyAwareController(SimpleSwitch13):

    _CONTEXTS = {
        'wsgi': WSGIApplication,
        'stplib': stplib.Stp  
    }

    def __init__(self, *args, **kwargs):
        super(EnergyAwareController, self).__init__(*args, **kwargs)

        # Essential for topology discovery 
        self.topology_api_app = self
        self.datapaths = {}
        
        # We only need the map to serve it via the API
        self.link_index_to_edge = OrderedDict()
        
        # Build the map once on startup
        self._build_topology()
        
        # Register this app with the web server to expose APIs
        wsgi = kwargs['wsgi']
        wsgi.register(EnergyAwareControllerAPI, {'EnergyController': self})

        self.logger.info("Network OS: STP/L2 is running. API is live on :8080")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Capture switch connections"""
        super(EnergyAwareController, self).switch_features_handler(ev)
        
        datapath = ev.msg.datapath
        self.datapaths[datapath.id] = datapath
        self.logger.info(f"📡 Switch s{datapath.id} connected.")

    def _build_topology(self):
        self.link_index_to_edge = OrderedDict()
        
        host_links = [
            (1, 4, 1, 1), (2, 5, 1, 1), (3, 4, 2, 2), (4, 6, 1, 2),
            (5, 5, 2, 3), (6, 7, 1, 3), (7, 6, 2, 4), (8, 8, 1, 4),
            (9, 7, 2, 5), (10, 9, 1, 5), (11, 6, 3, 6), (12, 8, 2, 6),
            (13, 9, 2, 7), (14, 5, 3, 7), (15, 4, 3, 8), (16, 6, 4, 8),
            (17, 5, 4, 9), (18, 7, 3, 9), (19, 6, 5, 10), (20, 8, 3, 10),
            (21, 7, 4, 11), (22, 9, 3, 11), (23, 8, 4, 12), (24, 9, 4, 12),
        ]
        
        core_links = [
            (25, 1, 1, 2, 1), (26, 1, 2, 3, 1), (27, 2, 2, 3, 2),
        ]
        
        core_agg_links = [
            (28, 1, 3, 4, 3), (29, 2, 3, 4, 4), (30, 1, 4, 5, 3), (31, 3, 3, 5, 4),
            (32, 2, 4, 6, 5), (33, 3, 4, 6, 6), (34, 1, 5, 7, 4), (35, 2, 5, 7, 5),
            (36, 1, 6, 8, 5), (37, 3, 5, 8, 6), (38, 2, 6, 9, 6), (39, 3, 6, 9, 7),
        ]
        
        for link_id, switch_dpid, switch_port, host_id in host_links:
            self.link_index_to_edge[f'link_{link_id}'] = (
                switch_dpid, switch_port, f'00:00:00:00:{switch_dpid:02x}:{switch_port:02x}',
                -host_id, 1, f'00:00:00:00:00:{host_id:02x}'
            )

        for link_id, dpid_a, port_a, dpid_b, port_b in (core_links + core_agg_links):
            self.link_index_to_edge[f'link_{link_id}'] = (
                dpid_a, port_a, f'00:00:00:00:{dpid_a:02x}:{port_a:02x}',
                dpid_b, port_b, f'00:00:00:00:{dpid_b:02x}:{port_b:02x}'
            )
        
        self.logger.info(f"Built topology map with {len(self.link_index_to_edge)} links.")

# --- Separate API controller class ---
class EnergyAwareControllerAPI(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(EnergyAwareControllerAPI, self).__init__(req, link, data, **config)
        self.controller = data['EnergyController']

    @route('topology', '/topology', methods=['GET'])
    def get_topology(self, req, **kwargs):
        """Serves the topology map as JSON"""
        try:
            if self.controller.link_index_to_edge:
                topology_data = {}
                for link_id, link_tuple in self.controller.link_index_to_edge.items():
                    topology_data[link_id] = list(link_tuple)  # Convert tuple to list for JSON
                
                # Encode the JSON response
                body = json.dumps({
                    'topology': topology_data,
                    'total_links': len(topology_data)
                })
                return Response(
                    content_type='application/json; charset=utf-8',
                    body=body.encode('utf-8')  # Explicitly encode to bytes
                )
            else:
                return Response(
                    status=500,
                    content_type='text/plain; charset=utf-8',
                    body="Topology map not ready.".encode('utf-8')
                )
        except Exception as e:
            return Response(
                status=500,
                content_type='text/plain; charset=utf-8', 
                body=str(e).encode('utf-8')
            )