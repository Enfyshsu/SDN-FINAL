import sys
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd 

# Packet Arrival Rate 
def diff_packet_rate(title, x_name, y_name, flow_id):
    if flow_id == 0:
        data=[[1,8,0],[2,15,0],[3,24,0],[4,31,0],[5,39,0]]
    elif flow_id == 1:
        data=[[1,6,0],[2,11,0],[3,18,0],[4,23,0],[5,30,0]]
    elif flow_id == 2:
        data=[[1,4,0],[2,8,0],[3,12,0],[4,15,0],[5,19,0]]
    
    df=pd.DataFrame(data,columns=["rate","baseline","IMU"])
    df.plot(x="rate", y=["baseline", "IMU"], kind="bar")
    plt.xticks(rotation=0)
    plt.yticks([0,10,20,30,40])
    plt.title(title)
    plt.xlabel(x_name)
    plt.ylabel(y_name)
    plt.legend(loc='upper left')
    plt.savefig(str(flow_id)+"_diff_packet_rate."+pictype, bbox_inches='tight', dpi=600, pad_inches=0.1, transparent=True)

def diff_rtt(title, x_name, y_name, flow_id):
    if flow_id == 0:
        data=[[1,20,0],[2,39,0],[3,58,0],[4,78,0],[5,97,0]]
    elif flow_id == 1:
        data=[[1,15,0],[2,29,0],[3,44,0],[4,58,0],[5,73,0]]
    elif flow_id == 2:
        data=[[1,10,0],[2,20,0],[3,29,0],[4,39,0],[5,48,0]]
    
    df=pd.DataFrame(data,columns=["delay (ms)","baseline","IMU"])
    
    df.plot(x="delay (ms)", y=["baseline", "IMU"], kind="bar")
    plt.xticks(rotation=0)
    plt.yticks([0,20,40,60,80,100])
    plt.title(title)
    plt.xlabel(x_name)
    plt.ylabel(y_name)
    plt.legend(loc='upper left')
    plt.savefig(str(flow_id)+"_diff_rtt."+pictype, bbox_inches='tight', dpi=600, pad_inches=0.1, transparent=True)

if __name__ == '__main__':
    pictype = "pdf"
    for flow_id in range(3):
        for pic_type in range (2):
            if pic_type == 0:
                diff_packet_rate("Flow"+str(flow_id), "Packet Arrival Rate (number/ms)", "Dropped Packet Number", flow_id)
            elif pic_type == 1:
                diff_rtt("Flow"+str(flow_id), "Link Delay", "Dropped Packet Number", flow_id)