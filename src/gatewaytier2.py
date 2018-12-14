import Pyro4
import config as constant
from multiprocessing import Lock
import time
import helpers

# 2 Database files

# ./database - logs all the events according the timestamps

# ./state_database - has rows corresponding the each device whose state is of interest

@Pyro4.expose
class gatDatabase: 
	def __init__(self, ID, daemon, nameServer):
		self.ID = ID 
		self.name = "Gateway database tier"
		self.nameServer = nameServer
		self._registerProcess(daemon, nameServer)

		self.port = int(nameServer.list()['Pyro.NameServer'][-4:])

		if self.port == constant.constants.serverPort1:
			self.idList = constant.constants.idList1
			self.dbfile = './database1'
			self.statedb = './state_database1'
		elif self.port == constant.constants.serverPort2:
			self.idList = constant.constants.idList2
			self.dbfile = './database2'
			self.statedb = './state_database2'



		self.recv_ok = False
		self.election_done = False
		self.election_lock = Lock()
		
		self.leader = -1
		self.time_dict = {}
		self.offset = 0.0


		# Also participates in leader election algorithm 
		# but does not participate in time sync (unless it's the leader and it has to coordinate)
	def init_election(self):		
		helpers.init_election(self)
		
	def process_election(self,msg):		
		helpers.process_election(self,msg)		

	def set_leader(self,msg):
		helpers.set_leader(self,msg)

	def ok(self):
		helpers.ok(self)


	def poll_clocks(self):
		helpers.poll_clocks(self)

	def leader_recv_timestamp(self,msg):
		#senders_time = msg[3]
		from_ = msg[1]
		self.time_dict[from_] = msg[3]
		return

	# inset sequential events into the ./database file
	# timestamp included 
	def insert(self,msg):
		sender = msg[1]
		data = msg[3]
		timestamp = msg[4]
		st = "{}, {}, {}".format(sender, data, timestamp)
		file = open(self.dbfile,'a')
		file.write(st)
		file.write('\n')
		file.close()

		# gets all the events in the order in which it was inserted
	def retrieve_all(self):
		all_events = []
		time.sleep(0.3) # simulated database delay
		with open(self.dbfile,'r+') as fobj:
			for line in fobj:
		            curr_event = [ch for ch in line.split(',')]
		            all_events.append(curr_event)
	        return all_events

	def print_all(self,timestamp):
		print "CONSISTENCY CHECK - At time {}, {} is".format(timestamp,self.dbfile)
		print self.retrieve_all()

	        #get last event - excluding the event with just happened - as a response to which this func is called
	        # so effictively get the 2nd highest event
	def retrieve_last(self):
		all_events = self.retrieve_all()
		if len(all_events) == 0:
			return ['-1',None,None]
		all_times = [float(e[2]) for e in all_events]
		#	print all_times,'TTTTTTT'

		# max_idx will be current event when event order lofic processed
		# get 2nd highest
		all_times.remove(max(all_times))
		if all_times == []:
			return ['-1',None,None]
		max_idx = all_times.index(max(all_times))
		
		return all_events[max_idx]


		# Deals with 2nd type of database : ./state_database

		# fetch the correspondinf row of the deviceId
		# and update with the new state
	def update_device_state(self,deviceID,state):
		f = open(self.statedb,'r+')
		content = f.readlines()
		for i in range(len(content)):
			if int(content[i][0]) == deviceID:
				content[i] = '{}, {}\n'.format(deviceID,state)
		f.seek(0)
		f.truncate()
		for c in content:
			f.write(c)
		f.close()

		# get func for ./state_datase
		# read that row and report the state as a string
	def retreive_device_state(self,deviceID):
		f = open(self.statedb,'r+')
		content = f.readlines()
		for i in range(len(content)):
			if int(content[i][0]) == deviceID:
				state_str = content[i].split(',')[1][1:-1]
		f.close()
		return state_str



		# receive message handling similar to gateway - no threaded
	def receiveMessage(self, msg):
		# this function is called by the push-based sensors 
		# to send their state to the gateway
		msgType = msg[0]
		if msgType == constant.constants.leaderElectionMsg:
			self.process_election(msg)
		elif msgType == constant.constants.leaderWinMsg:
			self.set_leader(msg)
		elif msgType==constant.constants.clockSyncMsg:
			self.leader_recv_timestamp(msg)
		

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
		print("{} has been registered with ID: {}").format(self.name, self.ID)
