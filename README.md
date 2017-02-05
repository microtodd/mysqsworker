# mysqsworker

Version 0.1

Work in progress, this is nowhere close to being ready.

# Install
    
1. pip install boto3, daemon, json-rpc, importlib

2. Deploy sqsworker.py

3. Create subdirectory called "modules"

4. Place worker modules and __init__.py into modules directory

5. _TODO_ Deploy init

6. CloudFormation or manually create the SQS Queue, ensure ec2 instance has the correct role

# TODO

1. Author init script

2. Implement logging

3. Implement conf file loading for all the parameters
