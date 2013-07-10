#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

# Note: if you run the python interpreter in the optimzed mode (-O),
# debug messages will be disabled.

# {{{ GNU GENERAL PUBLIC LICENSE

# This is the peer node of the P2PSP (Peer-to-Peer Simple Protocol)
# <https://launchpad.net/p2psp>.
#
# Copyright (C) 2013 Vicente Gonz�lez Ruiz.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# }}}

# Try running me as:
#
# ./splitter.py --source_hostname="localhost"
# ./gatherer.py --splitter_hostname="localhost" --source_hostname="localhost"
# vlc http://localhost:9999 &
# ./peer.py --splitter_hostname="localhost" --source_hostname="localhost"
# vlc http://localhost:9998 &

# {{{ Imports

'''
# VERSI�N B�SICA DEL PEER, no hay mensajes de hola por parte de los peers.
# Usar con splitter.py y gatherer.py (sin n�meros)
'''

import os
import logging
from colors import Color
import sys
import socket
import struct
import time
import argparse
import churn

# }}}

IP_ADDR = 0
PORT = 1

# Number of blocks of the buffer
#buffer_size = 32
buffer_size = 256

#cluster_port = 0 # OS default behavior will be used for port binding

# Port to communicate with the player
listening_port = 9998

# Splitter endpoint
#splitter_hostname = '150.214.150.68'
splitter_hostname = 'localhost'
splitter_port = 4552

# Number of bytes of the stream's header
#header_size = 1024*20*10
header_size = 1024*20

# Estas cuatro variables las deber�a indicar el splitter
#source_hostname = '150.214.150.68'
source_hostname = 'localhost'
source_port = 4551
channel = '134.ogg'
block_size = 1024

# Controls if the stream is sent to a player
_PLAYER_ = True

# Maximun number of blocks to receive from the splitter
number_of_blocks = 999999999


logging_levelname = 'INFO' # 'DEBUG' (default), 'INFO' (cyan),
                           # 'WARNING' (blue), 'ERROR' (red),
                           # 'CRITICAL' (yellow)

logging_level = logging.INFO

logging_filename = ''

console_logging = False
file_logging = True

weibull_scale = 0   #for churn. 0 means no churn.

# {{{ Args handing

print 'Argument List:', str(sys.argv)

parser = argparse.ArgumentParser(
    description='This is a peer node of a P2PSP network.')

parser.add_argument('--buffer_size',
                    help='size of the video buffer in blocks. (Default = {})'.format(buffer_size))

parser.add_argument('--channel',
                    help='Name of the channel served by the streaming source. (Default = {})'.format(channel))

parser.add_argument('--listening_port',
                    help='Port used to communicate with the player. (Default = {})'.format(listening_port))

parser.add_argument('--logging_levelname',
                    help='Name of the channel served by the streaming source. (Default = "{}")'.format(logging_levelname))

parser.add_argument('--logging_filename',
                    help='Name of the logging output file. (Default = "{})'.format(logging_filename))

parser.add_argument('--number_of_blocks',
                    help='Maximun number of blocks to receive from the splitter. (Default = {}). If not specified, the peer runs forever.'.format(number_of_blocks))

parser.add_argument('--source_hostname',
                    help='Hostname of the streaming source. (Default = {})'.format(source_hostname))

parser.add_argument('--source_port',
                    help='Listening port of the streaming source. (Default = {})'.format(source_port))

parser.add_argument('--splitter_hostname',
                    help='Hostname of the splitter. (Default = {})'.format(splitter_hostname))

parser.add_argument('--splitter_port',
                    help='Listening port of the splitter. (Default = {})'.format(splitter_port))

parser.add_argument('--no_player', help='Do no send the stream to a player.', action="store_true")

parser.add_argument('--churn', help='Scale parameter for the Weibull function, 0 means no churn. (Default = {})'.format(weibull_scale))

args = parser.parse_known_args()[0]
if args.buffer_size:
    buffer_size = int(args.buffer_size)
    print("Buffer size "+str(buffer_size))
if args.channel:
    channel = args.channel
if args.listening_port:
    listening_port = int(args.listening_port)
if args.logging_levelname == 'DEBUG':
    logging_level = logging.DEBUG
if args.logging_levelname == 'INFO':
    logging_level = logging.INFO
if args.logging_levelname == 'WARNING':
    logging_level = logging.WARNING
if args.logging_levelname == 'ERROR':
    logging_level = logging.ERROR
if args.logging_levelname == 'CRITICAL':
    logging_level = logging.CRITICAL
if args.logging_filename:
    logging_filename = args.logging_filename
if args.number_of_blocks:
    number_of_blocks = int(args.number_of_blocks)
if args.source_hostname:
    source_hostname = args.source_hostname
if args.source_port:
    source_port = int(args.source_port)
if args.splitter_hostname:
    splitter_hostname = args.splitter_hostname
if args.splitter_port:
    splitter_port = args.splitter_port
if args.no_player:
    _PLAYER_ = False
if args.churn:
    weibull_scale = int(args.churn)

# }}}

print 'This is a P2PSP peer node ...',
if __debug__:
    print 'running in debug mode'
else:
    print 'running in release mode'


# {{{ Logging initialization

# create logger
logger = logging.getLogger('peer (' + str(os.getpid()) + ')')
logger.setLevel(logging_level)

# create console handler and set the level
if console_logging == True:
    ch = logging.StreamHandler()
    ch.setLevel(logging_level)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)

#jalvaro
# create file handler and set the level
if args.logging_filename and file_logging == True:
    fh = logging.FileHandler('/home/jalvaro/workspaces-eclipse/P2PSP-sim-cluster/sim/sim-cluster/output/peer-'+str(os.getpid()))
    fh.setLevel(logging_level)
    #add fh to logger
    logger.addHandler(fh)
#jalvaro: create a file handler for the critical level, to store times. I know I shouldn't be using critical :D
fh_timing = logging.FileHandler('/home/jalvaro/workspaces-eclipse/P2PSP-sim-cluster/sim/sim-cluster/timing/peer-'+str(os.getpid()))
fh_timing.setLevel(logging.CRITICAL)
logger.addHandler(fh_timing)

# }}}



source = (source_hostname, source_port)
splitter = (splitter_hostname, splitter_port)

def get_player_socket():
    # {{{

    #sock = blocking_TCP_socket.blocking_TCP_socket(socket.AF_INET, socket.SOCK_STREAM)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # In Windows systems this call doesn't work!
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except:
        pass
    sock.bind(('', listening_port))
    sock.listen(0)

    if __debug__:
        logger.info(Color.cyan + '{}'.format(sock.getsockname()) + ' waiting for the player on port ' + str(listening_port) + Color.none)
    # }}}

    #sock, player = sock.baccept()
    sock, player = sock.accept()
    sock.setblocking(0)
    return sock

    # }}}

if _PLAYER_:
    player_sock = get_player_socket() # The peer is blocked until the
                                      # player establish a connection.

    # {{{ debug

    if __debug__:
        logger.debug('{}'.format(player_sock.getsockname()) +
                     ' The player ' +
                     '{}'.format(player_sock.getpeername()) +
                     ' has establised a connection')

    # }}}

def communicate_the_header():
    # {{{ 
    source_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    source_sock.connect(source)
    source_sock.sendall("GET /" + channel + " HTTP/1.1\r\n\r\n")

    # {{{ Receive the video header from the source and send it to the player

    # Nota: este proceso puede fallar si durante la recepci�n de los
    # bloques el stream se acaba. Habr�a que realizar de nuevo la
    # petici�n HTTP (como hace el servidor).

    if __debug__:
        logger.info(Color.cyan + str(source_sock.getsockname()) + ' retrieving the header ...' + Color.none)

    data = source_sock.recv(header_size)
    total_received = len(data)
    player_sock.sendall(data)
    while total_received < header_size:
        if __debug__:
            logger.debug(str(total_received))
        data = source_sock.recv(header_size - len(data))
        player_sock.sendall(data)
        total_received += len(data)

    # }}}

    if __debug__:
        logger.info(Color.cyan  + str(source_sock.getsockname()) + ' done' + Color.none)
    
    source_sock.close()
    # }}}

if _PLAYER_:
    communicate_the_header() # Retrieve the header of the stream from the
                             # source and send it to the player.

# {{{ debug
if __debug__:
    logger.debug(" Trying to connect to the splitter at" + str(splitter))
# }}}

def connect_to_the_splitter():
    # {{{
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(splitter)
    return sock

    # }}}

# COMIENZO DE BUFFERING TIME    
start_buffering_time = time.time()

splitter_sock = connect_to_the_splitter() # Connect to the splitter in
                                          # order to tell it who the
                                          # gatherer is.
splitter = splitter_sock.getpeername() # "localhost" -> "127.0.0.1"

if __debug__:
    logger.info(Color.cyan + '{}'.format(splitter_sock.getsockname()) + ' connected to the splitter' + Color.none)

def create_cluster_sock():
    # {{{

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # In Windows systems this call doesn't work!
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except:
        pass
    sock.bind(('',splitter_sock.getsockname()[PORT]))
    return sock

   # }}}
cluster_sock = create_cluster_sock()
cluster_sock.settimeout(1)

# {{{ This is the list of peers of the cluster. Each peer uses this
# structure to resend the blocks received from the splitter to these
# nodes.  }}}
peer_list = []

# {{{ This store the insolidarity of the peers of the cluster. When
# the solidarity exceed a threshold, the peer is deleted from the list
# of peers.  }}}
peer_insolidarity = {}

gatherer = None

def retrieve_the_list_of_peers():
    # {{{
    global gatherer
    number_of_peers = socket.ntohs(
        struct.unpack("H",splitter_sock.recv(struct.calcsize("H")))[0])

    # {{{ debug
    
    if __debug__:
        logger.debug('{}'.format(splitter_sock.getsockname()) +
                     ' <- ' +
                     '{}'.format(splitter_sock.getpeername()) +
                     ' Cluster size = ' +
                     str(number_of_peers))

    # }}}
    message = splitter_sock.recv(struct.calcsize("4sH"))
    IP_addr, port = struct.unpack("4sH", message)
    IP_addr = socket.inet_ntoa(IP_addr)
    port = socket.ntohs(port)
    gatherer = (IP_addr, port)
    while number_of_peers > 0:
        message = splitter_sock.recv(struct.calcsize("4sH"))
        IP_addr, port = struct.unpack("4sH", message)
        IP_addr = socket.inet_ntoa(IP_addr)
        port = socket.ntohs(port)
        peer = (IP_addr, port)

        # {{{ debug

        if __debug__:
            logger.debug('{}'.format(splitter_sock.getsockname()) +
                         ' <- ' +
                         '{}'.format(splitter_sock.getpeername()) +
                         ' Peer ' +
                         str(peer))

        # }}}

        peer_list.append(peer)
        peer_insolidarity[peer] = 0

        cluster_sock.sendto('', peer) # Send a empty block (this
                                      # should be fast)

        number_of_peers -= 1

    # }}}

retrieve_the_list_of_peers()

splitter_sock.close()

# {{{ In this momment, most of the rest of peers of the cluster are
# sending blocks to the new peer.
# }}}

# {{{ We define the buffer structure. Two components are needed: (1)
# the blocks buffer that stores the received blocks (2) the received
# buffer that stores if a block has been received or not.
# }}}
blocks = [None]*buffer_size
received = [False]*buffer_size

# True if the peer has received "number_of_blocks" blocks.
blocks_exhausted = False

# This variable holds the last block received from the splitter. It is
# used below to send the "last" block in the congestion avoiding mode.
last = ''

# Number of times that the last block has been sent to the cluster (we
# send the block each time we receive a block).
counter = 0

def receive_and_feed():
    global last
    global counter
    global blocks_exhausted
    global number_of_blocks

    try:
        # {{{ Receive and send
        message, sender = cluster_sock.recvfrom(struct.calcsize("H1024s"))
        if len(message) == struct.calcsize("H1024s"):
            # {{{ Received a video block
            number, block = struct.unpack("H1024s", message)
            block_number = socket.ntohs(number)
            # {{{ debug
            if __debug__:
                logger.debug('{}'.format(cluster_sock.getsockname()) +
                             " <- " +
                             '{}'.format(block_number) +
                             ' ' +
                             '{}'.format(sender))

            # }}}
            blocks[block_number % buffer_size] = block
            received[block_number % buffer_size] = True

            if sender == splitter:
                # {{{ Send the previously received block in burst mode.

                cluster_sock.sendto(message, gatherer)
                # {{{ debug
                if __debug__:
                    logger.debug('{}'.format(cluster_sock.getsockname()) +
                                 ' ' +
                                 str(block_number) +
                                 ' -> (gatherer) ' +
                                 '{}'.format(gatherer))

                # }}}

                if __debug__:
                        logger.debug("Sending block "+str(block_number)+" in burst mode")
                        logger.debug("Counter value: "+str(counter))

                while( (counter < len(peer_list)) & (counter > 0)):
                    peer = peer_list[counter]

                    if __debug__:
                        logger.debug("Counter: "+str(counter)+", Peer"+str(peer))

                    cluster_sock.sendto(last, peer)
    #                if not is_player_working:
    #                    cluster_sock.sendto('', peer)

                    peer_insolidarity[peer] += 1
                    if peer_insolidarity[peer] > 64: # <- Important parameter!!
                        del peer_insolidarity[peer]
                        peer_list.remove(peer)
                        if __debug__:
                            logger.info(Color.cyan + str(cluster_sock.getsockname()) + ' peer ' + str(peer) + ' removed' + Color.none)

                    counter += 1

                    # {{{ debug
                    if __debug__:
                        logger.debug('{}'.format(cluster_sock.getsockname()) +
                                     ' ' +
                                     str(block_number) +
                                     ' -> (peer) ' +
                                     '{}'.format(peer))

                    # }}}

                counter = 0
                last = message
                '''
                if args.number_of_blocks:
                    number_of_blocks -= 1
                    if number_of_blocks <= 0:
                        blocks_exhausted = True
'''
                # }}}
            else:
                # {{{ Check if the peer is new

                if sender not in peer_list:
                    # The peer is new
                    peer_list.append(sender)
                    if __debug__:
                        logger.info(Color.cyan + str(cluster_sock.getsockname()) + ' peer ' + str(sender) + ' added by data block' + Color.none)
                peer_insolidarity[sender] = 0

                # }}}

            if counter < len(peer_list):
                # {{{ Send the last block in congestion avoiding mode

                peer = peer_list[counter]
                cluster_sock.sendto(last, peer)

                peer_insolidarity[peer] += 1        
                if peer_insolidarity[peer] > 64: # <- Important parameter!!
                    del peer_insolidarity[peer]
                    peer_list.remove(peer)
                    if __debug__:
                        logger.info(Color.cyan + str(cluster_sock.getsockname()) + ' peer ' + str(peer) + ' removed by unsupportive' + Color.none)

                # {{{ debug
                if __debug__:
                    logger.debug('{}'.format(cluster_sock.getsockname()) +
                                 ' ' +
                                 str(block_number) +
                                 ' -> (peer) ' +
                                 '{}'.format(peer))

                # }}}
                
                counter += 1        
            
                # }}}

            if args.number_of_blocks:
                number_of_blocks -= 1
                if number_of_blocks <= 0:
                    blocks_exhausted = True


            return block_number
            # }}}
        elif message=='':
            # {{{ Received a control block

            if sender not in peer_list:
                peer_list.append(sender)
                peer_insolidarity[sender] = 0
                if __debug__:
                    logger.info(Color.cyan + str(cluster_sock.getsockname()) + ' peer ' + str(sender) + ' added by control block' + Color.none)
            else:
                peer_list.remove(sender)
                if __debug__:
                    logger.info(Color.cyan + str(cluster_sock.getsockname()) + ' peer ' + str(sender) + ' removed by control block' + Color.none)
            return -1
            # }}}
        # }}}
    except socket.timeout:
        # {{{
        if __debug__:
            logger.warning(Color.red + "cluster timeout!" + Color.none) 
        return -2
        # }}}

# {{{ debug
if __debug__:
    logger.debug(str(cluster_sock.getsockname()) + ' buffering ...')
# }}}

if __debug__:
    logger.info(Color.cyan + str(cluster_sock.getsockname()) + ' receiving data ...' + Color.none)

'''
#Fill half the buffer
'''
#WARNING!!!
#time.clock() measures the time spent by the process (so the time spent waiting for an execution slot in the processor is left out)
#time.time() measures wall time, this means execution time plus waiting time

last_block_number = 0
error_counter = 0

block_number = receive_and_feed()
while block_number<=0:
    block_number = receive_and_feed()
block_to_play = block_number % buffer_size
for x in xrange(buffer_size/2):
    while receive_and_feed()<=0:
        pass
#go through the buffer
num_errors_buf = 0
for x in range(block_to_play, block_to_play+(buffer_size/2)):
    if received[x%buffer_size] == False:
        num_errors_buf += 1

'''
block_number = receive_and_feed()
while block_number<=0:
    block_number = receive_and_feed()
block_to_play = block_number % buffer_size
for x in xrange(buffer_size/2):
    last_block_number = receive_and_feed()
    if last_block_number <= 0:
        error_counter += 1
'''

# FIN DE BUFFERING TIME
end_buffering_time = time.time()
buffering_time = end_buffering_time - start_buffering_time

if __debug__:
    logger.info(str(cluster_sock.getsockname()) + ' buffering done')
    logger.info('NUM_PEERS '+str(len(peer_list)))
    logger.critical('BUF_TIME '+str(buffering_time)+' secs')   #buffering time in SECONDS
    logger.critical('BUF_LEN '+str(buffer_size)+' bytes')
    logger.critical('NUM_ERRORS_BUF '+str(error_counter))
    percentage_errors_buf = float(error_counter*100)/float(buffer_size/2)
    logger.critical('PERCENTAGE_ERRORS_BUF ' + str(percentage_errors_buf))
    #logger.critical('PERCENTAGE_ERRORS_BUF {:.2}%'.format(percentage_errors_buf))
    logger.critical('NUM_PEERS '+str(len(peer_list)))
    # }}}

'''
#End buffering
'''

player_connected = True

def send_a_block_to_the_player():
    # {{{

    global block_to_play
    global player_sock
    global player_connected

    if not received[block_to_play]:
        message = struct.pack("!H", block_to_play)
        cluster_sock.sendto(message, splitter)

        if __debug__:
            logger.info(Color.cyan + str(cluster_sock.getsockname()) + ' complaining about lost block ' + str(block_to_play) + Color.none)

        # La mayor�a de los players se sincronizan antes si en lugar
        # de no enviar nada se env�a un bloque vac�o. Esto habr�a que
        # probarlo.

    try:
        player_sock.sendall(blocks[block_to_play])

        # {{{ debug
        if __debug__:
            logger.debug('{}'.format(player_sock.getsockname()) +
                         ' ' +
                         str(block_to_play) +
                         ' -> (player) ' +
                         '{}'.format(player_sock.getpeername()))

        # }}}

    except socket.error:
        if __debug__:
            logger.error(Color.red + 'player disconected!' + Color.none)
        player_connected = False
        return
    except Exception as detail:
        if __debug__:
            logger.error(Color.red + 'unhandled exception ' + str(detail) + Color.none)
        return

    received[block_to_play] = False

    # }}}
    
#get a death time
#death_time = churn.new_death_time(20)
death_time = churn.new_death_time(weibull_scale)

'''
#Once the buffer is half-filled, then start operating normally
'''
#while player_connected and not blocks_exhausted:
while player_connected and not churn.time_to_die(death_time):
    
    if __debug__ and death_time != churn.NEVER:
        current_time = time.localtime()
        logger.debug(Color.green+'Current time is '+str(current_time.tm_hour).zfill(2)+':'+str(current_time.tm_min).zfill(2)+':'+str(current_time.tm_sec).zfill(2)+Color.none)
        logger.debug(Color.green+'Scheduled death time is '+str(time.localtime(death_time).tm_hour).zfill(2)+':'+str(time.localtime(death_time).tm_min).zfill(2)+':'+str(time.localtime(death_time).tm_sec).zfill(2)+Color.none)
    
    block_number = receive_and_feed()
    if block_number>=0:
        if (block_number % 256) == 0:
            for i in peer_insolidarity:
                peer_insolidarity[i] /= 2
        if _PLAYER_:
            send_a_block_to_the_player()
            block_to_play = (block_to_play + 1) % buffer_size
    #elif block_number == -2:    #this stops the peer after only one cluster timeout
    #    break
    if __debug__:
        logger.debug('NUM PEERS '+str(len(peer_list)))
    
if __debug__:
    logger.info(Color.cyan + 'Goodbye!' + Color.none)
goodbye = ''
cluster_sock.sendto(goodbye, splitter)
for x in xrange(3):
    receive_and_feed()
for peer in peer_list:
    cluster_sock.sendto(goodbye, peer)

