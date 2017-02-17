## simple sqs worker
#
import jsonrpc          # JSONRPCResponseManager, dispatcher
import datetime
import boto3
import daemon
import signal
import os
import sys
import importlib
import json
import ConfigParser
import logging

__VERSION__ = '0.1'

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
    _daemonMode = False         #
    _dieFlag = False            #
    _region = 'us-east-1'       #
    _sqsClient = None           # Handle to the AWS SQS object
    _sqsResource = None
    
    ## constructor
    #
    def __init__(self,conf=None):

        # Load conf file, if passed
        if conf:

            # Ensure file exists
            if not os.path.isfile(conf):
                raise Exception('Conf file ' + str(conf) + ' not found')

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
                        elif str(command) == 'daemonmode':
                            if str(arg) == 'true':
                                self._daemonMode = True
                        elif str(command) == 'region':
                            self._region = str(arg)

                # Read queues
                if myConfParser.has_section('queues'):
                    for item in myConfParser.items('queues'):
                        command = item[0]
                        arg = item[1]
                        self._queuesToCheck.append(str(arg))
                else:
                    logging.warn('No queues found to check in config')

            except Exception as e:
                logging.error('Error loading config file: ' + str(e))
                sys.exit(1)
        else:
            raise Exception('No conf file specified')

    ## Properties

    @property
    def daemonMode(self):
        return self._daemonMode

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

            # Get the AWS handle
            try:
                self._sqsClient = boto3.client('sqs',region_name=self._region)
                self._sqsResource = boto3.resource('sqs',region_name=self._region)

            except Exception as e:
                logging.error('Cannot get AWS SQS handle: ' + str(e))
            
            # Start the work loop
            while not self._dieFlag:
                self.readQueues()

            # signal
            logging.info('SIGTERM received, shutting down')
        
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
                jsonrpc.dispatcher[opcode] = self._loadedClasses[moduleName].Processor
                
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
        print 'Test 1:' + str(payload)
        response = jsonrpc.JSONRPCResponseManager.handle(json.dumps(payload),jsonrpc.dispatcher)
        if not response.error:
            testObj = json.loads(response.json)
            if testObj['result'] == 'echo 1':
                print 'passed'
        payload = {
            "method": "echoTwo",
            "params": ["echo 1","echo 2"],
            "jsonrpc": "2.0",
            "id": 0
        }
        print 'Test 2:' + str(payload)
        response = jsonrpc.JSONRPCResponseManager.handle(json.dumps(payload),jsonrpc.dispatcher)
        if not response.error:
            testObj = json.loads(response.json)
            if testObj['result'] == 'echo 1_echo 2':
                print 'passed'
        payload = {
            "method": "echo1",
            "params": ["echo 1"],
            "jsonrpc": "2.0",
            "id": 0
        }
        print 'Test 3:' + str(payload)
        response = jsonrpc.JSONRPCResponseManager.handle(json.dumps(payload),jsonrpc.dispatcher)
        if response.error:
            print 'passed'
    
    ## readQueues
    #  
    #  
    def readQueues(self):

        # Iterate the queues we should read
        for queueName in self._queuesToCheck:
            try:
                
                # Poll for messages
                myMessages = self._sqsClient.receive_message(QueueUrl=queueName,\
                                                             MaxNumberOfMessages=1,\
                                                             WaitTimeSeconds=self._waitTimeSeconds,\
                                                             VisibilityTimeout=self._visibilityTimeout,\
                                                             AttributeNames=['SentTimestamp'])

                for message in myMessages['Messages']:
                
                    # Get the message metadata
                    rcptHandle = message['ReceiptHandle']
                    attr = message['Attributes']['SentTimestamp']
                    sentTime = datetime.datetime.fromtimestamp(float(attr)/1000.0)
                
                    # Send the message to the dispatcher. We assume the body is a json-rpc string.
                    response = jsonrpc.JSONRPCResponseManager.handle(str(message['Body']),jsonrpc.dispatcher)
                    
                    # Log the response, status, and sentTime somewhere
                    logging.info('Received message at ' + str(sentTime) + ' : ' + str(response))
                    
                    # Check for successful response. If message failed then don't delete from queue, [TODO]but keep a retry-counter
                    # for the message ID?
                    if response.error:
                        logging.warning('Received message failed processing: ' + str(message['Body']) + ' ::: ' + str(response.error))

                    else:
                        # If no error, then delete the message from the queue
                        self._sqsClient.delete_message(QueueUrl=queueName,ReceiptHandle=rcptHandle)
                
            except Exception as e:
                logging.error('Error reading queue: ' + str(e))
                sys.exit(1)

## main
#  
def main():
    
    # Vars
    pidFile = '/var/run/worker.pid'
    confFile = '/etc/sqsworker/sqsworker.ini'
    
    # Check command line for options file path
    i = 0
    for arg in sys.argv:
        if str(arg) == '-f':
            confFile = sys.argv[i+1]
        i += 1
    
    # Handle to worker
    messageProcessor = None
    messageProcessor = SQSConsumer(conf=confFile)

    # Run as a daemon if asked to
    if messageProcessor.daemonMode:
    
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
                messageProcessor.run()
        
            except Exception as e:
                logging.error('Error running as daemon: ' + str(e))
                sys.exit(1)
    else:
        try:
            messageProcessor.run()
        except Exception as e:
            logging.error('Error running in interactive mode: ' + str(e))
            sys.exit(1)
    
# Main
if __name__ == '__main__':
    main()
    
