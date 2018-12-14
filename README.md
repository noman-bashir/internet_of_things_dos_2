# How to Run

Note: A pre-req is Pyro4 installed in any standard Linux machine

1. 2 Different Pyro Nameserver needs to be up for Replication
2. Process should be registered 
3. Start the process with specific test cases

1. Start the name server using 

> pyro4-ns -p 9090

In a diff terminal/machine:

> pyro4-ns -p 9091

Or **you can use a port of your choice on any machine of your choice. Just make sure to mention it in the src/config.py config file**
The variables to edit are : serverAddress1 , serverPort1 , serverAddress2 , serverPort2


2. Now, run the registerProcesses.py to register all the processes and enter the number of processes to test load-balancing

*Note: All the output will also come in this terminal/machine*
*Note: This is only for load-balancing testing - for proper function all 6 processes need to be registered.*

> cd src
> python registerProcesses.py
Input no. of devices to be registered (1-6): 6


3. In a diff terminal/machine:
use the run.py file to start the process...

> cd src
> python run.py

**Note: some threads run as daemon in background, so when all events done use Ctrl+C to exit the registerProcess terminal**

# Configure HeartBeat Duration and Cache Size

As mentioned in req, we have made the cache size and the heartbeat duration configurable. Again, the config file is src/config.py 
The related values are:

For Cache Size : cacheSize

For HeartBeat Duration : hbPeriod

# Switch between Test Cases

To switch between test cases, simply comment out 2 of the lines and leave one remaining in the run.py file.

The description and expected outputs are provided in test/output.txt

# Database Structure

2 Database files are present both are Consistency ensured:

 ./database - logs all the events according the timestamps, used in ordering events by fetchinf last timestamped event

 ./state_database - has rows corresponding the each device whose state is of interest, used for recording current state of each device


# Running on Diff Machines

The code is tested and able to run on multiple machines. The object of interest is the pyro Name Server

Set the host-address and port number of the Pyro Name Server Process in src/config.py using the serverAddress1, serverPort1, serverAddress2, serverPort2 attributes



