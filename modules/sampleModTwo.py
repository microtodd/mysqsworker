# This sample module shows how to deploy an opcode with a worker.
#
# 1. Create a class in the "modules" directory.
# 2. Make sure the class name is the same as the file name. Example: "class sampleMod" => "sampleMod.py"
# 3. The class needs a property called "methodName", which is the string value of the SQS json-rpc method.
#    In other words, if you want this class to be registered to the json-rpc method "opcode1", then make
#    the "methodName" value be "opcode1".
# 4. Create a method in the class called "Processor".  The method should receive two arguments, which will
#    be the arguments from the json-rpc call.
#
class sampleModTwo(object):
    methodName = 'echoTwo'
    def Processor(self,input1,input2):
        return input1 + "_" + input2
        
