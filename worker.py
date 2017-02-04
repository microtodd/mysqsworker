import datetime
import boto3

mySqs = boto3.resource('sqs', region_name='us-east-1')
print 'all my queues:'
for queue in mySqs.queues.all():
    print '=> ' + str(queue)

myQueue = mySqs.get_queue_by_name(QueueName='sqsTest1')
myMessages = myQueue.receive_messages(MaxNumberOfMessages=10,WaitTimeSeconds=20,VisibilityTimeout=1,AttributeNames=['All'])
for message in myMessages:
    print 'body=>'+str(message.body)
    attr = message.attributes
    print 'sent=>'+str(attr.get('SentTimestamp'))
    print datetime.datetime.fromtimestamp(float(attr.get('SentTimestamp'))/1000.0)
    message.delete()