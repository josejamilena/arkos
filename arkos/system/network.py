import fcntl
import netifaces
import os
import psutil
import socket
import struct
import sys

from arkos import signals
from arkos.utilities import shell, netmask_to_cidr


class Connection:
    def __init__(self, id="", connected=False, enabled=False, config={}):
        self.id = id
        self.connected = connected
        self.enabled = enabled
        self.config = config
    
    def add(self):
        signals.emit("networks", "pre_add", self)
        with open(os.path.join("/etc/netctl", self.id), "w") as f:
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
            if self.config.get("addressing"):
                f.write('IP=\'' + self.config["addressing"] + '\'\n')
            if self.config.get("address") and self.config.get("addressing") == 'static':
                f.write('Address=(\'' + self.config["address"] + '\')\n')
            if self.config.get("gateway") and self.config.get("addressing") == 'static':
                f.write('Gateway=\'' + self.config["gateway"] + '\'\n')
            if self.config.get("key") and self.config.get("connection") == 'wireless':
                f.write('Key=\"' + self.config["key"] + '\"\n')
        signals.emit("networks", "post_add", self)

    def update(self):
        connected = self.connected
        if connected:
            self.disconnect()
        self.add()
        if connected:
            self.connect()
    
    def remove(self):
        signals.emit("networks", "pre_remove", self)
        if os.path.exists(os.path.join("/etc/netctl", self.id)):
            os.unlink(os.path.join("/etc/netctl", self.id))
        signals.emit("networks", "post_remove", self)
    
    def connect(self):
        signals.emit("networks", "pre_connect", self)
        for x in get_connections(iface=self.config.get("interface")):
            x.disconnect()
        s = shell('netctl start %s' % self.id)
        if s["code"] == 0:
            self.connected = True
            signals.emit("networks", "post_connect", self)
        else:
            raise Exception("Network connection failed")
    
    def disconnect(self):
        signals.emit("networks", "pre_disconnect", self)
        s = shell('netctl stop %s' % self.id)
        if s["code"] == 0:
            self.connected = False
            signals.emit("networks", "post_disconnect", self)
        else:
            raise Exception("Network disconnection failed")
    
    def toggle(self):
        if self.connected:
            self.disconnect()
        else:
            self.connect()
    
    def enable(self):
        s = shell('netctl enable %s' % self.id)
        if s["code"] == 0:
            self.enabled = True
        else:
            raise Exception("Network enable failed")
    
    def disable(self):
        s = shell('netctl disable %s' % self.id)
        if s["code"] == 0:
            self.enabled = False
        else:
            raise Exception("Network disable failed")
    
    def as_dict(self):
        return {
            "id": self.id,
            "connected": self.connected,
            "enabled": self.enabled,
            "config": self.config,
            "is_ready": True
        }


class Interface:
    def __init__(self, id="", itype="", up=False, ip=[], rx=0, tx=0):
        self.id = id
        self.itype = itype
        self.up = up
        self.ip = ip
        self.rx = rx
        self.tx = tx

    def bring_up(self):
        shell('ip link set dev %s up' % self.id)

    def bring_down(self):
        shell('ip link set dev %s down' % self.id)
    
    def enable(self):
        shell('systemctl enable netctl-auto@%s.service' % self.id)
    
    def disable(self):
        shell('systemctl disable netctl-auto@%s.service' % self.id)
    
    def as_dict(self):
        return {
            "id": self.id,
            "type": self.itype,
            "up": self.up,
            "ip": self.ip,
            "rx": self.rx,
            "tx": self.tx
        }


def get_connections(id=None, iface=None):
    conns = []
    netctl = shell('netctl list')
    for line in netctl["stdout"].split('\n'):
        if not line.split():
            continue
        c = Connection(id=line[2:], connected=line.startswith("*"),
            enabled=os.path.exists('/etc/systemd/system/multi-user.target.wants/netctl@'+line[2:]+'.service'))
        with open(os.path.join('/etc/netctl', c.id), "r") as f:
            data = f.readlines()
        for x in data:
            if x.startswith('#') or not x.strip():
                continue
            parse = x.split('=')
            c.config[parse[0].lower()] = parse[1].translate(None, '()\"\'\n')
        if id == c.id:
            return c
        if not iface or c.config.get("interface") == iface:
            conns.append(c)
    return conns if not id else None

def get_interfaces(id=None):
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
        i = Interface(id=x, itype=itype)
        data = psutil.net_io_counters(pernic=True)
        data = data[x] if type(data) == dict else data
        i.rx, i.tx = data[0], data[1]
        i.ip = netifaces.ifaddresses(i.id)[netifaces.AF_INET]
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        r = fcntl.ioctl(s.fileno(), 0x8913, i.id + ("\0"*256))
        flags, = struct.unpack("H", r[16:18])
        up = flags & 1
        s.close()
        i.up = up == 1
        if id == i.id:
            return i
        ifaces.append(i)
    return ifaces if not id else None

def get_active_ranges():
    ranges = []
    for x in get_interfaces():
        for y in x.ip:
            if '127.0.0.1' in y["addr"] or '0.0.0.0' in y["addr"]:
                continue
            ri = y["addr"].split('.')
            ri[3] = '0'
            ri = ".".join(ri)
            y = ri + '/' + str(netmask_to_cidr(y["netmask"]))
            ranges.append(y)
    return ranges
