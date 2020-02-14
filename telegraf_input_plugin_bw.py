#!/usr/bin/python3

from apscheduler.schedulers.background import BackgroundScheduler
import socket
import struct
import array
import fcntl
import time
import sys
from pwd import getpwnam  

SIOCGIFFLAGS = 0x8913  # from header /usr/include/bits/ioctls.h
SIOCETHTOOL = 0x8946  # As defined in include/uapi/linux/sockios.h
ETHTOOL_GSET = 0x00000001  # Get status command.


iface = sys.argv[1]

def slurp_file(filename):
    with open(filename, 'r') as f:
        data = f.read()
        return data

def write_out(filename, line):
	MyFile=open(filename,'w')
	MyFile.writelines(line)
	MyFile.close()

def get_tx_count(iface):
    stats_file = "/sys/class/net/{}/statistics/tx_bytes".format(iface)
    return slurp_file(stats_file)
    

def get_rx_count(iface):
    stats_file = "/sys/class/net/{}/statistics/rx_bytes".format(iface)
    return slurp_file(stats_file)



def get_network_interface_speed(sock, interface_name):
    """
    Return the ethernet device's advertised link speed.
    The return value can be one of:
        * 10, 100, 1000, 2500, 10000: The interface speed in Mbps
        * -1: The interface does not support querying for max speed, such as
          virtio devices for instance.
        * 0: The cable is not connected to the interface. We cannot measure
          interface speed, but could if it was plugged in.
    """
    cmd_struct = struct.pack("I39s", ETHTOOL_GSET, b"\x00" * 39)
    status_cmd = array.array("B", cmd_struct)
    packed = struct.pack("16sP", str.encode(interface_name), status_cmd.buffer_info()[0])

    speed = -1
    try:
        fcntl.ioctl(sock, SIOCETHTOOL, packed)  # Status ioctl() call
        res = status_cmd.tobytes()
        speed, duplex = struct.unpack("12xHB28x", res)
    except (IOError, OSError) as e:
        if e.errno == errno.EPERM:
            logging.warn("Could not determine network interface speed, "
                         "operation not permitted.")
        elif e.errno != errno.EOPNOTSUPP and e.errno != errno.EINVAL:
            raise e
        speed = -1
        duplex = False

    # Drivers apparently report speed as 65535 when the link is not available
    # (cable unplugged for example).
    if speed == 65535:
        speed = 0

    # The drivers report "duplex" to be 255 when the information is not
    # available. We'll just assume it's False in that case.
    if duplex == 255:
        duplex = False
    duplex = bool(duplex)

    return speed, duplex


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_IP)
(if_speed, dublex) = get_network_interface_speed(sock, iface)

last_packets_rx = 0
last_packets_tx = 0


first = True
def sensor():
    global last_packets_tx, last_packets_rx, first
    packets_tx = get_rx_count(iface)
    packets_rx = get_tx_count(iface)
    

    bw_rx = int(packets_rx) - int(last_packets_rx)
    bw_tx = int(packets_tx) - int(last_packets_tx)

    bw_rx_percent = (bw_rx/(if_speed*131072))*100
    bw_tx_percent = (bw_tx/(if_speed*131072))*100

    timestamp = time.time_ns()
    # net,interface=eth0,host=HOST bytes_sent=451838509i,bytes_recv=3284081640i,packets_sent=2663590i,packets_recv=3585442i,err_in=0i,err_out=0i,drop_in=4i,drop_out=0i 1492834180000000000
    lines = ["custom_net,interface={} bw_tx={}i,bw_tx_percent={},bw_rx_percent={},bw_rx={}i {}\n".format(iface, bw_tx, bw_tx_percent, bw_rx_percent, bw_rx, timestamp)]

    tmp_file="/tmp/telegraf_bandwidth_collector"

    if not first:
        write_out(tmp_file, lines)
    else:
        first = False

    last_packets_rx = packets_rx
    last_packets_tx = packets_tx


sched = BackgroundScheduler(daemon=False)
sched.add_job(sensor,'interval',seconds=1)
sched.start()
