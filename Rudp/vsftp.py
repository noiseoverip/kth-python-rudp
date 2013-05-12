'''
Created on May 12, 2013

@author: saulius
'''
import struct

class VsPacket:
    TYPE_BEGIN = 1
    TYPE_DATA = 2
    TYPE_END = 3
    
    def __init__(self):
        self.type = None
        self.data = ""
      
    def pack(self):
        data = bytes(self.data)
        if self.data is None:
            self.datalength = 0
        else:
            self.datalength = len(data)
        return struct.pack("I%ds" % (self.datalength,), self.type, self.data)
    
    def unpack(self, data):
        self.type, = struct.unpack("I", data[:4])
        if self.type == self.TYPE_BEGIN or self.type == self.TYPE_DATA:       
            (self.data,) = struct.unpack("%ds" % (len(data) - 4,), data[4:])        
        return self
    
    def __str__(self): # Override string representation
        return "VsPacket type:" + str(self.type) + " datasize:" + str(len(self.data))
