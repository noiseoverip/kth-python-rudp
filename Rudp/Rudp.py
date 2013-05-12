'''
Created on May 10, 2013

@author: Saulius Alisauskas
'''
import socket
import struct
import json
import Event
import sys
from random import randint
from Logging import Logger
from Logging import Level

rudpSockets = []
logger = Logger("RUDP", Level.TRACE)

def createSocket(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", port))
    rudpSocket = RudpSocket(sock)
    rudpSocket.addr_src = sock.getsockname()
    rudpSockets.append(rudpSocket)
    Event.eventFd(sock.fileno(), handleDataAvailable, rudpSocket, "DataReceived")
    return rudpSocket

def closeSocket(rudpSocket):
    ''' Called by user application '''
    for rs in rudpSockets:
        if rs == rudpSocket:
            logger.log(Level.INFO, "Closing socket:" + str(rs))           
            rs.close()
            
def socketFinished(rudpSocket):
    ''' Called by child sockets when they finish'''
    Event.eventFdDelete(handleDataAvailable, rudpSocket)
    rudpSockets.remove(rudpSocket)
    rudpSocket.eventHandler(rudpSocket, Event.TYPE_CLOSED)
    
            
def sendToAll(rudpSocket, data, address):
    if rudpSocket.closePending:
        return False
    rudpPacket = RudpPacket()
    rudpPacket.seqnum = 1
    rudpPacket.data = data
    rudpSocket.socket.sendto(rudpPacket.pack(), address)
    #TODO: register timeout
    pass

def registerReceiveHandler(rudpSocket, handler):
    rudpSocket.receiveHandler = handler
    pass

def registerEventHandler(rudpSocket, handler):
    rudpSocket.eventHandler = handler
    pass

def handleDataAvailable(fd, rudpSocket):
    #print "Received data on fd:" + str(fd)
    #TODO: read data from rudpSocket
    for rs in rudpSockets:
        if rs == rudpSocket:
            rudpSocket.receive()


class RudpSocket:
    ''' Socket session states'''
    STATE_CLOSED = 1
    STATE_LISTEN = 2
    STATE_INITING = 3
    STATE_ESTABLISHED = 4
    PARAM_MAX_DATA_LENGH = 1000
    PARAM_TIMEOUT = 50 # in milliseconds
    PARAM_WINDOWS_SIZE_MAX = 3  
    PARAM_RETIRES_MAX = 150
    FAKE_LOSS = 1 # In scale 1-10, where 10 = 100% loss
    packetloss = 0
    packetsSentData = 0
    packetsSentControl = 0
    packetsReceived = 0
    packetsReceivedData = 0
    packetsReceivedIgnored = 0
    packetFakeLoss = 0
    
    def registerPacketLoss(self):
        self.packetloss = self.packetloss + 1
    def registerDataPacketSent(self):
        self.packetsSentData = self.packetsSentData + 1
    def registerControlPacketSent(self):
        self.packetsSentControl = self.packetsSentControl + 1
    def registerPacketReceived(self):
        self.packetsReceived = self.packetsReceived + 1
    def registerPacketReceivedData(self):
        self.packetsReceivedData = self.packetsReceivedData + 1
    def registerPacketReceivedIgnored(self):
        self.packetsReceivedIgnored = self.packetsReceivedIgnored + 1
    def registerFakeLoss(self):
        self.packetFakeLoss = self.packetFakeLoss + 1
    
    def __init__(self, socket):
        self.socket = socket
        self.receiveHandler = None
        self.eventHandler = None        
        self.peers = [] #List of peers that we initiated connections to
        self.senders = [] #List of peers that initiated connection towards us
        self.addr_src = None
        self.closePending = False
        self.closed = False  
    def __str__(self): # Override string representation
        return "RUDP socket:" + str(self.__dict__)
    
    def __eq__(self, other): 
        return self.socket.fileno() == other.socket.fileno()
    
    def close(self):
        ''' Called by RUDP container instructing to close this RUDP socket'''
        self.closePending = True
        ''' Order close all sending peer sessions'''
        for peer in self.peers:
            if peer.finished is not True:
                peer.close()
    
    def _peerFinished(self):
        ''' Called by sending peer after receiving ACK for FIN'''
        allfinished = True
        for peer in self.peers:
            allfinished = allfinished & peer.finished
        if allfinished is True:
            logger.log(Level.INFO, "All peers finished for socket:" + str(self))
            self.close = True
            socketFinished(self)            
         
    def sendToAll(self, data):
        ''' Send data to all peers '''
        result = True
        for peer in self.peers:
            result & peer.sendToAll(data)
        return result
    
    def addPeer(self, address):
        peer = RudpSocketPeer(address)
        peer.rudpSocket = self
        self.peers.append(peer)
        return peer
    
    def sendPacketControl(self, address, rudpPacket):
        if self.closed:
            logger.log(Level.ERROR, "Tried to send on a close socket");
            return False
        self.socket.sendto(rudpPacket.pack(), address)
        logger.log(Level.TRACE, "")
        logger.log(Level.TRACE, ">>" + str(rudpPacket))
        self.registerControlPacketSent()
        return True
    
    def sendPacketData(self, address, rudpPacket):
        if self.closed:
            logger.log(Level.ERROR, "Tried to send on a close socket");
            return False
        self.socket.sendto(rudpPacket.pack(), address)
        logger.log(Level.TRACE, "")
        logger.log(Level.TRACE, ">>" + str(rudpPacket))
        self.registerDataPacketSent()
        return True
    
    def findOrCreateSenderPeer(self, address, createNew):
        for sender in self.senders:
            if sender.addr == address:
                return sender
        ''' Create new sender '''
        if createNew:            
            sender = RudpSocketPeer(address)
            self.senders.append(sender)
            return sender
        return None
            
    def receive(self):
        #print "Reading from rudpSocket"
        self.registerPacketReceived()
        data, addr = self.socket.recvfrom(1024) # set buffer size
        rudpPacket = RudpPacket().unpack(data)
        logger.log(Level.TRACE, "")
        logger.log(Level.TRACE, "<<" + str(rudpPacket))
        
        ''' Simulate packet loss '''
        if self.FAKE_LOSS > 0 and randint(1,10 / self.FAKE_LOSS) == 1:
            self.registerFakeLoss()
            logger.log(Level.DEBUG, "LOOSING PACKET!!!!!!!!!!!!!!")
            logger.log(Level.DEBUG, "LOOSING PACKET!!!!!!!!!!!!!!")
            logger.log(Level.DEBUG, "LOOSING PACKET!!!!!!!!!!!!!!")
            return
              
        ''' Find sender or '''
        sender = self.findOrCreateSenderPeer(addr, True)
        
        if rudpPacket.type == RudpPacket.TYPE_SYN:
            ''' Receiving side only'''
            
            if sender.state == RudpSocket.STATE_LISTEN:
                logger.log(Level.DEBUG, "Got SYN, sending ACK to " + str(addr) + " " + str(self))
                packet = RudpPacket()
                packet.type = RudpPacket.TYPE_ACK
                packet.seqnum = rudpPacket.seqnum + 1
                self.sendPacketControl(addr, packet)  
                sender.state = RudpSocket.STATE_ESTABLISHED
            else:
                logger.log(Level.ERROR, "Received unexpected packet " + str(self))
                self.registerPacketReceivedIgnored()
                
        elif rudpPacket.type == RudpPacket.TYPE_DATA:
            self.registerPacketReceivedData()
            ''' Receiving side only'''
            if sender.state == RudpSocket.STATE_ESTABLISHED:
                logger.log(Level.DEBUG,str(self) + " received DATA")
                if sender.nextSequenceNumber != rudpPacket.seqnum:
                    logger.log(Level.ERROR, "Packets out of order, was expecting:" + str(sender.nextSequenceNumber))
                    if rudpPacket.seqnum <= sender.nextSequenceNumber:
                        ''' We already got this packet, so we simply ACK it '''
                        logger.log(Level.INFO, "Duplicated packet, sending ACK")
                        packet = RudpPacket()
                        packet.seqnum = rudpPacket.seqnum + 1
                        packet.type = RudpPacket.TYPE_ACK
                        self.sendPacketControl(addr, packet)
                        self.registerPacketReceivedIgnored()
                    return
                
                self.receiveHandler(self, addr, rudpPacket.data)
                sender.nextSequenceNumber = rudpPacket.seqnum + 1
                packet = RudpPacket()
                packet.seqnum = sender.nextSequenceNumber
                packet.type = RudpPacket.TYPE_ACK
                self.sendPacketControl(addr, packet)
            else:
                logger.log(Level.ERROR, "ERROR session not ESTAB " + str(self) + " " + str(rudpPacket))
                self.registerPacketReceivedIgnored()
        
        elif rudpPacket.type == RudpPacket.TYPE_ACK:
            for peer in self.peers:
                if peer.addr == addr:
                    peer.handleACK(rudpPacket)
            pass
       
        elif rudpPacket.type == RudpPacket.TYPE_FIN:
            if sender.state == RudpSocket.STATE_ESTABLISHED or sender.state == RudpSocket.STATE_CLOSED:
                if rudpPacket.seqnum == sender.nextSequenceNumber:
                    logger.log(Level.DEBUG, "Received FIN, sending ACK and closing socket")
                    packet = RudpPacket()
                    packet.seqnum = sender.nextSequenceNumber + 1
                    packet.type = RudpPacket.TYPE_ACK
                    self.sendPacketControl(addr, packet)                    
                    sender.state = RudpSocket.STATE_CLOSED
                else:
                    logger.log(Level.ERROR, "FIN packet wrong seq")
                    self.registerPacketReceivedIgnored()
            else:
                logger.log(Level.ERROR, "Received FIN while not in STATE_ESTABLISHED")
                self.registerPacketReceivedIgnored()
            pass   
        pass
    
    def generateSynPacket(self):       
        packet = RudpPacket()
        packet.type = RudpPacket.TYPE_SYN
        packet.seqnum = randint(100,1000)
        return packet
        

class RudpSocketPeer:
    ''' Class for holding related socket information for each of the peers'''
    def __init__(self, address):
        self.nextSequenceNumber = 0
        self.nextPacketIndex = 0
        self.seqNumberAckNext = 1
        self.addr = address
        self.state = RudpSocket.STATE_LISTEN #Should be socket scope only
        self.window = 3
        self.retries = 0
        self.dataBuffer = []
        self.rudpSocket = None
        self.finished = False
        self.closePending = False
    def __str__(self):
        return "Peer " + str(self.addr) + " state:" + str(self.state) + " src:" + str(self.rudpSocket.addr_src)
        
    def sendToAll(self, data):        
        if self.state == RudpSocket.STATE_LISTEN:
            print str(self) + " not ESTABLISHED, sending SYN"
            packet = self.rudpSocket.generateSynPacket()
            self.seqNumberAckNext = packet.seqnum  + 1
            self.rudpSocket.sendPacketControl(self.addr, packet)
            self.state = RudpSocket.STATE_INITING
            Event.eventTimeout(RudpSocket.PARAM_TIMEOUT, self.__handleTimeoutSYN, packet.seqnum, "SYN timeout")
        elif self.state == RudpSocket.STATE_INITING:
            logger.log(Level.DEBUG, str(self) + " STATE_INITING, adding data to buffer")    
        elif self.state == RudpSocket.STATE_ESTABLISHED:
            logger.log(Level.DEBUG, str(self) + " STATE_ESTABLISHED, adding data to buffer")   
        elif self.state == RudpSocket.STATE_CLOSED:
            logger.log(Level.ERROR, str(self) + " STATE_CLOSED, adding data to buffer")   
            return False
        # Build packet and add to buffer
        packet = RudpPacket()
        packet.type = RudpPacket.TYPE_DATA
        packet.data = data
        packet.seqnum = self.nextSequenceNumber        
        self.dataBuffer.append(packet)
        self.nextSequenceNumber = self.nextSequenceNumber + 1
        logger.log(Level.TRACE, "Buffer has packets:" + str(len(self.dataBuffer)))
        return True
    def __handleTimeoutSYN(self, packetSequenceNumber):
        logger.log(Level.DEBUG, "Handling SYN timeout of:" + str(packetSequenceNumber))
        Event.eventTimeoutDelete(self.__handleTimeoutSYN, packetSequenceNumber)
        if self.__incrementRetries():
            packet = self.rudpSocket.generateSynPacket()
            self.seqNumberAckNext = packet.seqnum + 1
            logger.log(Level.INFO, "Retransmitting SYN")
            self.rudpSocket.sendPacketControl(self.addr, packet)
            Event.eventTimeout(RudpSocket.PARAM_TIMEOUT, self.__handleTimeoutSYN, packet.seqnum, "SYN timeout")
    def __handleTimeoutFIN(self, packetSequenceNumber):
        logger.log(Level.DEBUG, "Handling FIN timeout of:" + str(packetSequenceNumber))
        if self.__incrementRetries():
            Event.eventTimeoutDelete(self.__handleTimeoutFIN, packetSequenceNumber)
            packet = RudpPacket()
            packet.type = RudpPacket.TYPE_FIN
            packet.seqnum = packetSequenceNumber
            self.rudpSocket.sendPacketControl(self.addr, packet)
            Event.eventTimeout(RudpSocket.PARAM_TIMEOUT, self.__handleTimeoutFIN, packet.seqnum, "DATA Timeout")    
    def __handleTimeoutData(self, rudpSecNum):
        logger.log(Level.DEBUG, "Handling packet timeout DATA packet seq:" + str(rudpSecNum))
        ''' Here we need to remove all other DATA packet timeouts'''
        for seq in range(rudpSecNum, self.nextPacketIndex):            
            Event.eventTimeoutDelete(self.__handleTimeoutData, seq)
        if self.__incrementRetries():
            ''' Decrease window size, reset packet index to the one we lost'''
            self.window = 1 if self.window - 1 < 1 else self.window - 1
            self.nextPacketIndex = rudpSecNum
            self.__emptyBuffer()
            self.retries = self.retries + 1  
    
    def close(self):
        ''' Order to close the socket'''
        self.closePending = True
        self.__checkClose()
        
    def __checkClose(self):
        ''' Send FIN if all packet have been sent'''
        if self.closePending is True:
            if len(self.dataBuffer) < self.seqNumberAckNext:
                logger.log(Level.DEBUG, "Closing peer socket:" + str(self))
                packet = RudpPacket()
                packet.type = RudpPacket.TYPE_FIN
                packet.seqnum = self.dataBuffer[self.nextPacketIndex - 1].seqnum + 1
                self.rudpSocket.sendPacketControl(self.addr, packet)
                Event.eventTimeout(RudpSocket.PARAM_TIMEOUT, self.__handleTimeoutFIN, packet.seqnum, "DATA Timeout")
                self.state = RudpSocket.STATE_CLOSED
                self.finished = True
                
            else:
                logger.log(Level.DEBUG, "Could not close peer socket yet !!!!")
    def handleACK(self, ackPacket):
        if ackPacket.seqnum != self.seqNumberAckNext:
                logger.log(Level.ERROR, "ACK with wrong sequence number, probably arrived too late, ignoring")
                return
           
        if self.state == RudpSocket.STATE_INITING:
            ''' Must be ACK in response to SYN'''
            logger.log(Level.DEBUG, "Handling ACK for SYN")
           
            self.state = RudpSocket.STATE_ESTABLISHED
            self.seqNumberAckNext = 1
            Event.eventTimeoutDelete(self.__handleTimeoutSYN, ackPacket.seqnum - 1)            
            self.__emptyBuffer()
            self.__resetRetries()          
        elif self.state == RudpSocket.STATE_ESTABLISHED:
            ''' Must be ACK in response to DATA'''
            logger.log(Level.DEBUG, "Handling ACK for DATA")            
            logger.log(Level.DEBUG, "ACK CORRECT")
            Event.eventTimeoutDelete(self.__handleTimeoutData, ackPacket.seqnum - 1)
            self.seqNumberAckNext = ackPacket.seqnum + 1
            self.window = self.window + 1
            self.__emptyBuffer()
            self.__resetRetries()            
            self.__checkClose() 
        elif self.state == RudpSocket.STATE_CLOSED:
            ''' This must be the final ack'''
            logger.log(Level.DEBUG, "Final ACK received:" + str(self.rudpSocket))
            Event.eventTimeoutDelete(self.__handleTimeoutFIN, ackPacket.seqnum - 1)
            self.rudpSocket._peerFinished()
            
                
    def __emptyBuffer(self):
        logger.log(Level.TRACE, "Sending packets, window:" +  str(self.window) + " index:" + str(self.nextPacketIndex))
        if len(self.dataBuffer) > self.nextPacketIndex:
            while self.window > 0 and len(self.dataBuffer) > 0 and len(self.dataBuffer) > self.nextPacketIndex:            
                packet = self.dataBuffer[self.nextPacketIndex]
                self.rudpSocket.sendPacketData(self.addr, packet)
                self.nextPacketIndex = self.nextPacketIndex + 1
                self.window = self.window - 1
                Event.eventTimeout(RudpSocket.PARAM_TIMEOUT, self.__handleTimeoutData, packet.seqnum, "DATA Timeout")
    
    def __incrementRetries(self):
        self.retries = self.retries + 1
        self.rudpSocket.registerPacketLoss() 
        if self.retries > RudpSocket.PARAM_RETIRES_MAX:
            logger.log(Level.ERROR, "Maximum number of " + str(RudpSocket.PARAM_RETIRES_MAX) + " retries reached")
            self.rudpSocket.eventHandler(self.rudpSocket, Event.TYPE_TIMEOUT)
            self.finished = True
            self.rudpSocket.close()
            return False        
        return True
        
    
    def __resetRetries(self):
        self.retries = 0
            
class RudpPacket:
    """ RUDP packet class"""    
    TYPE_DATA = 1
    TYPE_SYN = 2
    TYPE_ACK  = 4
    TYPE_FIN  = 5
    
    #
    # Feilds:
    # vesion:
    # length
    # sequence number
    #
    #
    def __init__(self):
        self.version = 1
        self.type = None     
        self.seqnum = 0        
        self.datalength = None
        self.data = None       
        
    def pack(self):
        data = bytes(self.data)
        if self.data is None:
            self.datalength = 0
        else:
            self.datalength = len(data)
        return struct.pack("IIII%ds" % (len(data),), self.version, self.type, self.seqnum, self.datalength, data)
    
    def unpack(self, data):
        self.version, self.type, self.seqnum, self.datalength = struct.unpack("IIII", data[:16])
        if self.datalength > 0:       
            (self.data,) = struct.unpack("%ds" % (self.datalength,), data[16:])        
        return self
    def __str__(self): # Override string representation
        return "RudpPacket " + str(self.__dict__)