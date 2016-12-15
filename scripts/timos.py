#!/usr/bin/env python3

# scripts/timos.py
#
# Import/Export script for SROS.
#
# @author Andrea Dainese <andrea.dainese@gmail.com>
# @copyright 2014-2016 Andrea Dainese
# @license BSD-3-Clause https://github.com/dainok/unetlab/blob/master/LICENSE
# @link http://www.unetlab.com/
# @version 20160719

import getopt, multiprocessing, os, pexpect, re, sys, time
from datetime import datetime

username = 'admin'
password = 'admin'
conntimeout = 3     # Maximum time for console connection
expctimeout = 3     # Maximum time for each short expect
longtimeout = 115    # Maximum time for each long expect
timeout = 150        # Maximum run time (conntimeout is included)

def node_login(handler):
    # Send an empty line, and wait for the login prompt
    i = -1
    while i == -1:
        try:
            handler.sendline('\r\n')
            i = handler.expect([
                'Login:',
                '#'],
				timeout = 5)
        except:
            i = -1

    if i == 0:
        # Need to send username and password
        handler.sendline(username)
        try:
            handler.expect('Password:', timeout = expctimeout)
        except:
            print('ERROR: error waiting for "Password:" prompt.')
            node_quit(handler)
            return False

        handler.sendline(password)
        try:
            j = handler.expect(['#'], timeout = expctimeout)
        except:
            print('ERROR: error waiting for ["#"] prompt.')
            node_quit(handler)
            return False

        if j == 0:
            # Nothing to do
            return True
        else:
            # Unexpected output
            node_quit(handler)
            return False
    elif i == 1:
        # Config mode detected, need to exit
        handler.sendline('exit all')
        try:
            handler.expect('#', timeout = expctimeout)
        except:
            print('ERROR: error waiting for "#" prompt.')
            node_quit(handler)
            return False
        return True
    else:
        # Unexpected output
        node_quit(handler)
        return False

def node_quit(handler):
    if handler.isalive() == True:
        handler.sendline('logout\n')
    handler.close()

def config_get(handler):
    # Clearing all "expect" buffer
    while True:
        try:
            handler.expect('#', timeout = 0.1)
        except:
            break

    # Disable paging
    handler.sendline('environment no more')
    try:
        handler.expect('#', timeout = expctimeout)
    except:
        print('ERROR: error waiting for "#" prompt.')
        node_quit(handler)
        return False

    # Getting the config
    handler.sendline('admin display-config')
    try:
        handler.expect('# Finished', timeout = longtimeout)
    except:
        print('ERROR: error waiting for "#" prompt.')
        node_quit(handler)
        return False
    config = handler.before.decode()
	# Enable paging
    handler.sendline('environment more')
    print(str(datetime.now()))
    # Manipulating the config
    #config = re.sub('\r', '', config, flags=re.DOTALL)                                      # Unix style
    config = config.replace('\r', '')
    config = config.replace('admin display-config', '')
    #config = re.sub('.*Using [0-9]+ out of [0-9]+ bytes\n', '', config, flags=re.DOTALL)    # Header
    #config = re.sub('.*admin display-config', '', config, flags=re.DOTALL)          # Header
    #config = re.sub('.*environment more\n', '', config, flags=re.DOTALL)          # Footer
    #config = re.sub('.*logout.*', '', config, flags=re.DOTALL)          # Footer
    #config = re.sub('!\nend.*', '!\nend\n', config, flags=re.DOTALL)                        # Footer
    print(str(datetime.now()))
    return config

def config_put(handler):
    while True:
        try:
           i = handler.expect('CVAC-4-CONFIG_DONE', timeout)
        except:
           return False
        return True

def usage():
    print('Usage: %s <standard options>' %(sys.argv[0]));
    print('Standard Options:');
    print('-a <s>    *Action can be:')
    print('           - get: get the startup-configuration and push it to a file')
    print('           - put: put the file as startup-configuration')
    print('-f <s>    *File');
    print('-p <n>    *Console port');
    print('-t <n>     Timeout (default = %i)' %(timeout));
    print('* Mandatory option')

def now():
    # Return current UNIX time in milliseconds
    return int(round(time.time() * 1000))

def main(action, fiename, port):
    try:
        # Connect to the device
        tmp = conntimeout
        while (tmp > 0):
            handler = pexpect.spawn('telnet 127.0.0.1 %i' %(port))
            time.sleep(0.1)
            tmp = tmp - 0.1
            if handler.isalive() == True:
                break

        if (handler.isalive() != True):
            print('ERROR: cannot connect to port "%i".' %(port))
            node_quit(handler)
            sys.exit(1)

        if action == 'get':
            rc = node_login(handler)
            if rc != True:
               print('ERROR: failed to login.')
               node_quit(handler)
               sys.exit(1)
            config = config_get(handler)
            if config in [False, None]:
                print('ERROR: failed to retrieve config.')
                node_quit(handler)
                sys.exit(1)
            try:
                fd = open(filename, 'a')
                fd.write(config)
                fd.close()
            except:
                print('ERROR: cannot write config to file.')
                node_quit(handler)
                sys.exit(1)
        elif action == 'put':
			# Import Config is disabled here
            node_quit(handler)
            sys.exit(1)
            rc = config_put(handler)
            if rc != True:
                print('ERROR: failed to push config.')
                node_quit(handler)
                sys.exit(1)

            # Remove lock file
            lock = '%s/.lock' %(os.path.dirname(filename))

            if os.path.exists(lock):
                os.remove(lock)

            # Mark as configured
            configured = '%s/.configured' %(os.path.dirname(filename))
            if not os.path.exists(configured):
                open(configured, 'a').close()

        node_quit(handler)
        sys.exit(0)

    except Exception as e:
        print('ERROR: got an exception')
        print(type(e))  # the exception instance
        print(e.args)   # arguments stored in .args
        print(e)        # __str__ allows args to be printed directly,
        node_quit(handler)
        return False

if __name__ == "__main__":
    action = None
    filename = None
    port = None

    # Getting parameters from command line
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'a:p:t:f:', ['action=', 'port=', 'timeout=', 'file='])
    except getopt.GetoptError as e:
        usage()
        sys.exit(3)

    for o, a in opts:
        if o in ('-a', '--action'):
            action = a
        elif o in ('-f', '--file'):
            filename = a
        elif o in ('-p', '--port'):
            try:
                port = int(a)
            except:
                port = -1
        elif o in ('-t', '--timeout'):
            try:
                timeout = int(a) * 1000
            except:
                timeout = -1
        else:
            print('ERROR: invalid parameter.')

    # Checking mandatory parameters
    if action == None or port == None or filename == None:
        usage()
        print('ERROR: missing mandatory parameters.')
        sys.exit(1)
    if action not in ['get', 'put']:
        usage()
        print('ERROR: invalid action.')
        sys.exit(1)
    if timeout < 0:
        usage()
        print('ERROR: timeout must be 0 or higher.')
        sys.exit(1)
    if port < 0:
        usage()
        print('ERROR: port must be 32768 or higher.')
        sys.exit(1)
    if action == 'get' and os.path.exists(filename):
        usage()
        print('ERROR: destination file already exists.')
        sys.exit(1)
    if action == 'put' and not os.path.exists(filename):
        usage()
        print('ERROR: source file does not already exist.')
        sys.exit(1)
    if action == 'put':
        try:
            fd = open(filename, 'r')
            config = fd.read()
            fd.close()
        except:
            usage()
            print('ERROR: cannot read from file.')
            sys.exit(1)

    # Backgrounding the script
    end_before = now() + timeout
    p = multiprocessing.Process(target=main, name="Main", args=(action, filename, port))
    p.start()

    while (p.is_alive() and now() < end_before):
        # Waiting for the child process to end
        time.sleep(1)

    if p.is_alive():
        # Timeout occurred
        print('ERROR: timeout occurred.')
        p.terminate()
        sys.exit(127)

    if p.exitcode != 0:
        sys.exit(127)

    sys.exit(0)
