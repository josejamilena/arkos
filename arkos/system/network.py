import fcntl
import netifaces
import os
import psutil
import socket
import struct
import sys

from arkos.utilities import shell


class Connection(object):
    def __init__(self, name="", connected=False, enabled=False, config={}):
        self.name = name
        self.connected = connected
        self.enabled = enabled
        self.config = config
    
    def add(self):
        with open(os.path.join("/etc/netctl", self.name), "w") as f:
            f.write("# automatically generated by arkOS\n")
            if self.config.get("connection"):
                f.write('Connection=\'' + self.config["connection"] + '\'\n')
            if self.config.get("description"):
                f.write('Description=\'' + self.config["description"] + '\'\n')
            if self.config.get("interface"):
                f.write('Interface=\'' + self.config["interface"] + '\'\n')
            if self.config.get("security") and self.config.get("connection") == 'wireless':
                f.write('Security=\'' + self.config["security"] + '\'\n')
            if self.config.get("essid") and self.config.get("connection") == 'wireless':
                f.write('ESSID=\"' + self.config["essid"] + '\"\n')
            if self.config.get("ip"):
                f.write('IP=\'' + self.config["addressing"] + '\'\n')
            if self.config.get("address") and self.config.get("addressing") == 'static':
                f.write('Address=(\'' + self.config["address"] + '\')\n')
            if self.config.get("gateway") and self.config.get("addressing") == 'static':
                f.write('Gateway=\'' + self.config["gateway"] + '\'\n')
            if self.config.get("key") and self.config.get("connection") == 'wireless':
                f.write('Key=\"' + self.config["key"] + '\"\n')

    def update(self):
        self.add()
    
    def remove(self):
        if os.path.exists(os.path.join("/etc/netctl", self.name)):
            os.unlink(os.path.join("/etc/netctl", self.name))
    
    def connect(self):
        shell('netctl start %s' % self.name)
    
    def disconnect(self):
        shell('netctl stop %s' % self.name)
    
    def toggle(self):
        if self.connected:
            self.disconnect()
        else:
            self.connect()
    
    def enable(self):
        shell('netctl enable %s' % self.name)
    
    def disable(self):
        shell('netctl disable %s' % self.name)


class Interface(object):
    def __init__(self, name="", itype="", up=False, ip=[], rx=0, tx=0):
        self.name = name
        self.itype = itype
        self.up = up
        self.ip = ip
        self.rx = rx
        self.tx = tx

    def bring_up(self):
        shell('ip link set dev %s up' % self.name)

    def bring_down(self):
        shell('ip link set dev %s down' % self.name)
    
    def enable(self):
        shell('systemctl enable netctl-auto@%s.service' % self.name)
    
    def disable(self):
        shell('systemctl disable netctl-auto@%s.service' % self.name)


def get_connections(name=None):
    conns = []
    netctl = shell('netctl list')
    for line in netctl["stdout"].split('\n'):
        if not line.split():
            continue
        c = Connection(name=line[2:], connected=line.startswith("*"),
            enabled=os.path.exists('/etc/systemd/system/multi-user.target.wants/netctl@'+line[2:]+'.service'))
        with open(os.path.join('/etc/netctl', c.name), "r") as f:
            data = f.readlines()
        for x in data:
            if x.startswith('#') or not x.strip():
                continue
            parse = x.split('=')
            c.config[parse[0].lower()] = parse[1].translate(None, '()\"\'\n')
        if name == c.name:
            return c
        conns.append(c)
    return conns if not name else None

def get_interfaces(name=None):
    ifaces = []
    for x in netifaces.interfaces():
        if x[:-1] in ['ppp', 'wvdial']:
            itype = 'ppp'
        elif x[:2] in ['wl', 'ra', 'wi', 'at']:
            itype = 'wireless'
        elif x[:2].lower() == 'br':
            itype = 'bridge'
        elif x[:2].lower() == 'tu':
            itype = 'tunnel'
        elif x.lower() == 'lo':
            itype = 'loopback'
        elif x[:2] in ["et", "en"]:
            itype = 'ethernet'
        else:
            itype = "unknown"
        i = Interface(name=x, itype=itype)
        data = psutil.net_io_counters(pernic=True)
        data = data[x] if type(data) == dict else data
        i.rx, i.tx = data[0], data[1]
        i.ip = netifaces.ifaddresses(i.name)[netifaces.AF_INET]
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            r = fcntl.ioctl(s.fileno(), 0x8913, i.name + ("\0"*256))
            flags, = struct.unpack("H", r[16:18])
            up = flags & 1
        i.up = up == 1
        if name == i.name:
            return i
        ifaces.append(i)
    return ifaces if not name else None

def get_active_ranges():
    ranges = []
    for x in get_interfaces():
        for y in x.ip:
            if '127.0.0.1' in y or '0.0.0.0' in y:
                continue
            if not '/' in y:
                ri = y
                rr = '32'
            else:
                ri, rr = y.split('/')
            ri = ri.split('.')
            ri[3] = '0'
            ri = ".".join(ri)
            y = ri + '/' + rr
            ranges.append(y)
    return ranges
