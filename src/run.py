# This is the code that visits the warehouse.
from gatewaytier1 import gatProcess
import Pyro4
import config as constant
import sys
import user
import helpers

sys.excepthook = Pyro4.util.excepthook

# can be any random node to start the elction process
# r1 = constant.constants.doorSensorID
# r2 = constant.constants.tempSensorID

#ameServer = Pyro4.locateNS() # locating name server
ns1 = Pyro4.locateNS(constant.constants.serverAddress1, constant.constants.serverPort1)
ns2 = Pyro4.locateNS(constant.constants.serverAddress2, constant.constants.serverPort2)

r1 = helpers.get_idlist(1)[0]
r2 = helpers.get_idlist(2)[0]

# init election for gateway 1
#print r1
uri1 = ns1.lookup(str(r1))
recProc = Pyro4.Proxy(uri1)
recProc.init_election()

# init election for gateway 2
uri2 = ns2.lookup(str(r2))
recProc = Pyro4.Proxy(uri2)
recProc.init_election()

#uri = nameServer.lookup(str(constant.constants.userID)) # looking for registered object
#recProc = Pyro4.Proxy(uri)

# TEST CASES
# Uncomment one of these 3 test cases files to run that particular case

#user.user().start('../test/event_consistency')  # Refers to 'Test Case 2' in test.pdf doc - for consistency checking
#user.user().start('../test/event1')
#user.user().start('../test/event2')
user.user().start('../test/event3')

