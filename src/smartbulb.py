import Pyro4
import config as constant
from multiprocessing import Lock
import time
import helpers
import threading


@Pyro4.expose
class bulb:
	def __init__(self, ID, daemon, nameServer):
		self.ID = ID 
		self.name = "Smart bulb"

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
			
		self.bulbState = constant.constants.turnOff


		self.recv_ok = False
		#self.is_leader = False
		self.election_done = False
		self.election_lock = Lock()
		self.leader = -1

		self.time_dict = {}
		self.offset = 0.0

		self.logicalCounter = 0
		self._registerProcess(daemon, self.nameServer)

	def init_election(self):		
		helpers.init_election(self)
		
	def process_election(self,msg):		
		helpers.process_election(self,msg)		

	def set_leader(self,msg):
		helpers.set_leader(self,msg)

	def ok(self):
		helpers.ok(self)

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
		'''
		if (msg[2] == constant.constants.initLogCloclMsg):
			print("event happened elsewehere, send ack to others")
		elif(msg[2] == constant.constants.ackLogClockMsg):
			print("wait for acks from all of the processes and then increase counter")
		'''	
		self.sendMessage(msg)



	def receiveMessage(self, msg):
		# this function is called by the push-based sensors 
		# to send their state to the gateway
		#print("{} with ID {} is getting data").format(self.name, self.ID)
		msgType = msg[0]

		if msgType == constant.constants.hbMessage: 
			self.hbTime = time.time()
		elif msgType == constant.constants.crashMessage:
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
				#print ("Event update received, increasing logical clock by 1 to {}").format(self.logicalCounter)


	def controlState(self, msg):
		# this function can be called by the user 
		# or the gateway manager to change the state
		# of the bulb. Set some global variable
		# if (constant.constants.useLogicalClock):
		# 	self.logicalCounter += 1
		# 	timestamp = self.logicalCounter
		# else:
		# 	timestamp = time.time() + self.offset

		timestamp = time.time()


		if (msg[3] == constant.constants.turnOn):
			self.bulbState = constant.constants.turnOn
			if (msg[1] == constant.constants.userID):
				print("Event {}: User turned on the bulb.").format(timestamp)
			else: 
				print("Event {}: Bulb turned on by the gateway.").format(timestamp)
		elif(msg[3] == constant.constants.turnOff):
			self.bulbState = constant.constants.turnOff
			if (msg[1] == constant.constants.userID):
				print("Event {}: User turned off the bulb.").format(timestamp)
			else: 
				print("Event {}: Bulb turned off by the gateway.").format(timestamp)

		#if (constant.constants.useLogicalClock):
			# lClockMsg = [constant.constants.logicalClockMsg, self.ID, constant.constants.broadcastRcvID, '', self.logicalCounter]
			# self.logicalClock(lClockMsg)
		
		msg = [constant.constants.pushMsg, self.ID, constant.constants.processingTierID, self.bulbState, timestamp]
		self.sendMessage(msg)

	def getState(self):
		# this function is called by the gateway to 
		# get the state of the bulb.
		print("Responding the bulb state to the gateway.")
		if (constant.constants.useLogicalClock):
			timestamp = self.logicalCounter
		else:
			timestamp = time.time() + self.offset
		msg = [constant.constants.responseMsg, self.ID, constant.constants.processingTierID, self.bulbState, timestamp]
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