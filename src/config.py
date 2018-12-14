class constants:

	def retreive_device_ID(device_name):
		f = open('./id','r+')
		content = f.readlines()
		state_int = 0
		for i in range(len(content)):
				state_list = content[i].split(',')
				if state_list[0] == device_name:
					state_int = int(state_list[1])
		f.close()
		return state_int

	serverAddress1 = "localhost"
	serverPort1 = 9090

	serverAddress2 = "localhost"
	serverPort2 = 9091

	cacheSize = 3
	hbPeriod = 3

	extraTime = 1

	# to use logical clock or not
	# if =0 then clock sync will be used
	useLogicalClock = 0

	# to be set according to the scenario being tested
	# uncomment one of these lines
	# in given testcases , test2 should be occupied initially
	initialHomeState = "empty"
	#initialHomeState = "occupied"


	# assigning IDs to the processes

	totalProcesses = 8 			# this doesn't include user process

	no_of_devices = retreive_device_ID('Number')

	userID = 0
	doorSensorID = retreive_device_ID('door')
	motionSensorID = retreive_device_ID('motion')
	presenceSensorID = retreive_device_ID('presence')
	smartBulbID = retreive_device_ID('bulb')
	smartOutletID = retreive_device_ID('outlet')
	tempSensorID = retreive_device_ID('temperature')
	databaseTierID = 7
	processingTierID = 8 
	broadcastRcvID = 99

	idList1 = []
	idList2 = []
	idList = []
 
	for i in range(no_of_devices):
		k = i+1
		idList.append(k)
		if (k%2 == 0):
			idList1.append(k)
		elif (k%2 == 1):
			idList2.append(k)

	idList1.append(7)
	idList1.append(8)

	idList2.append(7)
	idList2.append(8)

	idList1.append(7)
	idList1.append(8)

	#print idList1, idList2

	#idList1 = [2, 4, 6, 7, 8] # maintaining the list as IDs can be assigned 
	#idList2 = [1, 3, 5, 7, 8]
	allIDs = [1,2,3,4,5,6,7,8]
	deviceIDs = []
	# by any other sophisticated mechanism


	# different message types

	userActivityMsg = 0
	pushMsg = 1
	controlStateMsg = 2
	pullMsg = 3
	leaderElectionMsg = 40
	leaderWinMsg = 41
	clockSyncMsg = 50
	clockSyncPollMsg = 51
	clockSyncOffsetMsg = 52
	logicalClockMsg = 60
	initLogCloclMsg = 61
	ackLogClockMsg = 62
	responseMsg = 7
	selectiveMsg = 8
	broadCastMsg = 9
	hbMessage = 911
	crashMessage = 1122

	# control signals

	turnOn = 'ON'
	turnOff = 'OFF'

	# burglar vs legit user

	validID = 1
	invalidID = 0

	# motion state

	motionSensed = 1
	motionNotSensed = 0

	# temperature limits

	lowestTemp = 10
	highestTemp = 60

	dummyPayload = 9999

	occupied = 1 # if user is at home
	empty = 0 # if user is outside

	ON = 1
	OFF = 0
