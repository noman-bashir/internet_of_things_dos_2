import Pyro4
import config as constant
import random as random
import time
from multiprocessing import Lock
import helpers
import threading



@Pyro4.expose
class temperature:
	def __init__(self, ID, daemon, nameServer):
		self.ID = ID 
		self.name = "Temperature sensor"

		self.daemon = daemon

		self.crash = 0 
		self.hbTime = 0

		# if ID assigned is even, register with first nameServer. Otherwise with second
		# the metrics used for this assignment can be changed and easily inserted here. 
		if (self.ID%2 ==0):
			self.nameServer = nameServer[0]
		elif(self.ID%2 == 1):
			self.nameServer = nameServer[1]
		else:
			print "The ID assigned is neither even nor odd"

		self.port = int(self.nameServer.list()['Pyro.NameServer'][-4:])
		if self.port == constant.constants.serverPort1:
			self.idList = constant.constants.idList1
		elif self.port == constant.constants.serverPort2:
			self.idList = constant.constants.idList2

		self._registerProcess(daemon, self.nameServer)



		self.tempVal = 30

		self.recv_ok = False
		#self.is_leader = False
		self.election_done = False
		self.election_lock = Lock()
		self.leader = -1

		self.time_dict = {}
		self.offset = 0.0

		self.logicalCounter = 0

	def init_election(self):		
		helpers.init_election(self)


		# processing the election message once it is received
	 	# sends ok signal backs and recursively calls init_election again
	def process_election(self,msg):		
		helpers.process_election(self,msg)		

		# after recv win msg from leader  set leader variables
	def set_leader(self,msg):
		helpers.set_leader(self,msg)

	def ok(self):
		helpers.ok(self)

		# poll clocks for the time sync algorithm
		# using a dedicate thread as a daemon in the background
	def poll_clocks(self):
		print "Running Clock Sync Thread"
	    	th = threading.Thread(target=helpers.poll_clocks, args=(self,))
        	th.daemon = True   # Daemonize thread
	        th.start()

	def send_timestamp(self,msg):
		helpers.send_timestamp(self,msg)

	def set_offset(self,msg):
		offset_dict = msg[3]
		self.offset = offset_dict[self.ID]
		#print "id ", self.ID, "  offset = ", self.offset

	def leader_recv_timestamp(self,msg):
		#senders_time = msg[3]
		from_ = msg[1]
		self.time_dict[from_] = msg[3]
		return

	def logicalClock(self, msg):
		self.sendMessage(msg)



	def receiveMessage(self, msg):
		# this function is called by the push-based sensors 
		# to send their state to the gateway
		#print("{} with ID {} is getting data").format(self.name, self.ID)
		msgType = msg[0]

		if msgType == constant.constants.hbMessage: 
			self.hbTime = time.time()
		elif msgType == constant.constants.crashMessage:
			#print "crash message has been received"
			self.crash = 1
		elif msgType == constant.constants.leaderElectionMsg:
			self.process_election(msg)
		elif msgType == constant.constants.leaderWinMsg:
			self.set_leader(msg)
		elif msgType==constant.constants.clockSyncMsg:
			self.leader_recv_timestamp(msg)
		elif msgType==constant.constants.clockSyncOffsetMsg:
			self.set_offset(msg)
		elif msgType==constant.constants.clockSyncPollMsg:
			self.send_timestamp(msg)
		elif msgType == constant.constants.logicalClockMsg:
			if (self.logicalCounter < msg[4]):    # this is done to avoid increasing the counter twice even if 
				self.logicalCounter += 1    	  # the two events have the same time stamp
				#print ("Event update received, increasing counter by 1 to {}").format(self.logicalCounter)


	def senseTemperature(self):
		# this function should read from a file or generate 
		# temperature value randomly. It emulates actual sensing
		temperature = random.randint(constant.constants.lowestTemp, constant.constants.highestTemp)
		return temperature

	def getState(self):
		# the central gateway should call this function to get 
		# temperature value

		# if (constant.constants.useLogicalClock):
		# 		self.logicalCounter += 1
		# 		timestamp = self.logicalCounter
		# 		lClockMsg = [constant.constants.logicalClockMsg, self.ID, constant.constants.broadcastRcvID, '', self.logicalCounter]
		# 		self.logicalClock(lClockMsg)
		# else:
		# 	timestamp = time.time() + self.offset


		timestamp = time.time()
		

		tempVal = self.senseTemperature() # calling sense temperature function to get value
		print("Event {}: Responding the temperature value to the gateway.").format(timestamp)
		msg = [constant.constants.responseMsg, self.ID, constant.constants.processingTierID, tempVal, timestamp]
		self.sendMessage(msg)


	def sendMessage(self, msg):
		# if the message is push or response then, msg format = [msgType, sender, receiver, msg]
		# if the message type is selective then, msg format = [msgType, sender, [receivers 1-N], msg]
		# in the selective msg type, receivers should be inside an array even if there is only one
		# if the message is broadcast type, then msg format is msg format = [msgType, sender, receiver, msg]
		# you can put anything at receivers place, it doesn't matter as broadcast mechanism sends msg to everyone
		# except the node itself
		helpers.sendMessage(self,msg)

	def _registerProcess(self, daemon, nameServer):
		processUri = daemon.register(self)
		nameServer.register(str(self.ID), processUri)
		print("{} has been assigned an ID {} and registered with gateway {}").format(self.name, self.ID, self.port)
		
		#this thread starts the check pulse process for all the devices and gateways. 
		th = threading.Thread(target=helpers.checkPulse, args=(self,))
		th.daemon = True   # Daemonize thread
		th.start()