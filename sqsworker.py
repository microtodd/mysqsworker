## simple sqs worker
#
from jsonrpc import JSONRPCResponseManager, dispatcher
import datetime
import boto3
import daemon
import signal
import os
import sys
import importlib
import json
import ConfigParser

__VERSION__ = "0.1"

## SQSConsumer
#  
class SQSConsumer(object):

    ## class vars
    _visibilityTimeout = 1      #
    _waitTimeSeconds = 20       # Long polling by default
    _queuesToCheck = []         #
    _moduleDir = 'modules'      #
    _loadedClasses = {}         # 'moduleName' => Class()
    _testMode = False           #
    _dieFlag = False            #
    _region = 'us-east-1'       #
    
    ## constructor
    #
    def __init__(self,conf=None):

        # Load conf file, if passed
        if conf:
            myConfParser = ConfigParser.ConfigParser()
            try:
                myConfParser.read(conf)

                # Options
                if myConfParser.has_section('main'):
                    for item in myConfParser.items('main'):
                        command = item[0]
                        arg = item[1]
                        if str(command) == 'visibilitytimeout':
                            self._visibilityTimeout = int(arg)
                        elif str(command) == 'waittimeseconds':
                            self._waitTimeSeconds = int(arg)
                        elif str(command) == 'testmode':
                            if str(arg) == 'true':
                                self._testMode = True
                        elif str(command) == 'region':
                            self._region = str(arg)

                # Read queues
                if myConfParser.has_section('queues'):
                    for item in myConfParser.items('main'):
                        command = item[0]
                        arg = item[1]
                        self._queuesToCheck.append(str(arg))

            except Exception as e:
                print >> sys.stderr, str(e)
                sys.exit(1)
        else:
            pass

    ## run
    #
    #
    def run(self):
        
        # Load the workers
        self.loadWorkers()
        
        # Read queue
        if self._testMode:
            self.testQueueRead()
        else:
            
            # Start the work loop
            while not self._dieFlag:
                self.readQueues()
        
    ## loadWorkers
    #  
    #  
    def loadWorkers(self):
    
        # Iterate the workers dir
        # Dynamically load each class (assume classname matches filename)
        # Each class needs a member parameter that is the "method"
        # In the dispatcher dictionary, tie that method to <class>.process( jsonPayload )
        for file in os.listdir(self._moduleDir):
        
            # Only look at py files
            if str(file).endswith('.py'):
            
                # Assume class/module name matches filename
                moduleName, suffix = str(file).split('.')
                
                # Skip the package descriptor
                if moduleName == '__init__':
                    continue
                
                # Import the module (import modules.<modName>)
                thisModule = importlib.import_module(self._moduleDir + '.' + moduleName)
                
                # Grab handle to class (modules.<modName>.<className>)
                thisClass = getattr(thisModule,moduleName)
                
                # Instantiate the class
                self._loadedClasses[moduleName] = thisClass()
                
                # Tie this module/class to the dispatch map
                opcode = self._loadedClasses[moduleName].methodName
                dispatcher[opcode] = self._loadedClasses[moduleName].Processor
                
                if self._testMode:
                    print "Loaded " + file + " class " + thisClass.__class__.__name__ + " with opcode " + str(opcode)

    ## testQueueRead
    #  
    #  
    def testQueueRead(self):
    
        payload = {
            "method": "echo",
            "params": ["echo 1"],
            "jsonrpc": "2.0",
            "id": 0
        }
        print "Test 1:" + str(payload)
        response = JSONRPCResponseManager.handle(json.dumps(payload),dispatcher)
        print "response:" + str(response.json)
        if response.error:
            print "yeah got an error"

        payload = {
            "method": "echo1",
            "params": ["echo 1"],
            "jsonrpc": "2.0",
            "id": 0
        }
        print "Test 2:" + str(payload)
        response = JSONRPCResponseManager.handle(json.dumps(payload),dispatcher)
        print "response:" + str(response.json)
        if response.error:
            print "yeah got an error"

    
    ## readQueues
    #  
    #  
    def readQueues(self):

        # Iterate the queues we should read
        for queueName in self._queuesToCheck:
            thisQueue = None
            try:
                thisQueue = mySqs.get_queue_by_name(QueueName=queueName)
                
                # Poll for messages
                # TODO test this....if MaxNumberOfMessages>1 do I actually get >1?
                myMessages = myQueue.receive_messages(MaxNumberOfMessages=1,WaitTimeSeconds=20,VisibilityTimeout=1,AttributeNames=['SentTimestamp'])
                for message in myMessages:
                
                    # Get the message senttime
                    attr = message.attributes
                    sentTime = datetime.datetime.fromtimestamp(float(attr.get('SentTimestamp'))/1000.0)
                
                    # Send the message to the dispatcher. We assume the body is a json-rpc string.
                    response = JSONRPCResponseManager.handle(str(message.body),dispatcher)
                    
                    # TODO: Log the response, status, and sentTime somewhere
                    
                    # Check for successful response. If message failed then don't delete from queue, [TODO]but keep a retry-counter
                    # for the message ID?
                    if response.error:
                        pass # log the error

                    else:
                        # If no error, then delete the message from the queue
                        message.delete()
                
            except Exception as e:
                print >> sys.stderr, str(e)
                sys.exit(1)

## main
#  
def main():
    
    # Vars
    runAsDaemon = False
    pidFile = '/var/run/worker.pid'
    confFile = '/etc/sqsworker/sqsworker.ini'
    
    # Check command line for options file path
    i = 0
    for arg in sys.argv:
        if str(arg) == '-f':
            confFile = sys.argv[i+1]
        i += 1
    
    # Run as a daemon if asked to
    if runAsDaemon:
    
        # Handle to worker
        messageProcessor = None

        # Signal handlers
        def sig_term(signal_num, stack_frame):
            
            # If a TERM is received, set the die flag
            if messageProcessor:
                messageProcessor._dieFlag = True
    
        # Load pidfile, support multiple versions
        try:
            from daemon import pidlockfile
        except ImportError:
            from daemon import pidfile as pidlockfile
        
        with daemon.DaemonContext(pidfile=pidlockfile.TimeoutPIDLockFile(pidFile, 300), signal_map={signal.SIGTERM : sig_term}):
            try:
                messageProcessor = SQSConsumer(conf=confFile)
                messageProcessor.run()
        
            except Exception as e:
                print >> sys.stderr, str(e)
                sys.exit(1)
    else:
        try:
            messageProcessor = SQSConsumer(conf=confFile)
            messageProcessor.run()
        except Exception as e:
            print >> sys.stderr, str(e)
            sys.exit(1)
    
# Main
if __name__ == "__main__":
    main()
    
