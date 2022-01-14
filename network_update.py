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
from ryu.ofproto import ofproto_v1_3
import json
import time

class NetworkUpdate(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    flow_path = []
    filename = "flow_path.json"
    method = 'IMU'
    #method = 'baseline'
    target_flow = 0
    def __init__(self, *args, **kwargs):
        super(NetworkUpdate, self).__init__(*args, **kwargs)
        self.datapaths = {}
        #self.monitor_thread = hub.spawn(self._monitor)
        self.monitor_thread = hub.spawn(self._periodical_update)
        self.pre_byte = {}
        self.flow_pre_byte = {}
        self.conjunction = {}
        self.flow_path = self._load_path(self.filename)

        #print(self.flow_path)
    #algorithms =[alg1(),alg2()]
    def update(self, flowId, method):
        if method == 'baseline':
            self._baselineUpdate(flowId)
        elif method == 'IMU':
            self._IMU_update(flowId)

    def _IMU_update(self, flowid):
        flowInfo =  self.flow_path[flowid]
        self._IMU_update_dir(flowid, 'A')
        #self._IMU_update_dir(flowid, 'B')
        state = flowInfo['state']
        if state == 'main':
            flowInfo['state'] = 'backup'
        else:
            flowInfo['state'] = 'main'

    def _IMU_update_dir(self, flowid, d):
        print("IMU " + d)
        d = '_' + d
        flowInfo =  self.flow_path[flowid]
        if flowInfo['state'] == 'main':
            old = 'main'
            new = 'backup'
        else:
            old = 'backup'
            new = 'main'

        newSet = set(flowInfo[new + d].keys())
        oldSet = set(flowInfo[old + d].keys())
        intersection = newSet & oldSet
        addSet = newSet - intersection
        deleteSet = oldSet - intersection
        noEditionSet = set()
        replacementSet = set()

        for device in intersection:
            oldIn = flowInfo[old + d][device]['input_port']
            oldOut = flowInfo[old + d][device]['output_port']
            newIn = flowInfo[new + d][device]['input_port']
            newOut = flowInfo[new + d][device]['output_port']
            if (oldIn,oldOut) == (newIn,newOut):
                noEditionSet.add(device)
            elif oldIn == newIn and oldOut != newOut:
                replacementSet.add(device)
            else:
                addSet.add(device)
                deleteSet.add(device)
        '''    
        print("-------------------------------")
        print(replacementSet)
        print(addSet)
        print(deleteSet)
        '''

        if 'A' in d:
            src_ip = flowInfo['src_ip']
            dst_ip = flowInfo['dst_ip']
        else:
            src_ip = flowInfo['dst_ip']
            dst_ip = flowInfo['src_ip']
        
        # Phase 1: Install new rules
        print("To delete")
        for device in addSet:
            print(device)
            switch = self.datapaths[int(device)] 
            parser = switch.ofproto_parser
            ports = flowInfo[new+d][device]
            actions = [parser.OFPActionOutput(int(ports['output_port']))]
            
            match = parser.OFPMatch(in_port=int(ports['input_port']),eth_type=ether_types.ETH_TYPE_IP, ipv4_src=src_ip, ipv4_dst=dst_ip)
            self.add_flow(switch, 1024, match, actions)
            #req = parser.OFPBarrierRequest(switch)
            #switch.send_msg(req)
            
        time.sleep(0.1)

        # Phase 2: replacement
        print("To replace")
        for device in replacementSet:
            print(device)
            switch = self.datapaths[int(device)]
            parser = switch.ofproto_parser
            ports = flowInfo[new+d][device]
            actions = [parser.OFPActionOutput(int(ports['output_port']))]
            match = parser.OFPMatch(in_port=int(ports['input_port']),eth_type=ether_types.ETH_TYPE_IP, ipv4_src=src_ip, ipv4_dst=dst_ip)
            #self.mod_flow(switch,match,actions)
            self.add_flow(switch, 1024, match, actions)
            
            
        time.sleep(0.1)

        # Phase 3: Delete old rules
        print("To add")
        for device in deleteSet:
            print(device)
            switch = self.datapaths[int(device)]
            parser = switch.ofproto_parser
            ports = flowInfo[old+d][device]
            match = parser.OFPMatch(in_port=int(ports['input_port']),eth_type=ether_types.ETH_TYPE_IP, ipv4_src=src_ip, ipv4_dst=dst_ip)
            self.del_flow(switch,match)
        

    def _baselineUpdate(self,flowid):
        print("Baseline")
        flowInfo = self.flow_path[flowid]
        
        if flowInfo['state'] == 'main':
            old = 'main'
            new = 'backup'
        else:
            old = 'backup'
            new = 'main'
        
        d = '_A'
        src_ip = flowInfo['src_ip']
        dst_ip = flowInfo['dst_ip']
        newSet = set(flowInfo[new + d].keys())
        oldSet = set(flowInfo[old + d].keys())
        intersection = newSet & oldSet
        addSet = newSet - intersection
        deleteSet = oldSet - intersection

        for device in intersection:
            oldIn = flowInfo[old + d][device]['input_port']
            oldOut = flowInfo[old + d][device]['output_port']
            newIn = flowInfo[new + d][device]['input_port']
            newOut = flowInfo[new + d][device]['output_port']
            if oldIn == newIn and oldOut != newOut:
                addSet.add(device)
            else:
                addSet.add(device)
                deleteSet.add(device)

        print("To delete")
        for device in deleteSet:
            print("Device ", device)
            switch = self.datapaths[int(device)]
            parser = switch.ofproto_parser
            ports = flowInfo[old+d][device]
            match = parser.OFPMatch(in_port=int(ports['input_port']),eth_type=ether_types.ETH_TYPE_IP, ipv4_src=src_ip, ipv4_dst=dst_ip)
            self.del_flow(switch,match)
            #time.sleep(0.01)

        print("To add")
        for device in addSet:
            print("Device ", device)
            switch = self.datapaths[int(device)] 
            parser = switch.ofproto_parser
            ports = flowInfo[new+d][device]
            actions = [parser.OFPActionOutput(int(ports['output_port']))]
            
            match = parser.OFPMatch(in_port=int(ports['input_port']),eth_type=ether_types.ETH_TYPE_IP, ipv4_src=src_ip, ipv4_dst=dst_ip)
            self.add_flow(switch, 1024, match, actions)
            #time.sleep(0.01)

        flowInfo['state'] = new 
        return 
        '''
        # delete
        for device, ports in flowInfo[old + '_A'].items():
            #if device in flowInfo[new+'_A'].keys() and ports['input_port'] == flowInfo[new+'_A'][device]['input_port'] and ports['output_port'] == flowInfo[new+'_A'][device]['output_port']:
            #    continue
            switch = self.datapaths[int(device)]           #, device['output_port']
            input_port = int(ports['input_port'])
            parser = switch.ofproto_parser
            match = parser.OFPMatch(in_port=input_port, eth_type=ether_types.ETH_TYPE_IP, ipv4_src=flowInfo['src_ip'], ipv4_dst=flowInfo['dst_ip'])
            self.del_flow(switch,match)
        for device, ports in flowInfo[old+'_B'].items():
            switch = self.datapaths[int(device)]           #, device['output_port']
            input_port = int(ports['input_port'])
            parser = switch.ofproto_parser
            match = parser.OFPMatch(in_port=input_port, eth_type=ether_types.ETH_TYPE_IP, ipv4_src=flowInfo['dst_ip'], ipv4_dst=flowInfo['src_ip'])
            self.del_flow(switch,match)
        '''

        
        #time.sleep(0.5)
        '''
        # add
        for device, ports in flowInfo[new+'_A'].items():
            #if device in flowInfo[old+'_A'].keys() and ports['input_port'] == flowInfo[old+'_A'][device]['input_port'] and ports['output_port'] == flowInfo[old+'_A'][device]['output_port']:
            #    continue
            switch = self.datapaths[int(device)] 
            parser = switch.ofproto_parser
            input_port = int(ports['input_port'])
            actions = [parser.OFPActionOutput(int(ports['output_port']))]
            match = parser.OFPMatch(in_port=input_port, eth_type=ether_types.ETH_TYPE_IP, ipv4_src=flowInfo['src_ip'], ipv4_dst=flowInfo['dst_ip'])
            self.add_flow(switch, 1024, match, actions)
        
        # Install B
        for device, ports in flowInfo[new+'_B'].items():
            switch = self.datapaths[int(device)] 
            parser = switch.ofproto_parser
            input_port = int(ports['input_port'])
            actions = [parser.OFPActionOutput(int(ports['output_port']))]
            match = parser.OFPMatch(in_port=input_port, eth_type=ether_types.ETH_TYPE_IP, ipv4_src=flowInfo['dst_ip'], ipv4_dst=flowInfo['src_ip'])
            self.add_flow(switch, 1024, match, actions)
        '''
        

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        device = str(datapath.id)

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly. The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        #actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD, 0)]
        #actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        actions = []
        self.add_flow(datapath, 0, match, actions)
        #self.send_port_states_request(datapath)
        
        ''' 
        ofp_parser = datapath.ofproto_parser
        req = ofp_parser.OFPBarrierRequest(datapath)
        res = datapath.send_msg(req)
        print("Send barrier request, ", res)
        '''

        if datapath.id not in self.datapaths:
            self.logger.debug("register datapath: %016x", datapath.id)
            self.datapaths[datapath.id] = datapath

        for flowInfo in self.flow_path:
            # Install A
            #print(datapath.id)
            #print(flowInfo)
            
            if device in flowInfo['main_A'].keys():
                output_port = int(flowInfo['main_A'][device]['output_port'])
                input_port = int(flowInfo['main_A'][device]['input_port'])
                actions = [parser.OFPActionOutput(output_port)]
                match = parser.OFPMatch(in_port=input_port, eth_type=ether_types.ETH_TYPE_IP, ipv4_src=flowInfo['src_ip'], ipv4_dst=flowInfo['dst_ip'])
                self.add_flow(datapath, 1024, match, actions)

        for flowInfo in self.flow_path:
            # Install B
            #print(datapath.id)
            #print(flowInfo['main_B'][str(datapath.id)])

            if device in flowInfo['main_B'].keys():
                output_port = int(flowInfo['main_B'][device]['output_port'])
                input_port = int(flowInfo['main_B'][device]['input_port'])
                actions = [parser.OFPActionOutput(output_port)]
                match = parser.OFPMatch(in_port=input_port, eth_type=ether_types.ETH_TYPE_IP, ipv4_src=flowInfo['dst_ip'], ipv4_dst=flowInfo['src_ip'])
                self.add_flow(datapath, 1024, match, actions)



    def _load_path(self, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        for flow in data:
            flow['state'] = 'main'
        return data    


    def _periodical_update(self):
        hub.sleep(20)
        print("Start to peridically update flow")
        while True:
            #for dp in self.datapaths.values():
            #    self._request_stats(dp)
            print("---------------")
            if len(self.datapaths) > 1:
                
                print("Update !")
                hub.sleep(5)
                #self.update(1, self.method)
                self.update(self.target_flow, self.method)
                try:
                    #self.update(self.target_flow, self.method)
                    print("Finished")
                    return 
                except:
                    print("Catch")
                    pass
            else:
                print("No switches")
            hub.sleep(5)

    def drop_flow(self, datapath, match):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        mod = parser.OFPFlowMod(
            datapath=datapath, match=match,
            command=ofproto.OFPFC_MODIFY)
        datapath.send_msg(mod)

    def mod_flow(self, datapath, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        instructionList = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, 
                                match=match,
                                command=ofproto.OFPFC_MODIFY,
                                instructions=instructionList)
        datapath.send_msg(mod)

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

    @set_ev_cls(ofp_event.EventOFPBarrierReply, [CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def barrier_reply_handler(self, ev):
        print('OFPBarrierReply received') 
