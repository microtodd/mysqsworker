# mysqsworker

Version 0.1

Work in progress, this is sorta ready but hasn't really been tested yet

## Install
    
1. pip install boto3, daemon, json-rpc, importlib

2. Deploy sqsworker.py

3. Create subdirectory called "modules"

4. Place worker modules and __init__.py into modules directory

5. Deploy init

6. CloudFormation or manually create the SQS Queue, ensure ec2 instance has the correct role

## Configuration

- /etc/sqsworker/sqsworker.cfg (although this location can be overridden with the -f option to the daemon)

```
[main]
visibilityTimeout   = 1             Defaults to 1, you probably don't need to change this unless you have a long-running module
WaitTimeSeconds     = 20            Long polling, max is 20, you probably don't need to change this unless you have a LOT of rpc calls
testMode            = true          true or false, if true this runs unit tests and exits
region              = 'us-east-1'   Defaults to us-east-1

[queues]
queueName       = queueUrl          Queues must have unique names and URLs
```

## Plugin modules

To create a plugin module:

1. Name the class the same as the file (without the .py extension)

2. Make sure there is a property called 'methodName' which will be the RPC method this is registered to

3. Make sure there is a method called 'Processor' that accepts arguments. It will be the same number of arguments
   that you expect to receive with that RPC message

## Cloudformation

A cloudformation template is presented as an example of how this stack could be deployed.

