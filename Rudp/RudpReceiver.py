'''
Created on May 10, 2013

@author: saulius
'''
import Rudp
import Event
from vsftp import VsPacket
import time
import sys

UDP_IP = "127.0.0.1"
UDP_PORT = 5005
WORKSPACE = "/home/saulius/rudpReceive/"

def getCurrentMills():
    return int(round(time.time() * 1000))

class Receiver:
    files = []
    
    def start(self):
        self.rudpSocket = Rudp.createSocket(UDP_PORT)
        Rudp.registerReceiveHandler(self.rudpSocket, self.receiveHandler)
        Event.eventLoop()
        
    def receiveHandler(self, rudpSocket, senderAddress, data):
        packet = VsPacket().unpack(data)
        print ">> " + str(packet)
        
        ''' Get or create file info object'''
        fileInfo = None
        for fInfoTmp in self.files:
            if fInfoTmp.sender == senderAddress:
                fileInfo = fInfoTmp
        if fileInfo is None:
            fileInfo = FileInfo()
            fileInfo.sender = senderAddress
            self.files.append(fileInfo)
        
        ''' Handle different VSFTP pacekt types'''
        if packet.type == VsPacket.TYPE_BEGIN:
            if fileInfo.filename is not None:
                print "File already open !!!!"
                sys.exit(1)
            
            filename = WORKSPACE + packet.data
            print "GOT PACKET BEGIN, openning fileToWrite for writing:" + filename
            fileInfo.filename = filename
            fileInfo.filehandle = open(filename,'w')
            fileInfo.sendStarted = Event.getCurrentMills()  
            pass
        elif packet.type == VsPacket.TYPE_DATA:
            fileInfo.filehandle.write(packet.data)
            pass
        elif packet.type == VsPacket.TYPE_END:
            print "GOT PACKET END, closing file"
            fileInfo.filehandle.close()
            self.files.remove(fileInfo)
            print "Socket closed event received on " + str(rudpSocket)
            print "Lost Packets:" + str(rudpSocket.packetloss)
            print "Sent Data packets:" + str(rudpSocket.packetsSentData)
            print "Sent Control packets:" + str(rudpSocket.packetsSentControl)
            print "Received packets(total):" + str(rudpSocket.packetsReceived)
            print "Received data packets:" + str(rudpSocket.packetsReceivedData)
            print "Received and skipped packets:" + str(rudpSocket.packetsReceivedIgnored)
            print "Fake loss:" + str(rudpSocket.packetFakeLoss)
            print "Time taken: " + str((Event.getCurrentMills() - fileInfo.sendStarted))
    
            pass  
        pass

class FileInfo:
    sender = None
    filename = None
    filehandle = None
    sendStarted = None
    
    
Receiver().start()   


#while True:
#    data, addr = sock.recvfrom(1024) # set buffer size
#    rudpPacket = RudpPacket().unpack(data)
#    print "Received RUDP packet:" + str(rudpPacket) + " from:" + str(addr)
    