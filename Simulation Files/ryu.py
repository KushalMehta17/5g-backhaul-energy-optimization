from ryu.app.simple_switch_stp_13 import SimpleSwitch13
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER, set_ev_cls

class BasicSwitchController(SimpleSwitch13):
    """Ryu controller with SimpleSwitch support."""

    def __init__(self, *args, **kwargs):
        super(BasicSwitchController, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.logger.info(">> Initialized RYU Controller successfully")

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.info(f"*** Switch s{datapath.id} connected")
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.info(f"*** Switch s{datapath.id} disconnected")
                del self.datapaths[datapath.id]

