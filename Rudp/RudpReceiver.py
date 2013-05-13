'''
Created on May 10, 2013

@author: Saulius Alisauskas
'''
import Rudp
import Event
from vsftp import VsPacket
import time
import sys
import Logging

def getCurrentMills():
    return int(round(time.time() * 1000))

class Receiver:
    files = []
    def __init__(self, host, port):
        self.port = port
        self.host = host
    
    def start(self):
        self.rudpSocket = Rudp.createSocket(self.host, self.port)
        Rudp.registerReceiveHandler(self.rudpSocket, self.receiveHandler)
        print "Started Receiver on  " + str(self.rudpSocket.socket.getsockname())
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
            
            filename = packet.data
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

if __name__ == '__main__':
    Logging.Logger.setFile("receiver.log") # Set file for log messages
    if len(sys.argv)  < 2:
        print "Please provide port number, ex: python RudpReceiver.py 5000"
    else:
        Receiver("0.0.0.0", int(sys.argv[1])).start()   

#while True:
#    data, addr = sock.recvfrom(1024) # set buffer size
#    rudpPacket = RudpPacket().unpack(data)
#    print "Received RUDP packet:" + str(rudpPacket) + " from:" + str(addr)
    