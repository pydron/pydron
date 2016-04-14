
Pydron - Semi-automatic parallelization
=============================================================

Pydron takes sequential python code and runs it in parallel
on multiple cores, clusters, or cloud infrastructures.

----------------------
Let's get going!
----------------------

.. code-block:: python

	import pydron
   
	@pydron.schedule
	def calibration_pipeline(inputs):
  		outputs = []
  		for input in inputs: 
  			output = process(input)
   			outputs = outputs + [output]
   		return outputs
   	
   	@pydron.functional
   	def process(input):
   		...
   	
This will run all `process` calls in parallel.



.. _api:

----------------------
API
----------------------

.. py:module:: pydron

Pydron's API consists of only two decorators:

.. py:decorator:: pydron.schedule

	Pydron will only parallelize code with this decorator.
	All other code will run as usual.
	
	The function may contain arbitrary code with the
	exception of `try except`, `try finally`, and `with` 
	statements that are not yet implemented.
	
	While arbitrary code is allowed and should
	(in theory at least, there are bugs) produce correct
	results, not every code can be made to run in
	parallel. See  :ref:`best-pratices` for guide lines.
	
.. py:decorator:: pydron.functional

	Pydron can only run function calls in parallel if the
	functions have this decorator. 
	
	The decorator defines a contract between the developer
	and Pydron. The developer may decorate a function
	with `functional` if the following conditions are met:
	
	* The function does not assign global variables or as
	  any other kind of side effects.
	
	* If the function reads global variables they must have
	  been unchanged since the module was loaded. This is
	  typically the case for classes and functions defined
	  in a module. What is excluded is access to dynamic
	  state stored globally.
	  
	* All arguments passed to the function must be serializable
	  with `pickle`.
	  
	* The return value or the thrown exception must be serializable
	  with `pickle`.
	  
	* The function does not modify the objects that are passed
	  as arguments. Often you can return modified copies instead.
	  
	

.. _best-pratices:

----------------------
Best practices
----------------------

Pydron can run two function calls in parallel if the following conditions
are met:

 * The return value of one is not an argument of the other, directly or
   indirectly.
   
 * Both have the :func:`pydron.functional` decorator.
 
 * The code which, in a sequential execution, would be executed between the
   two, must be free of `sync-points` (see below).
  
^^^^^^^^^^^^^^^^^^^^^
Synchonization points
^^^^^^^^^^^^^^^^^^^^^
   
A `sync-point` is an operation that Pydron cannot reason about. It therefore
executes that operation at the same 'time' as it would in a sequential execution.
That is, every operation that comes before must have finished and
all operations that come afterwards have to wait. 

A single `sync-point` inside
a loop forces the iterations to run one after the other, making
parallelism impossible. Therefore `sync-point` should be avoided.

The following operations cause a `sync-point`:

 * Calls to functions without the :func:`pydron.functional` decorator.
   Currently, this includes pretty much all built-in functions
   and functions from libraries since I haven't populated the
   white-lists yet.
 
 * Operations that modify an object. These include:
 
   * Assigning an attribute: `obj.x = ...`
   
   * Assigning a subscript: `obj[i] = ...`
   
   * Augmented Assignment: `obj += ...`
   
   The last one might be a bit surprising since `x += 1`
   is often to be identical to `x = x + 1`. But this might not be
   the case. Some types, including `list` and `numpy.ndarray`, 
   perform the operation in-place, modifying the object instead
   of creating a new one. Pydron currently treads all augmented assignments
   as sync-points, even for data types such as integers. 

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Unsupported Language Features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There some features of the Python language that have not made it into
this release:
 
 * `try`, `except`, `finally`. Exceptions thrown within `@schedule` functions
   are forwarded to the caller, but exception handing within the function
   is not yet implemented.
   
 * `yield`. This statement transforms a function into a generator. 
   `@schedule` functions don't support this right now.

 * Generator expressions `(x for x in y)`. While `list`, `set` and `dict` comprehensions
   works fine, the ones with round brackets are a very different beast.
   They are syntactic sugar around a nested function that contains the loop
   and uses `yield` for the values. Lacking support `yield`, Pydron cannot
   currently support generator expressions.
   
   
----------------------
Configuration
----------------------

Pydron uses a configuration file to figure out where to run the parallel
tasks.

This configuration file must be named `pydron.conf` and is searched in the 
following locations:

 * Path stored in environment variable `PYDRON_CONF`
 * Within the current working directory
 * Within the user's home directory
 * `/etc/pydron.conf`
 
These are in order searched.

The configuration file is in JSON format. 

^^^^^^^^^^^^^^^^^^^^^
Multi-Core Setup
^^^^^^^^^^^^^^^^^^^^^

A typical configuration file to use multiple cores on the local machine
would look like this::

	{
	    "workers": [
	        {
	        "type":"multicore",
	        "cores":4
	        }
	    ]
	}

This will start four additional Python interpreters on the local machine when
the `@schedule` decorated function is invoked. It will also terminate them
afterwards.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Remote workers with SSH
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To use more than just the cores available locally, we can also connect
to a remote machine::

	{
	    "workers": [
	        {
		        "type":"ssh",
		        "hostname":"node1.mydomain.tld",
		        "username":"myusername",
		        "password":"mypassword",
		        "tmp_dir":"/tmp",
		        "data_ports":"10000-10010",
		        "cores":4,
	        }
	    ]
	}

This will start four Python interpreters on `node1.mydomain.tld`. 

Pydron is using TCP connections to talk to the processes started. The started
processes open ports within the range given with `data_ports`. Since each
process is opening a port, the range must contain at least as many ports
as `cores`.

is the port range 

To use more than just one remote machine, put multiple entries into the
`workers` configuration section::

	{
	    "workers": [
	        {
		        "type":"ssh",
		        "hostname":"node1.mydomain.tld",
		        "username":"myusername",
		        "password":"mypassword",
		        "tmp_dir":"/tmp",
		        "data_ports":"10000-10010",
		        "cores":4
	        },
	        {
		        "type":"ssh",
		        "hostname":"node2.mydomain.tld",
		        "username":"myusername",
		        "password":"mypassword",
		        "tmp_dir":"/tmp",
		        "data_ports":"10000-10010",
		        "cores":4
	        },
	        {
		        "type":"ssh",
		        "hostname":"node3.mydomain.tld",
		        "username":"myusername",
		        "password":"mypassword",
		        "tmp_dir":"/tmp",
		        "data_ports":"10000-10010",
		        "cores":4
	        }
	    ]
	}

In this example, 12 cores would be used.

If things go wrong, it can happen that processes keep running on the remote
machine. There are a few safety mechanisms in place to avoid this, but
they are not perfect. I recommend checking occasionally if there are some
processes left over, especially after a run hasn't cleanly completed.

^^^^^^^^^^^^^^^^^^^^^
Cloud Computing
^^^^^^^^^^^^^^^^^^^^^

You can also let Pydron start instances in the cloud. Pydron is using Apache 
libcloud, so we should support a wide range of cloud providers. I have
only tried this with Amazon EC2 though.
 
There are a few important issues you need to be aware of:

 * Pydron cannot guarantee that the instances will be terminated in all
   cases. It will try, but there is always a risk that instances are
   left behind. **THESE WILL STILL COST YOU MONEY**. Check afterwards
   if everything was terminated properly. Accidentally running hundreds of big 
   instances over the weekend will get really expensive. You've been warned. 
   Don't send the bill to me.
   
 * The instances are started when the `@schedule` decorated function is invoked
   and a 'best effort' attempt is made to terminate them at the end. 
   
   Depending on the cloud provider they might not charge you by the minute
   but by the hour or by some other interval. If the execution takes only five
   minutes you might still end up paying for a longer period.
   
   Ideally, Pydron would keep the instances running so that you can do several
   runs without starting and stopping the instances every time. This is not
   yet been implemented.
   
The configuration file for EC2 will look like this::

	{
	    "workers": [
	        {
		        "type":"cloud",
		        "username":"root",
		        "provider":"ec2_us_east",
		        "accesskeyid":"ABCDEF.....",
		        "accesskey":"AbDef012+Z...",
		        "imageid":"ami-abcdef",
		      	"sizeid":"t1.micro",
		      	"publickey":"C:\...\id_rsa.pub",
		      	"privatekey":"C:\...\id_rsa",
		      	"tmp_dir":"/tmp",
		      	"data_ports":"10000-10010",
		      	"count":10
	        }
	    ]
	}

This will start ten `t1.micro` instances with the `ami-abcdef` machine image.

We don't currently provide an image, but any Linux image able to run Python 2.7
should do. Make sure that Pydron is installed there too. 

Pydron will connect with SSH and login as 
`root` with the given privatekey and run a command like this::

	/usr/bin/env python -c "..."
	
It will also upload a file to `tmp_dir` with SFTP. It is a good idea to have
Pydron installed in the image. It's not strictly required, but it will ensure
that the required libraries are in place.


----------------------
Common Pitfalls
----------------------

* "connection closed cleanly" while opening the SSH connection used to
  start remote processes.
  
  There is a limitation of the twisted-conch library that Pydron is
  using. It does not support all key-exchange algorithms. Some recent versions
  of linux distributions (Ubuntu, for example) deactivated some algorithms
  by default. The result is that twisted-conch and the ssh server cannot agree
  on an algorithm for the key exchange. Twisted-conch produces a rather
  non-sense "closed cleanly" error message as a result.
  
  The proper solution would be to add support for the missing algorithms, but
  for now, we can tell the ssh server to accept the deprecated algorithms by 
  adding a line to `/etc/ssh/sshd_config`::
  
    KexAlgorithms curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group-exchange-sha256,diffie-hellman-group14-sha1,diffie-hellman-group1-sha1

  To which degree this compromizes the security of the server, I cannot say.
  