import Pyro4
import config as constant
from multiprocessing import Lock
import time
import helpers
import threading


@Pyro4.expose
class gatProcess:
	def __init__(self, ID, daemon, nameServer):
		self.ID = ID
		self.name = "Gateway processing tier"
		self.nameServer = nameServer

		# variables to handle fault tolerance
		self.crash = 0
		self.hbTime = 0

		self.port = int(self.nameServer.list()['Pyro.NameServer'][-4:])

		if self.port == constant.constants.serverPort1:
			self.idList = constant.constants.idList1
		elif self.port == constant.constants.serverPort2:
			self.idList = constant.constants.idList2

		self._registerProcess(daemon, nameServer)

		self.port = int(nameServer.list()['Pyro.NameServer'][-4:])

		# maintains state of last device to be queried and it's corresponding lock
		# as the gatway has threads to serve multiple requests
		self.last_query_state = 0
		self.state_lock = threading.Lock()

		# thread sync lock for database
		self.db_lock = threading.Lock()

		# ok signal flag during leader election algorithm
		self.recv_ok = False
		# election done flag which stops further processing of messages
		self.election_done = False
		# lock to process multiple incoming election start messages on one node
		self.election_lock = Lock()
		# id of leader
		self.leader = -1

		# berkely clock sync algo data structures
		self.time_dict = {}
		self.offset = 0.0
		# logical clock counter
		self.logicalCounter = 0

		# these are our test case parameters
		if (constant.constants.initialHomeState=="empty"):
			self.homeState = constant.constants.empty
			self.securitySystem = constant.constants.ON
		elif (constant.constants.initialHomeState=="occupied"):
			self.homeState = constant.constants.occupied
			self.securitySystem = constant.constants.OFF

		self.cache = list([])

  # essentially intelligently inserts new values in the cache
  # the replacement policy is FIFO - which is ideal for our scenario
	def cache_handler(self,msg):
		# oldest is 0 index
		# append new at the end

		N = constant.constants.cacheSize

		if N == 0:
			self.cache = []
			return

		if not self.cache:
			curr_size = 0
			temp = []
		else:
			curr_size = len(self.cache)
			temp = self.cache


		sender = msg[1]
		data = msg[3]
		timestamp = msg[4]
		st = "{}, {}, {}".format(sender, data, timestamp)

		# if cache size has reached max limit then discard the first value
		if curr_size == N:
			temp = temp[1:]
		elif curr_size > N:
			assert(False)

		# check to handle the low probability case where
		# new event reaches this gateway before write msg from other gateway
		if curr_size != 0:
			recent_time = float(temp[len(temp)-1].split(',')[2])
			if recent_time > float(timestamp):
				# swap the two items
				a = temp[len(temp)-1]
				temp[len(temp)-1] = st
				temp.append(a)
			else:
				temp.append(st)
		else:
			temp.append(st)

		self.cache = temp

			# initiates election and is also called if the node receives the election start 
			# signal from another node
	def init_election(self):		
		helpers.init_election(self)
	
	# processing the election message once it is received
	# sends ok signal backs and recursively calls init_election again
	def process_election(self,msg):		
		helpers.process_election(self,msg)		

	# after recv win msg from leader  set leader variables
	def set_leader(self,msg):
		helpers.set_leader(self,msg)

	# receive ok msg
	def ok(self):
		helpers.ok(self)

	# # poll clocks for the time sync algorithm
	# # using a dedicate thread as a daemon in the background
	# def poll_clocks(self):
	#     	th = threading.Thread(target=helpers.poll_clocks, args=(self,))
 #        	th.daemon = True   # Daemonize thread
	#         th.start()
 #        	print "Started Clock Sync Thread. Starting events..."

 #    # send my own timestamp as a response to poll clock from leader
	# def send_timestamp(self,msg):
	# 	helpers.send_timestamp(self,msg)
	# 	return

	# # receive the offset value from the dict from the leader
	# def set_offset(self,msg):
	# 	offset_dict = msg[3]
	# 	self.offset = offset_dict[self.ID]
	# 	return
	# 	#print "id ", self.ID, "  offset = ", self.offset

	# # the leader will receive the timesatamp from other and update dict
	# def leader_recv_timestamp(self,msg):
	# 	#senders_time = msg[3]
	# 	from_ = msg[1]
	# 	self.time_dict[from_] = msg[3]
	# 	return


	# main process logic to handle receiving messages at gateway
	# leader elections not threaded
	# event processing threaded
	def receiveMessage(self, msg):
		# distinguish type of messages and calling appropriate functions
		msgType = msg[0]
		if msgType == constant.constants.hbMessage: 
			#print "{} has received the heartbeat message from {}".format(self.name, self.port)
			self.hbTime = time.time()
		elif msgType == constant.constants.leaderElectionMsg:
			self.process_election(msg)
		elif msgType == constant.constants.leaderWinMsg:
			self.set_leader(msg)
		elif msgType == constant.constants.logicalClockMsg:
			self.logicalCounter += 1
		# this should not be new thread - queryState should wait for this to finish
		elif msgType == constant.constants.responseMsg:
			self.process_state_response(msg)
		elif msgType==constant.constants.clockSyncMsg:
			self.leader_recv_timestamp(msg)
		elif msgType==constant.constants.clockSyncOffsetMsg:
			self.set_offset(msg)
		elif msgType==constant.constants.clockSyncPollMsg:
			self.send_timestamp(msg)
		
		elif msgType == constant.constants.pushMsg:
			self.store(msg)
			self.store_cache(msg)
			self.eventOrderLogic(msg)

		#else:
		#	th = threading.Thread(target=self.threaded_receiveMessage, args=(msg,))
	        	#th.daemon = True   # Daemonize thread
		 #       th.start()

	# function called in threaded manner simiar to receiveMessage
#	def threaded_receiveMessage(self,msg):
#		msgType = msg[0]
#		if msgType==constant.constants.clockSyncMsg:
#			self.leader_recv_timestamp(msg)
#		elif msgType==constant.constants.clockSyncOffsetMsg:
#			self.set_offset(msg)
#		elif msgType==constant.constants.clockSyncPollMsg:
#			self.send_timestamp(msg)
		
#		elif msgType == constant.constants.pushMsg:
#			self.store(msg)
#			self.store_cache()
#			self.eventOrderLogic(msg)


	# to handle the change of eg. home state = occupied from one gateway to another
	def change_home_state(self,str,state):
		if str == 'security':
			self.securitySystem = state
		elif str == 'home':
			self.homeState = state

			# find the nameserver of the device in cases where
			# 1. state has to be queried 2. state has to controled of a smart device
	def find_nameserver(self,deviceID):
		idList1 = helpers.get_idlist(1)
		idList2 = helpers.get_idlist(2)

		# if server is down then that idList will be list of -1

		if deviceID in idList1:
			ns = Pyro4.locateNS(constant.constants.serverAddress1, constant.constants.serverPort1)
		elif deviceID in idList2:
			ns = Pyro4.locateNS(constant.constants.serverAddress2, constant.constants.serverPort2)
		elif idList1[0] == -1 or idList2[0]==-1:
			ns = 0

		return ns

			# pull data from sensors based on only the device id
	def queryState(self,deviceID):
		# this function is called by the 
		#  main logic to get the state of pull-based
		# sensors or smart outlet
		if (deviceID==constant.constants.presenceSensorID):
			print "Gateway can't query presence sensor"
			return

		print("pulling data from the sensors")
		ns = self.find_nameserver(deviceID)
		if ns ==0:
			print "Can't query state if {}, it's server down - hasn't yet registered with new".format(deviceID)
			return

		recURI = ns.lookup(str(deviceID))
		recProxy = Pyro4.Proxy(recURI)
		recProxy.getState() 
		state = self.last_query_state
		self.state_lock.release()
		return state

		# for processing the response to the query
		# print to screen and set the last devide queried state - which
		# will be read by queryState
	def process_state_response(self,msg):
		# just for informative printing 
		state = msg[3]
		deviceID = msg[1]
		time = msg[4]

		self.state_lock.acquire()
		self.last_query_state = state

		if (deviceID==constant.constants.motionSensorID):
			print "The motion sensor state is {} at time {}".format(str(state),time)
		elif (deviceID==constant.constants.doorSensorID):
			print "The door sensor state is {} at time {}".format(str(state),time)
		elif (deviceID==constant.constants.tempSensorID):
			print "The current temperature is {} at time {}".format(str(state),time)
		elif (deviceID==constant.constants.smartBulbID):
			print "Smart Bulb is {} at time {}".format(str(state),time)
		elif (deviceID==constant.constants.smartOutletID):
			print "Smart Outlet is {} at time {}".format(str(state),time)

		# controlling the 2 smart devices - smart bulb and smart outlet
		# either turns on or odd the 2 smart devices only
	def sendControlMsg(self,deviceID,state):
		# this function changes the state of the appliances
		# device should either be bulb or outlet
		if (deviceID !=  constant.constants.smartBulbID) and (deviceID != constant.constants.smartOutletID):
			print "Gateway trying to control incorrect devices"
			return

		if state == 1:
			payload = constant.constants.turnOn
		elif state == 0 :
			payload = constant.constants.turnOff
		else:
			print "Wrong outlet state by gateway"
			return

		print("Gateway controlling the state of smart appliances")
		msgType = constant.constants.controlStateMsg
		msg = [msgType, self.ID, deviceID, payload]
		#recURI = self.nameServer.lookup(str(deviceID))
		ns = self.find_nameserver(deviceID)
		if ns == 0:
			print "Can't control state of {}, it's server down - hasn't yet registered with new".format(deviceID)
			return

		recURI = ns.lookup(str(deviceID))
		#print deviceID, '------------ ', ns.list()
		recProxy = Pyro4.Proxy(recURI)
		recProxy.controlState(msg) # this will take care of sending logical clock msg and updating db

		# insert most recent event in the cache with consistency
		# ie. of crash has not happened then write in other server's cache too
	def store_cache(self,msg):
		self.cache_handler(msg)
		if self.crash==0:
			if self.port == constant.constants.serverPort1:
				try:
					recv_nameserver = Pyro4.locateNS(constant.constants.serverAddress2, constant.constants.serverPort2)
				except:
					print "Can not locate other nameserver from {}".format(self.port)
					recv_nameserver = 0
			elif self.port == constant.constants.serverPort2:
				try:
					recv_nameserver = Pyro4.locateNS(constant.constants.serverAddress1, constant.constants.serverPort1)
				except:
					print "Can not locate other nameserver from {}".format(self.port)
					recv_nameserver = 0

			if recv_nameserver != 0:
				recURI = recv_nameserver.lookup(str(constant.constants.processingTierID))
				recProxy = Pyro4.Proxy(recURI)
				recProxy.cache_handler(msg)

		
		# store the push based events to a sequential database
		# also call another func to update a 2nd database file to
		# save state of each device

		# Does 3 things: 1. Store in own main db
		# 2. Send same write msg to other db - consistency
		# 3. Store in own state db - send consistency message
	def store(self,msg):
		# this message stores the event/value in the database on tier 2
		print "Storing event on database with Consistency messages"
		self.recv_write_info(msg)

		# send write message to second gateway
		if self.crash == 0:
			if self.port == constant.constants.serverPort1:
				try:
					recv_nameserver = Pyro4.locateNS(constant.constants.serverAddress2, constant.constants.serverPort2)
				except:
					print "Can not locate other nameserver from {}".format(self.port)
					recv_nameserver = 0
			elif self.port == constant.constants.serverPort2:
				try:
					recv_nameserver = Pyro4.locateNS(constant.constants.serverAddress1, constant.constants.serverPort1)
				except:
					print "Can not locate other nameserver from {}".format(self.port)
					recv_nameserver = 0

			if recv_nameserver != 0:
				recURI = recv_nameserver.lookup(str(constant.constants.processingTierID))
				recProxy = Pyro4.Proxy(recURI)
				recProxy.recv_write_info(msg)

		# update state in 2nd state database
		deviceID = msg[1]
		state = msg[3]
		self.store2(deviceID,state)
		

		# called by store()
		# simple inserts a message into the corresponding database
	def recv_write_info(self,msg):
		recURI = self.nameServer.lookup(str(constant.constants.databaseTierID))
		recProxy = Pyro4.Proxy(recURI)
		self.db_lock.acquire()
		recProxy.insert(msg)
		self.db_lock.release()


		# the 2nd db - state_database 
		# update the corresponsing row with the latest state
		# with consistency
	def store2(self,deviceID,new_state):
		print "Updating Device ID {} state on Both State Databases to {}".format(deviceID,new_state)
		self.update_device_state_db(deviceID,new_state)		

		# send write message to second gateway
		if self.crash == 0:
			if self.port == constant.constants.serverPort1:
				try:
					recv_nameserver = Pyro4.locateNS(constant.constants.serverAddress2, constant.constants.serverPort2)
				except:
					print "Can not locate other nameserver from {}".format(self.port)
					recv_nameserver = 0
			elif self.port == constant.constants.serverPort2:
				try:
					recv_nameserver = Pyro4.locateNS(constant.constants.serverAddress1, constant.constants.serverPort1)
				except:
					print "Can not locate other nameserver from {}".format(self.port)
					recv_nameserver = 0
			if recv_nameserver != 0:
				recURI = recv_nameserver.lookup(str(constant.constants.processingTierID))
				recProxy = Pyro4.Proxy(recURI)
				recProxy.update_device_state_db(deviceID,new_state)
		# complimentary function for above function
		# retreives state of a device from the state_datavase file

		# update the device states in the 2nd databsae of state databse
		# called by store2()
	def update_device_state_db(self,deviceID,new_state):
		recURI = self.nameServer.lookup(str(constant.constants.databaseTierID))
		recProxy = Pyro4.Proxy(recURI)
		self.db_lock.acquire()
		recProxy.update_device_state(deviceID,new_state)
		self.db_lock.release()
		
	def retreive_device_state_db(self,deviceID):
		recURI = self.nameServer.lookup(str(constant.constants.databaseTierID))
		recProxy = Pyro4.Proxy(recURI)
		state_str = recProxy.retreive_device_state(deviceID)
		return state_str

	def retrieve_last(self):
		# this message retrieves the data from the database when needed
		recURI = self.nameServer.lookup(str(constant.constants.databaseTierID))
		recProxy = Pyro4.Proxy(recURI)
		last_e = recProxy.retrieve_last()
		#print("retrieving data from database")
		return last_e


	def sendMessage(self, msg):
		# if the message is push or response then, msg format = [msgType, sender, receiver, msg]
		# if the message type is selective then, msg format = [msgType, sender, [receivers 1-N], msg]
		# in the selective msg type, receivers should be inside an array even if there is only one
		# if the message is broadcast type, then msg format is msg format = [msgType, sender, receiver, msg]
		# you can put anything at receivers place, it doesn't matter as broadcast mechanism sends msg to everyone
		# except the node itself
		helpers.sendMessage(self,msg)

	def eventOrderLogic(self,msg):
		# activated only in case of push messages
		if (msg[1] == constant.constants.doorSensorID):

			if not self.cache:
				clen = 0
			else:
				clen = len(self.cache)
			# The way we have desgined - we only need to get the last event from the DB
			# If the cache size / current size >= 2 then we are garunteed to find what is required in cache
			# The replacment policy is FIFO
			if clen >= 2:
				print "CACHE HIT: Data present in Cache"
				#print self.cache
				line = self.cache[-2]
				last_event = [ch for ch in line.split(',')]
			else:
				print "CACHE MISS: Data NOT present in Cache - getting from DB"
				last_event = self.retrieve_last()
			
			last_event_type = int(last_event[0])
			# empty house and door opern after prsence - let user in
			if (self.homeState == constant.constants.empty and last_event_type==constant.constants.presenceSensorID):
				# check if there is no motion sensed in the recent past
				print("GATEWAY: User has just entered the home with presence. Turning off the security system.")
				self.securitySystem = constant.constants.OFF
				self.homeState = constant.constants.occupied

				if self.crash == 0:
					if self.port == constant.constants.serverPort1:
						try:
							recv_nameserver = Pyro4.locateNS(constant.constants.serverAddress2, constant.constants.serverPort2)
						except:
							print "Can not locate other nameserver from {}".format(self.port)
							recv_nameserver = 0
					elif self.port == constant.constants.serverPort2:
						try:
							recv_nameserver = Pyro4.locateNS(constant.constants.serverAddress1, constant.constants.serverPort1)
						except:
							print "Can not locate other nameserver from {}".format(self.port)
							recv_nameserver = 0

					if recv_nameserver != 0:
						recURI = recv_nameserver.lookup(str(constant.constants.processingTierID))
						recProxy = Pyro4.Proxy(recURI)
						recProxy.change_home_state('security',constant.constants.OFF)
						recProxy.change_home_state('home',constant.constants.occupied)


				# empty house and door opens with no beacon = burgler
			elif (self.homeState == constant.constants.empty and last_event_type!=constant.constants.presenceSensorID):
				# check if there is no motion sensed in the recent past
				print("GATEWAY: ALERT! Intruder opened door without presence sensor Ring Alarm ")
				self.sendControlMsg(constant.constants.smartBulbID,1)		# turn on the bulbs because of the alarms

				# occupied house and door operns after motions
				# let use out
				# turn the lights off
			elif (self.homeState == constant.constants.occupied and last_event_type==constant.constants.motionSensorID):
				# check which event happened first
				print ("GATEWAY: User is leaving the home. Turning on the security system and turn off lights.")
				self.securitySystem = constant.constants.ON
				self.homeState = constant.constants.empty

				if self.crash == 0:
					if self.port == constant.constants.serverPort1:
						try:
							recv_nameserver = Pyro4.locateNS(constant.constants.serverAddress2, constant.constants.serverPort2)
						except:
							print "Can not locate other nameserver from {}".format(self.port)
							recv_nameserver = 0
					elif self.port == constant.constants.serverPort2:
						try:
							recv_nameserver = Pyro4.locateNS(constant.constants.serverAddress1, constant.constants.serverPort1)
						except:
							print "Can not locate other nameserver from {}".format(self.port)
							recv_nameserver = 0

					if recv_nameserver != 0:
						recURI = recv_nameserver.lookup(str(constant.constants.processingTierID))
						recProxy = Pyro4.Proxy(recURI)
						recProxy.change_home_state('security',constant.constants.ON)
						recProxy.change_home_state('home',constant.constants.empty)

				self.sendControlMsg(constant.constants.smartBulbID,0)	# turn off the bulbs

				# occupied house but door opern with noe beacon = burgler
			elif (self.homeState == constant.constants.occupied and last_event_type!=constant.constants.motionSensorID):
				# check which event happened first
				print("GATEWAY: ALERT! Intruder opened door without presence sensor Ring Alarm ")
				self.sendControlMsg(constant.constants.smartBulbID,1)

				# motion in an empty house meanse a intruder
				# if occupied house then turn the lights on if not already on
		elif (msg[0] == constant.constants.pushMsg and msg[1] == constant.constants.motionSensorID):
			if (self.homeState == constant.constants.empty):
				print "GATEWAY: ALERT! Motion when house empty - ringing alarms"
			elif (self.homeState == constant.constants.occupied):
				# turn on the lights if not already on
				bulb_state = self.queryState(constant.constants.smartBulbID)
				if bulb_state != constant.constants.turnOn:
					print "GATEWAY: Turn on Lights due to Motion"
					self.sendControlMsg(constant.constants.smartBulbID,1)
	

	def _registerProcess(self, daemon, nameServer):
		processUri = daemon.register(self)
		nameServer.register(str(self.ID), processUri)

		# we start sending the heartbeat message as a part of the registeration process
		th = threading.Thread(target=helpers.sendPulse, args=(self,))
		th.daemon = True   # Daemonize thread
		th.start()


		#this thread starts the check pulse process for all the devices and gateways. 
		th1 = threading.Thread(target=helpers.checkPulse, args=(self,))
		th1.daemon = True   # Daemonize thread
		th1.start()
		print("{} has been registered with ID: {}").format(self.name, self.ID)
