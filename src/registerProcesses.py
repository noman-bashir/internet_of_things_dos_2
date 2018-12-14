import Pyro4
import config as constants
from doorsense import door
from tempsense import temperature
from motionsense import motion
from presencesense import presence
from smartbulb import bulb
from smartoutlet import outlet
from gatewaytier1 import gatProcess
from gatewaytier2 import gatDatabase
from user import user
import numpy as np
import os


daemon = Pyro4.Daemon()

nameServer1 = Pyro4.locateNS(constants.constants.serverAddress1, constants.constants.serverPort1)
nameServer2 = Pyro4.locateNS(constants.constants.serverAddress2, constants.constants.serverPort2)
nameServer = [nameServer1, nameServer2]

n = input("Input no. of devices to be registered (1-6): ")

list_of_devices = [door, motion, presence, bulb, outlet, temperature]

try: 
	os.remove('./id')
except:
	pass

file = open('./id','a')

j = 0
for d in list_of_devices: 
	j += 1
	if j <= n:
		d(j, daemon, nameServer)
		#print d	
		tmp = str(d)
		device = tmp.split('.')
		file.write(device[1] + ',' + str(j))
		file.write('\n')
file.write('Number' + ',' + str(n))
file.close()

gatProcess(constants.constants.processingTierID, daemon, nameServer1)
gatDatabase(constants.constants.databaseTierID, daemon, nameServer1)
gatProcess(constants.constants.processingTierID, daemon, nameServer2)
gatDatabase(constants.constants.databaseTierID, daemon, nameServer2)

#user(constants.constants.userID, daemon, nameServer1)
#user(constants.constants.userID, daemon, nameServer2)

print("All processes have been registered.")
daemon.requestLoop()