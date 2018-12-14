import Pyro4
import config as constant
from multiprocessing import Lock
import time
import helpers
import threading

@Pyro4.expose
class door:
	def __init__(self, ID, daem, nameServer):
		# these are the initial values of the variables that are 
		# set when the node register itself with the name server

		self.daemon = daem 

		self.ID = ID
		self.name = "Door sensor" 

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

		#print self.nameServer

		self.port = int(self.nameServer.list()['Pyro.NameServer'][-4:])

		if self.port == constant.constants.serverPort1:
			self.idList = constant.constants.idList1
		elif self.port == constant.constants.serverPort2:
			self.idList = constant.constants.idList2

		# this function call is to register itself with the nameserver
		self._registerProcess(self.daemon, self.nameServer)

		# maintains state of last device to be queried and it's corresponding lock
		# as the gatway has threads to serve multiple requests
		self.doorState = 'DOOR-CLOSED'	
		self.last_door_time = 0.0	


		# these variables are related to leader election and clock synchronization
		self.recv_ok = False
		#self.is_leader = False
		self.election_done = False
		self.election_lock = Lock()
		self.leader = -1

		# berkely clock sync algo data structures
		self.time_dict = {}
		self.offset = 0.0

		# logical clock counter
		self.logicalCounter = 0

	def init_election(self):
		# this function call is to start the election where this node 
		# sends a message to all other processes to start an election

		# it also checks if election done message is received or there 
		# is no reply from other nodes, and sets itself leader in that case. 

		helpers.init_election(self)
		
		# processing the election message once it is received
		# sends ok signal backs and recursively calls init_election again
	def process_election(self,msg):	
		# this function processes the election messages received.
		helpers.process_election(self,msg)		

		# after recv win msg from leader  set leader variables
	def set_leader(self,msg):
		# sets the leader
		helpers.set_leader(self,msg)

	def ok(self):
		helpers.ok(self)
	
		# poll clocks for the time sync algorithm
		# using a dedicate thread as a daemon in the background
	# def poll_clocks(self):
	# 	# starts a clock sync thread in a new thread to support concurrency
	# 	print "Running Clock Sync Thread"
	#     	th = threading.Thread(target=helpers.poll_clocks, args=(self,))
 #        	th.daemon = True   # Daemonize thread
	#         th.start()


	# def send_timestamp(self,msg):
	# 	helpers.send_timestamp(self,msg)

	# def set_offset(self,msg):
	# 	offset_dict = msg[3]
	# 	self.offset = offset_dict[self.ID]
	# 	#print "id ", self.ID, "  offset = ", self.offset


	# def leader_recv_timestamp(self,msg):
	# 	#senders_time = msg[3]
	# 	from_ = msg[1]
	# 	self.time_dict[from_] = msg[3]
	# 	return

	# def logicalClock(self, msg):
	# 	self.sendMessage(msg)

	def receiveMessage(self, msg):
		# this function is called by the push-based sensors 
		# to send their state to the gateway
		sender = msg[1]
		#print("{} with ID {} is getting data from {}").format(self.name, self.ID, sender)
		msgType = msg[0]

		# this function compare the different type of messages received
		if msgType == constant.constants.hbMessage: 
			#print "{} has received the heartbeat message from {}".format(self.name, self.port)
			self.hbTime = time.time()
			#print "Receiving heartbeat"
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
			# should I send an ack?

	def openDoor(self, entranceID):
		# this function changes the state of the 
		# door as instructed by the user process
		# whenever state changes this function informs gateway as well
		
		#entranceID = msg[3]
		
		if (entranceID == constant.constants.validID):

			self.doorState = 'DOOR-OPEN'
			self.last_door_time = time.time()

			# here we chose between logical clocks and synchronized clock mechanisms
			# if (constant.constants.useLogicalClock):
			# 	self.logicalCounter += 1
			# 	timestamp = self.logicalCounter
			# 	lClockMsg = [constant.constants.logicalClockMsg, self.ID, constant.constants.broadcastRcvID, '', self.logicalCounter]
			# 	self.logicalClock(lClockMsg)
			# else:
			# 	timestamp = time.time() + self.offset

			timestamp = time.time()
			
			print("Event {}: Door tried to be opened, informing gateway.").format(timestamp)
			msg = [constant.constants.pushMsg, self.ID, constant.constants.processingTierID, self.doorState, timestamp]

			try:
				self.nameServer.list()
				self.sendMessage(msg)
			except Pyro4.errors.ConnectionClosedError:
				# current server is down - has not registered with new server
				print "SYSTEM DOWN: {}'s Server is down - not yet registered with new server".format(self.name)

			#if constant.constants.useLogicalClock:
				
			# this function ensures that the state of the door is reversed to closed after some seconds
			th = threading.Thread(target=self.revert_state)
	        	th.daemon = True   # Daemonize thread
        		th.start()
		else: 
			# similar to prescence sensor ... 
			print("ALERT! Intruder got access, ringing alarms.")

	def revert_state(self):
		# close door after 1 seconds of last door open 
		while(self.doorState=='DOOR-OPEN'):
			t = time.time()
			if (t - self.last_door_time>=1.0):
				self.doorState = 'DOOR-CLOSED'
				try:
					recURI = self.nameServer.lookup(str(constant.constants.processingTierID))
				except:
					print "Failure to revert state due to crash"
					
				recProxy = Pyro4.Proxy(recURI)
				recProxy.store2(self.ID,'DOOR-CLOSED')
		return


	def getState(self):
		# this method can be called by the gateway to get the status of the door
		print("Responding the door state to the gateway.")
		if constant.constants.useLogicalClock:
			timestamp = self.logicalCounter
		else:
			timestamp = time.time() + offset

		msg = [constant.constants.responseMsg, self.ID, constant.constants.processingTierID, self.doorState, timestamp]
		self.sendMessage(msg)
		#return self.doorState

	def sendMessage(self, msg):
		# if the message is push or response then, msg format = [msgType, sender, receiver, msg, timestamp]
		# if the message type is selective then, msg format = [msgType, sender, [receivers 1-N], msg, timestamp]
		# in the selective msg type, receivers should be inside an array even if there is only one
		# if the message is broadcast type, then msg format is msg format = [msgType, sender, receiver, msg, timestamp]
		# you can put anything at receivers place, it doesn't matter as broadcast mechanism sends msg to everyone
		# except the node itself
		helpers.sendMessage(self,msg)

	def _registerProcess(self, daemon, nameServer):
		processUri = daemon.register(self)
		nameServer.register(str(self.ID), processUri)
		print("{} has been assigned an ID {} and registered with gateway {}").format(self.name, self.ID, self.port)

		#this thread starts the check pulse process for all the devices and gateways. 
		#print self.hbTime
		th = threading.Thread(target=helpers.checkPulse, args=(self,))
		th.daemon = True   # Daemonize thread
		th.start()

			# crashed with old server - registered with new
