#How to Run

> pyro4-ns -p 9090

In a diff terminal/machine:

> pyro4-ns -p 9091

Or **you can use a port of your choice on any machine of your choice. Just make sure to mention it in the src/config.py config file**
The variables to edit are : serverAddress1 , serverPort1 , serverAddress2 , serverPort2


Now, run the registerProcesses.py to register all the processes and enter the number of processes to test load-balancing

*Note: All the output will also come in this terminal/machine*
*Note: This is only for load-balancing testing - for proper function all 6 processes need to be registered.*

> cd src
> python registerProcesses.py
Input no. of devices to be registered (1-6): 6


In a diff terminal/machine:
use the run.py file to start the process...

> cd src
> python run.py
