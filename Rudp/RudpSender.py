'''
Created on May 10, 2013

@author: Saulius Alisauskas
'''

import Rudp
import Event
import sys
import ntpath
import time
from vsftp import VsPacket

UDP_IP = "127.0.0.1"
UDP_PORT = 0
UPD_DESTINATION = 5005

class FileSender:
    timeStarted = Event.getCurrentMills()
    
    def __init__(self, fileName, addresses):
        self.fileName = fileName
        self.addresses = addresses
        self.packetcount = 0
        
    def send(self):
        self.rudpSocket = Rudp.createSocket(UDP_PORT)
        Rudp.registerEventHandler(self.rudpSocket, fileSender.handleEvent)
        
        for desination in self.addresses:
            self.rudpSocket.addPeer(desination)
        
        fileToSend = open(self.fileName)
        Event.eventFd(fileToSend.fileno(), self.handleFileDataAvailable, fileToSend, "FileDataAvailable")
        print "Openned fileToSend DF:" + str(fileToSend.fileno()) + " name: " + str(self.fileName)        
        
        ''' Send BEGIN packet'''
        vsFtpPacket = VsPacket()
        vsFtpPacket.type = VsPacket.TYPE_BEGIN
        vsFtpPacket.data = FileSender.processFileName(self.fileName)
        if self.rudpSocket.sendToAll(vsFtpPacket.pack()) == False:
            print "Transmission error, quiting"
            sys.exit()
        
    def handleFileDataAvailable(self, fd, fileToSend):      
        data = fileToSend.read(800)
        if data:
            vsFtpPacket = VsPacket()
            vsFtpPacket.type = VsPacket.TYPE_DATA
            vsFtpPacket.data = data
            if self.rudpSocket.sendToAll(vsFtpPacket.pack()) == False:
                print "Transmission error, quiting"
                sys.exit()   
            self.packetcount  = self.packetcount + 1
            print "### " + str(self.packetcount)
            #time.sleep(0)
        else:
            ''' Send END packet'''
            vsFtpPacket = VsPacket()
            vsFtpPacket.type = VsPacket.TYPE_END
            vsFtpPacket.data = data
            if self.rudpSocket.sendToAll(vsFtpPacket.pack()) == False:
                print "Transmission error, quiting"
            Event.eventFdDelete(self.handleFileDataAvailable, fileToSend)
            print "File " + self.fileName + " sent"
            Rudp.closeSocket(self.rudpSocket)
            
    def handleEvent(self, rudpSocket, eventType):
        if eventType == Event.TYPE_TIMEOUT:
            sys.exit("TimeOut event received")
        if eventType == Event.TYPE_CLOSED:
            print "Socket closed event received on " + str(rudpSocket)
            print "Lost Packets:" + str(rudpSocket.packetloss)
            print "Sent Data packets:" + str(rudpSocket.packetsSentData)
            print "Sent Control packets:" + str(rudpSocket.packetsSentControl)           
            print "Received packets(total):" + str(rudpSocket.packetsReceived)
            print "Received data packets:" + str(rudpSocket.packetsReceivedData)
            print "Received and skipped packets:" + str(rudpSocket.packetsReceivedIgnored)
            print "Fake loss:" + str(rudpSocket.packetFakeLoss)
            print "Time taken: " + str((Event.getCurrentMills() - self.timeStarted))
            
    @staticmethod
    def processFileName(path):
        head, tail = ntpath.split(path)
        return tail or ntpath.basename(head)
            
if __name__ == '__main__':
    fileSender = FileSender('/home/saulius/testfileBig.ogv', [(UDP_IP, UPD_DESTINATION)])
    fileSender.send()
    #fileSender = FileSender('/home/saulius/testFileSmall2.txt', [(UDP_IP, UPD_DESTINATION)])
    #fileSender.send()
    Event.eventLoop()



        



    
#For unpacking we first need to know the size of the data

#eceivedPacker = RudpPacket().unpack(packet.pack());
#print receivedPacker

#print "Secnum:" + str(receivedPacker.seqnum) + " Data length:" + str(receivedPacker.datalength)
#print "Data:" + receivedPacker.data