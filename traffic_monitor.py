from operator import attrgetter
from ryu.base import app_manager
from ryu.app import simple_switch_13
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import ether_types
import json
import time

class TrafficMonitor(app_manager.RyuApp):
    flow_path = []
    filename = "flow_path.json"
    def __init__(self, *args, **kwargs):
        super(TrafficMonitor, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)
        self.pre_byte = {}
        self.flow_pre_byte = {}
        self.conjunction = {}
        self.flow_path = self._load_path(self.filename)

        #print(self.flow_path)
    #algorithms =[alg1(),alg2()]
   # def update(flowId,method):
        #if method == 'baseline':
          #  baselineUpdate()
    def _baselineUpdate(self,flowid):
        flowInfo =  self.flow_path[flowid]
        
        if flowInfo['state'] == 'main':
            old = 'main'
            new = 'backup'
        else:
            old = 'backup'
            new = 'main'
        
        # delete
        for device in flowInfo[old + '_A']:
            switch = self.datapaths[int(device['device_id'])]           #, device['output_port']
            parser = switch.ofproto_parser
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=flowInfo['src_ip'], ipv4_dst=flowInfo['dst_ip'])
            self.del_flow(switch,match)
        for device in flowInfo[old+'_B']:
            
            switch = self.datapaths[int(device['device_id'])]           #, device['output_port']
            parser = switch.ofproto_parser
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=flowInfo['dst_ip'], ipv4_dst=flowInfo['src_ip'])
            self.del_flow(switch,match)
        # add
        for device in flowInfo[new+'_A']:
            switch = self.datapaths[int(device['device_id'])] 
            parser = switch.ofproto_parser
            actions = [parser.OFPActionOutput(int(device['output_port']))]
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=flowInfo['src_ip'], ipv4_dst=flowInfo['dst_ip'])
            self.add_flow(switch, 1024, match, actions)
        # Install B
        for device in flowInfo[new+'_B']:
            switch = self.datapaths[int(device['device_id'])] 
            parser = switch.ofproto_parser
            actions = [parser.OFPActionOutput(int(device['output_port']))]
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=flowInfo['dst_ip'], ipv4_dst=flowInfo['src_ip'])
            self.add_flow(switch, 1024, match, actions)
        
        flowInfo['state'] = new 

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly. The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        #actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD, 0)]
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        #self.send_port_states_request(datapath)
        

        for path in self.flow_path:
            # Install A
            for pair in path['main_A']:
                #print(pair)
                #print(datapath.id, pair['device_id'])
                if int(datapath.id) == int(pair['device_id']):
                    actions = [parser.OFPActionOutput(int(pair['output_port']))]
                    match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=path['src_ip'], ipv4_dst=path['dst_ip'])
                    self.add_flow(datapath, 1024, match, actions)
            # Install B
            for pair in path['main_B']:
                #print(pair)
                #print(datapath.id, pair['device_id'])
                if int(datapath.id) == int(pair['device_id']):
                    actions = [parser.OFPActionOutput(int(pair['output_port']))]
                    match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=path['dst_ip'], ipv4_dst=path['src_ip'])
                    self.add_flow(datapath, 1024, match, actions)
        #self.send_port_states_request(datapath)

            
    def send_port_states_request(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        request = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(request)

            

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packetInHandler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        #print("---------datapath id %d ----------" % (datapath.id))
        #print(pkt.get_protocols)
        if eth.ethertype == ether_types.ETH_TYPE_LLDP or eth.ethertype == ether_types.ETH_TYPE_IPV6 or eth.ethertype == ether_types.ETH_TYPE_ARP:
            return


        return

    def _load_path(self, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        for flow in data:
            flow['state'] = 'main'
        return data    

    def drop_flow(self, datapath, match):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        mod = parser.OFPFlowMod(
            datapath=datapath, match=match,
            command=ofproto.OFPFC_MODIFY)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        ofproto = datapath.ofproto
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath

                self.pre_byte[datapath.id] = {}
                self.conjunction[datapath.id] = {}
                for port in datapath.ports.keys():
                    #if port < ofproto.OFPP_MAX:
                    self.pre_byte[datapath.id][port] = 0
                    self.conjunction[datapath.id][port] = False
                #print(datapath.ports.keys())
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]
        #print("-----pre_byte-----")
        #print(self.pre_byte)

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(5)

    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)
        
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        datapath = ev.msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto
        print("Flow Statistical Information")
        self.logger.info('datapath         ' 
                         'in-port  '
                         'match src_ip src_port       dst_ip dst_port  protocol '
                         'action   '
                         'packets  bytes    '
                         'delta byte')
        self.logger.info('---------------- '
                         '-------- '
                         '----------------------------------------------------- '
                         '-------- '
                         '-------- -------- '
                         '--------- ')
        for stat in body:
            #print(stat)
            #print(stat.instructions)
            #for m in stat.match._fields2:
            #    print(m)
            #print(stat.match['ipv4_src'])
            self.flow_pre_byte.setdefault(dpid, {})
            flow_match = None
            if 'ip_proto' in stat.match and stat.match['ip_proto'] == 6:             
                flow_match = (stat.match.get("in_port"), 
                            stat.match.get("ipv4_src"),
                            stat.match.get("tcp_src"),
                            stat.match.get("ipv4_dst"),
                            stat.match.get("tcp_dst"),
                            "TCP",)
            elif 'ip_proto' in stat.match and stat.match['ip_proto'] == 17:             
                flow_match = (stat.match.get("in_port"), 
                            stat.match.get("ipv4_src"),
                            stat.match.get("udp_src"),
                            stat.match.get("ipv4_dst"),
                            stat.match.get("udp_dst"),
                            "UDP",)

            if flow_match not in self.flow_pre_byte[dpid]:
                #self.logger.info("Add flow")
                self.flow_pre_byte[dpid][flow_match] = 0
            delta = stat.byte_count - self.flow_pre_byte[dpid][flow_match]
            #print(len(self.flow_pre_byte[dpid]))

            #print(stat.__dict__)
            in_port = stat.match.get('in_port') if stat.match.get('inport') < ofproto.OFPP_MAX else None
            #print(in_port)
            out_port = None
            try:
                action = "port %d" % (stat.instructions[0].actions[0].port)
                if stat.instructions[0].actions[0].port < ofproto.OFPP_MAX:
                    out_port = stat.instructions[0].actions[0].port 
            except:
                action = "dropped"
                
            if 'ip_proto' in stat.match and stat.match['ip_proto'] == 6:
                
                self.logger.info('%016x %8x %12s %8s %12s %8s %8s %8s %8d %8d %9d',
                                 ev.msg.datapath.id,
                                 stat.match['in_port'],
                                 stat.match['ipv4_src'],
                                 stat.match['tcp_src'],
                                 stat.match['ipv4_dst'],
                                 stat.match['tcp_dst'],
                                 "TCP",
                                 action, 
                                 stat.packet_count, 
                                 stat.byte_count, 
                                 delta)         
                
            elif 'ip_proto' in stat.match and stat.match['ip_proto'] == 17:
                self.logger.info('%016x %8x %12s %8s %12s %8s %8s %8s %8d %8d %9d',
                                 ev.msg.datapath.id,
                                 stat.match['in_port'],
                                 stat.match['ipv4_src'],
                                 stat.match['udp_src'],
                                 stat.match['ipv4_dst'],
                                 stat.match['udp_dst'],
                                 "UDP",
                                 action, 
                                 stat.packet_count, 
                                 stat.byte_count, 
                                 delta)
            #self.logger.info(delta)
            self.flow_pre_byte[dpid][flow_match] = stat.byte_count    

            # Deal with conjunction 
            if ((in_port != None and self.conjunction[dpid][in_port]) or (out_port != None and self.conjunction[dpid][out_port])) and delta > 5e5:
                print("Deal with conjunction")
                print(delta)
                if in_port != None:
                    self.conjunction[dpid][in_port] = False
                if out_port != None:
                    self.conjunction[dpid][out_port] = False
                
                self.drop_flow(datapath, stat.match)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body
        datapath = ev.msg.datapath
        print("In handler")
        time.sleep(10)
        print("Delete!!!")
        self._baselineUpdate(0)
        '''
        print("Port Statistical Information")
        self.logger.info('datapath         port     '
                         'rx-pkts  rx-bytes '
                         'tx-pkts  tx-bytes '
                         'dropped  error     delta-byte-count')
        self.logger.info('---------------- -------- '
                         '-------- -------- '
                         '-------- -------- '
                         '-------- --------  --------------- ')
        for stat in sorted(body, key=attrgetter('port_no')):
            #print(stat)
            #print(datapath.id, stat.port_no)
            delta = stat.rx_bytes + stat.tx_bytes - self.pre_byte[datapath.id][stat.port_no] 
            self.logger.info('%016x %8x %8d %8d %8d %8d %8d %8d %15d',
                             datapath.id, stat.port_no,
                             stat.rx_packets, stat.rx_bytes,
                             stat.tx_packets, stat.tx_bytes, 
                             stat.rx_dropped + stat.tx_dropped, 
                             stat.rx_errors + stat.tx_errors, 
                             delta)
            self.pre_byte[datapath.id][stat.port_no] = stat.rx_bytes + stat.tx_bytes
            #print(delta)
            #print(delta>1e6)
            if delta > 1e6:
                self.conjunction[datapath.id][stat.port_no] = True
                self.logger.info("Conjunction occur!!!!")  
        '''

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        instructionList = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath,
                                    buffer_id=buffer_id,
                                    priority=priority,
                                    match=match,
                                    instructions=instructionList)
        else:
            mod = parser.OFPFlowMod(datapath=datapath,
                                    priority=priority,
                                    match=match,
                                    instructions=instructionList)
        datapath.send_msg(mod)
    
    def del_flow(self, datapath, match):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        mod = parser.OFPFlowMod(datapath=datapath,
                                command=ofproto.OFPFC_DELETE,
                                out_port=ofproto.OFPP_ANY,
                                out_group=ofproto.OFPG_ANY,
                                match=match)
        datapath.send_msg(mod)
