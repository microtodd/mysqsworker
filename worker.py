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

__VERSION__ = "0.1"

## SQSConsumer
#  
class SQSConsumer(object):

    ## class vars
    _visibilityTimeout = 1      #
    _waitTimeSeconds = 20       # Long polling by default
    _queuesToCheck = []         #
    _dispatchMap = {}           # Used to map json-rpc methods to the function pointers
    _moduleDir = 'modules'      #
    _loadedClasses = {}         #
    
    ## constructor
    #
    def __init__(self):
        pass

    ## run
    #
    #
    def run(self):
        
        # Load the workers
        self.loadWorkers()
        
        # Read queue
        
    ## loadWorkers
    #  
    #  
    def loadWorkers(self):
    
        # Iterate the workers dir
        # Dynamically load each class (assume classname matches filename)
        # each class needs a member parameter that is the "method"
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
                self._dispatchMap[opcode] = self._loadedClasses[moduleName].Processor
                print "Loaded " + file + " class " + thisClass.__class__.__name__ + " with opcode " + str(opcode)

    ## readQueues
    #  
    #  
    def readQueues(self):
        mySqs = boto3.resource('sqs', region_name='us-east-1')
        print 'all my queues:'
        for queue in mySqs.queues.all():
            print '=> ' + str(queue)

        myQueue = mySqs.get_queue_by_name(QueueName='sqsTest1')
        
        # TODO test this....if MaxNumberOfMessages>1 do I actually get >1?
        myMessages = myQueue.receive_messages(MaxNumberOfMessages=10,WaitTimeSeconds=20,VisibilityTimeout=1,AttributeNames=['All'])
        for message in myMessages:
            print 'body=>'+str(message.body)
            attr = message.attributes
            print 'sent=>'+str(attr.get('SentTimestamp'))
            print datetime.datetime.fromtimestamp(float(attr.get('SentTimestamp'))/1000.0)
            message.delete()
    
## main
#  
def main():
    
    # Vars
    runAsDaemon = False
    pidFile = '/var/run/worker.pid'
    
    # Check command line
    pass # TODO
    
    # Run as a daemon if asked to
    if runAsDaemon:

        # Signal handlers
        def sig_term(signal_num, stack_frame):
            pass

    
        # Load pidfile, support multiple versions
        try:
            from daemon import pidlockfile
        except ImportError:
            from daemon import pidfile as pidlockfile
        
        with daemon.DaemonContext(pidfile=pidlockfile.TimeoutPIDLockFile(pidFile, 300), signal_map={signal.SIGTERM : sig_term}):
            try:
                messageProcessor = SQSConsumer()
                messageProcessor.run()
        
            except Exception as e:
                print >> sys.stderr, str(e)
                sys.exit(1)
    else:
        try:
            messageProcessor = SQSConsumer()
            messageProcessor.run()
        except Exception as e:
            print >> sys.stderr, str(e)
            sys.exit(1)
    
# Main
if __name__ == "__main__":
    main()
    