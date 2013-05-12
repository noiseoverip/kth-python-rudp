'''
Created on May 12, 2013

@author: saulius
'''
class Logger:
    
    def __init__(self, loggerName, level):
        self.loggerName = loggerName
        self.level = level
    
    def log(self, messageLevel, message):
        if self.level >= messageLevel:
            if messageLevel == Level.INFO:
                print self.loggerName + " INFO " + message
            elif messageLevel == Level.DEBUG:
                print self.loggerName + " DEBUG " + message
            elif messageLevel == Level.TRACE:
                print self.loggerName + " TRACE " + message
            elif messageLevel == Level.ERROR:
                print self.loggerName + " ERROR " + message
            
class Level:
    ERROR = 0
    INFO = 1
    DEBUG = 2
    TRACE = 3