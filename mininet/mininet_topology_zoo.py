from mininet.net import Mininet
from mininet.node import Controller, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import Link, Intf, TCLink
from mininet.topo import Topo
from mininet.util import dumpNodeConnections
import logging
import os

class Mininet_topology_zoo(Mininet):
    '''
    construct the topology in mininet from topology zoo
    http://www.topology-zoo.org/
    every switch has only one host.
    '''
    all_switches = []
    all_links = []
    longitude = []
    latitude = []

    def __init__(self, *args, **kwargs):
        # Read topology info
        name = 'Easynet'
        path = "/home/enfyshsu/topo_zoo/" + name + ".gml"
        file = open(path, "r")
        self.all_switches, self.all_links = self.handler(file)
        # Add default members to class
        super(Mininet_topology_zoo, self).__init__(*args, **kwargs)
        # Create switches and hosts
        self._addSwitches(self.all_switches)
        self._addLinks(self.all_switches, self.all_links)

    def handler(self,file):
        switches = []
        links = []
        for line in file:
            if line.startswith("    id "):
                token = line.split("\n")
                token = token[0].split(" ")
                line = line[7:]
                if not line.startswith("\""):
                    token = line.split("\n")
                    switches.append(int(token[0]) + 1)
                    curr = int(token[0])
                    self.longitude.append(0)
                    self.latitude.append(0)
                    curr += 1
            if "Longitude" in line:
                token = line.split()
                self.longitude[curr - 1] = float(token[1])
            if "Latitude" in line:
                token = line.split()
                self.latitude[curr - 1] = float(token[1])
            if line.startswith("    source"):
                token = line.split("\n")
                token = token[0].split(" ")
                sw1 = int(token[-1])+1
            if line.startswith("    target"):
                token = line.split("\n")
                token = token[0].split(" ")
                sw2 = int(token[-1])+1
                print(sw1, sw2)
                links.append((sw1,sw2))
        print(switches,len(self.longitude),len(self.latitude))
        return switches, links

    def _addSwitches(self,switches):
        for s in switches:
            print(s)
            #self.addSwitch('s%d' %s, annotations={"latitude": self.latitude[s - 1], 'longitude': self.longitude[s-1]})
            self.addSwitch('s%d' %s)
            
            h = hex(s).split('x')[-1]
            if len(h) == 1:
                h = '0' + h

            mac = "00:00:00:00:00:%s" % (h)    
            self.addHost('h%d'  %s, mac=mac)

    def _addLinks(self,switches,links):
        for s in switches:
            self.addLink("h%s" %s, "s%s" %s, 0)
        for dpid1, dpid2 in links:
            self.addLink(node1="s%s" %dpid1, node2="s%s" %dpid2)

topos = {'mytopo':(lambda :Mininet_topology_zoo("Easynet"))}

def main():
    "Create and test a simple network"
    #topo = Mininet_topology_zoo("Easynet")
    net = Mininet_topology_zoo(topo=None, controller=None)
    net.addController(name='c0', controller = RemoteController)

    net.start()
    h1 = net.get('h1')
    h1.cmd('arp -s 10.0.0.11 00:00:00:00:00:0b')

    h11 = net.get('h11')
    h11.cmd('arp -s 10.0.0.1 00:00:00:00:00:01')

    h2 = net.get('h2')
    h2.cmd('arp -s 10.0.0.16 00:00:00:00:00:10')
    #h2.cmd('iperf3 -s &')
    h16 = net.get('h16')
    h16.cmd('arp -s 10.0.0.2 00:00:00:00:00:02')
    #h16.cmd('iperf3 -s &')
    
    h4 = net.get('h4')
    h4.cmd('arp -s 10.0.0.18 00:00:00:00:00:12')
    h18 = net.get('h18')
    h18.cmd('arp -s 10.0.0.4 00:00:00:00:00:04')
    
    h2 = net.get('h2')
    h2.cmd('arp -s 10.0.0.13 00:00:00:00:00:0d')
    h2.cmd('iperf3 -s &')
    h13 = net.get('h13')
    h13.cmd('arp -s 10.0.0.2 00:00:00:00:00:02')
    h13.cmd('iperf3 -s &')
    #dumpNodeConnections(net.hosts)
    #net.pingAll()
    CLI(net)
    net.stop()

if __name__ == "__main__":
    setLogLevel('info')
    main()
