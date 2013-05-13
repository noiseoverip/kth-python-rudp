'''
Created on May 12, 2013

@author: saulius
'''
from datetime import datetime

class Logger:
    file = None
    
    @staticmethod
    def setFile(filename):
        Logger.file = open(filename,'w')
    
    def __init__(self, loggerName, level):
        self.loggerName = loggerName
        self.level = level
            
    def log(self, messageLevel, message):
        if self.level >= messageLevel:                
            time = datetime.now()
            if messageLevel == Level.INFO:
                self._print(time, "INFO", message)
            elif messageLevel == Level.DEBUG:
                self._print(time, "DEBUG", message)
            elif messageLevel == Level.TRACE:
                self._print(time, "TRACE", message)
            elif messageLevel == Level.ERROR:
                self._print(time, "ERROR", message)
                
    def _print(self, time, level, message):
        formatedMessage = str(time) + " " + self.loggerName + " " + level + " " + message
        print formatedMessage
        if Logger.file is not None:
            Logger.file.write(formatedMessage + "\n")
        
class Level:
    ERROR = 0
    INFO = 1
    DEBUG = 2
    TRACE = 3