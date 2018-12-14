import Pyro4
import time
from multiprocessing import Lock
import config as constant


# common functions mostly relating to clock mechanism
# or leader election seperated to avoid redundancies

# different msg types with similar sending behavious grouped together
selective_msgs = [constant.constants.selectiveMsg, constant.constants.leaderElectionMsg, constant.constants.clockSyncMsg]
response_msgs = [constant.constants.pushMsg, constant.constants.responseMsg]
broadcast_msgs = [constant.constants.broadCastMsg, constant.constants.leaderWinMsg, constant.constants.logicalClockMsg, constant.constants.hbMessage, constant.constants.crashMessage]
clock_msgs = [constant.constants.clockSyncOffsetMsg,constant.constants.clockSyncPollMsg]



def init_election(self):
	#self.is_leader = False
	#self.recv_ok = False
	if self.election_done:
		return

	idList = self.idList
	recv_list = []
	for i in idList:
		if (self.ID<i):
			recv_list.append(i)

	msgType = constant.constants.leaderElectionMsg
	sender = self.ID
	msgPayLoad = ''
	msg = [msgType, sender, recv_list, msgPayLoad]
	#print "election msg from", self.ID, " -> ", recv_list
	self.sendMessage(msg)
	# send election message to all nodes whose id is less than self

	# time to allow ok signals to come in
	time.sleep(1)

	# if no ok signal received - elect leader
	if not self.recv_ok and not self.election_done:
		# set leader vars
		self.leader = self.ID
		self.election_done = True

		msgType = constant.constants.leaderWinMsg
		sender = self.ID
		msgPayLoad = self.ID
		msg = [msgType, sender, [], msgPayLoad]
		self.sendMessage(msg)
		print "ELECTION DONE: Leader is ", self.name

		#time.sleep(1)

		# start clock sync polling
		#self.poll_clocks()


	# process election receive msg by sending ok back and calling init_election
def process_election(self,msg):

	sender = msg[1]
	# send ok back 
	recURI = self.nameServer.lookup(str(sender))
	recProxy = Pyro4.Proxy(recURI)
	recProxy.ok()
	# send more elctions

	# or lock here ?
	self.election_lock.acquire()
	self.init_election()
	self.election_lock.release()
	#helpers.process_election()

	

def set_leader(self,msg):
	payload = msg[3]
	leader_id = payload
	self.leader = leader_id
	self.election_done = True


def ok(self):
	if self.election_done:
		return
	self.recv_ok = True



######################################################

def poll_clocks(self):
	
	if not (self.ID == self.leader):
		print "ERORR - polling not done by leader"
		return
	idList = self.idList

	# keep continuing as a daemon
	while (True):
		self.time_dict = {}

		msgType = constant.constants.clockSyncPollMsg
		sender = self.ID
		msgPayLoad = ''
		msg = [msgType, sender, [], msgPayLoad]
		self.sendMessage(msg)
		self.time_dict[self.ID] = time.time()
		#print "time dict  ", self.time_dict

		# time.sleep(1) ## will it cause un-sync ??	
		# print "22 ", self.time_dict

		if (len(self.time_dict)==len(idList)-1): # no db tier
		# avg calc
			time_dict = self.time_dict
			time_sum = 0.0
			for k in time_dict:
				time_sum += time_dict[k]
			avg_time = time_sum/float(len(idList)-1)

		# send offset
			offsets = {}
			for k in time_dict:
				offsets[k] = avg_time - time_dict[k]

			msgType = constant.constants.clockSyncOffsetMsg
			sender = self.ID
			msgPayLoad = offsets
			msg = [msgType, sender, [], msgPayLoad]

			# set leader's offset
			self.offset = offsets[self.ID]
			#print offsets
			self.sendMessage(msg)

		time.sleep(5)


def send_timestamp(self,msg):
	from_ = msg[1]
	if from_ != self.leader:
		print "ERORR! Leader is not equal to Time Poller"
		return

		# send current time back to leader

	msgType = constant.constants.clockSyncMsg
	recv_list = [from_]
	msg = [msgType, self.ID, recv_list, time.time()]
	self.sendMessage(msg)
	return


#################################

def sendMessage(self, msg):
		# if the message is push or response then, msg format = [msgType, sender, receiver, msg]
		# if the message type is selective then, msg format = [msgType, sender, [receivers 1-N], msg]
		# in the selective msg type, receivers should be inside an array even if there is only one
		# if the message is broadcast type, then msg format is msg format = [msgType, sender, receiver, msg]
		# you can put anything at receivers place, it doesn't matter as broadcast mechanism sends msg to everyone
		# except the node itself
		msgType = msg[0]
		msgSender = msg[1]
		msgReceiver = msg[2]
		if msgType in selective_msgs :
			for i in range(len(msgReceiver)):
				recURI = self.nameServer.lookup(str(msgReceiver[i]))
				recProxy = Pyro4.Proxy(recURI)
				recProxy.receiveMessage(msg)

		elif msgType in response_msgs:
			recURI = self.nameServer.lookup(str(msgReceiver))
			recProxy = Pyro4.Proxy(recURI)
			recProxy.receiveMessage(msg)

		elif msgType == constant.constants.controlStateMsg:
			recURI = self.nameServer.lookup(str(msgReceiver))
			recProxy = Pyro4.Proxy(recURI)
			recProxy.controlState(msg)

		elif msgType == constant.constants.pullMsg:
			recURI = self.nameServer.lookup(str(msgReceiver))
			recProxy = Pyro4.Proxy(recURI)
			recProxy.getState()

		elif msgType in broadcast_msgs:
			#print msgType
			procList = self.idList # list of all the processes
			#print procList
			for i in range(len(procList)):
				if (procList[i] != self.ID):
					try: 
						recURI = self.nameServer.lookup(str(procList[i]))
						recProxy = Pyro4.Proxy(recURI)
						recProxy.receiveMessage(msg)
					except: 
						pass

		elif msgType in clock_msgs:
			send_time = time.time()
			# TODO send start, end time --- RTT
			procList = self.idList
			for i in range(len(procList)):
				if (procList[i] != self.ID) and (procList[i] != constant.constants.databaseTierID):
					recURI = self.nameServer.lookup(str(procList[i]))
					recProxy = Pyro4.Proxy(recURI)
					recProxy.receiveMessage(msg)

#################################################

# check pulse daemon running in all nodes
# if stop receiving heeartbeat and crash not yet happened then - switch servers
# if gateway foundout other gateway has crashed then send crash=1  message to all original nodes
def checkPulse(self):

	current_time = 0

	add_time = constant.constants.extraTime

	# the implementation of check pulse is different for gateways and other devices. 
	# we differentiate them based on the name as IDs can be assigned dynamically

	if self.name == "Gateway processing tier":

		# check if the time elapsed since last heartbeat is less than the 
		# heartbeat period or not. We add one second extra time to account 
		# for the delays in message propogation
		while (current_time - self.hbTime < (constant.constants.hbPeriod + add_time)):
			current_time = time.time()
			time.sleep(constant.constants.hbPeriod) #check periodically
			#print "{} has received the heartbeat message from {}".format(self.name, self.port)

		# if heartbeat has not be received, set the crash value to 1 and print gateway crashed.
		self.crash = 1

		print "One gateway has crashed."

		# when crash value is set to 1, the gateways stop sending the pulse. 
		# here we notify the devices connected to the alive gateway to not 
		# expect any heartbeat message from now on. 

		msg = [constant.constants.crashMessage, self.ID, constant.constants.broadcastRcvID, '']
		self.sendMessage(msg)

		# we also update the idlist to the one containing all the devices. 
		# the devices must have been registered with this gateway by now. Even if not,
		# this update don't have negative implications.

		self.idList = constant.constants.idList

	else: 
		# this part works for all the devices except gateways. 

		# check if the time elapsed since last heartbeat is less than the 
		# heartbeat period or not. We add one second extra time to account 
		# for the delays in message propogation
		if self.crash == 0: 
			while (current_time - self.hbTime < (constant.constants.hbPeriod + add_time)):
				current_time = time.time()
				time.sleep(constant.constants.hbPeriod)
				#print "{} has received the heartbeat message from {}".format(self.name, self.port)


		# once the gateway crashes, we wait for x second. 
		# we do this to give the live gateway enough time to 
		# inform its devices to not expect heartbeat by setting 
		# self.crash = 1
		# we do this to make it generic as otherwise self.crash will be zero for devices 
		# from the dead gateway and vice versa. It will deregister even alive devices.
			time.sleep(6)

			if self.crash == 1:
				pass 	# this condition will be triggered by the device connected to the live gateway. Thus
						# freeing them from taking any sort of action
			else: 
				# self.crash is still zero for the devices from the dead gateway. 
				# set it to 1
				self.crash = 1
				# unregister those devices from the daemon as otherwise registering gives error 
				# that the device alread have a Pyro id
				self.daemon.unregister(self)

				# if a device was connected to gateway 1, it attempts to register with 
				# gateway 2 and vice versa. 

				if self.port == constant.constants.serverPort1:
					self.port = constant.constants.serverPort2
					self.nameServer = Pyro4.locateNS(constant.constants.serverAddress2, constant.constants.serverPort2)
					self._registerProcess(self.daemon, self.nameServer)
					#register again with server 2
				elif self.port == constant.constants.serverPort2:
					self.port = constant.constants.serverPort1
					self.nameServer = Pyro4.locateNS(constant.constants.serverAddress1, constant.constants.serverPort1)
					#door(constants.constants.doorSensorID, self.daemon, self.nameServer)
					#print "calling register process"
					self._registerProcess(self.daemon, self.nameServer)
				self.crash = 1
		else: 
			pass

# pulse daemin thread
# keep sending heartbeat in regular intervals to all the connected nodes + other gateway
# once crash happends - stop sending heartbeat
def sendPulse(self):
	while (True):
		if self.crash == 0:
			# if crash has not happened, send heartbeat to all the connected devices
			msg = [constant.constants.hbMessage, self.ID, constant.constants.broadcastRcvID, '']
			self.sendMessage(msg)

			# also send the heartbeat to the other gateway.
			if self.port == constant.constants.serverPort1:
				try: 
					otherServer = Pyro4.locateNS(constant.constants.serverAddress2, constant.constants.serverPort2)
					recURI = otherServer.lookup(str(constant.constants.processingTierID))
					recProxy = Pyro4.Proxy(recURI)
					recProxy.receiveMessage(msg)
				except:
					pass
			elif self.port == constant.constants.serverPort2:
				try: 
					otherServer = Pyro4.locateNS(constant.constants.serverAddress1, constant.constants.serverPort1)
					recURI = otherServer.lookup(str(constant.constants.processingTierID))
					recProxy = Pyro4.Proxy(recURI)
					recProxy.receiveMessage(msg)
				except:
					pass

		else: 
			pass 

		# sleep for heartbeat interval
		time.sleep(constant.constants.hbPeriod)
		# send message to the 
######################################################

def logicalClock(msg):
	self.sendMessage(self, msg)

def get_idlist(nameserver_id):
	if nameserver_id == 1:
		try:
			ns = Pyro4.locateNS(constant.constants.serverAddress1, constant.constants.serverPort1)
		except Pyro4.errors.NamingError:
			return [-1]
	elif nameserver_id == 2:
		try:
			ns = Pyro4.locateNS(constant.constants.serverAddress2, constant.constants.serverPort2)
		except Pyro4.errors.NamingError:
			return [-1]		

	a = []
	for k in ns.list():
		a.append(k)
	#print a
	a = a[1:]
	idList = [int(i) for i in a]
	#print idList
	return idList
