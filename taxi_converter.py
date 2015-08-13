#!/bin/python
'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import sys
import argparse
from argparse import RawTextHelpFormatter
from geopy.distance import vincenty
from time import strptime, mktime
from datetime import datetime

__author__ = "Juliano Fischer Naves"
__license__ = "GPL Version 3"
__email__ = "julianofischer@gmail.com"

UNINITIALIZED = -1
clock = 0
current_datetime = UNINITIALIZED
previous_datetime = UNINITIALIZED
node_positions = {}
args = UNINITIALIZED
open_connections = {}
range = UNINITIALIZED

def conf_argparser():
    description = "Author: "+__author__ + "\nemail: " + __email__ + "\nLicense: " + __license__ + "\n" '\nProcess the datatrace input and creates a new file containing a connection trace.'

    parser = argparse.ArgumentParser(description=description, formatter_class=RawTextHelpFormatter)
    parser.add_argument('--range',nargs='?',help="The theoretical transmission range.", default=100,type=int)
    parser.add_argument('--output',nargs='?',help="The output filename.", default='output.txt')
    parser.add_argument('datatrace',nargs=1,help="the datatrace file")
    args=parser.parse_args()
    return args

def convert_to_dict(line):
    line = line.split(';')
    id = int(line[0])
    
    date_time = line[1].split('+01')[0].split('.')[0]
    position = line[2].split(' ')
    x_position = float(position[0].split('POINT(')[1])
    y_position = float(position[1].split(')')[0])

    assert x_position >= -90
    assert x_position <= 90
    assert y_position >= -180
    assert y_position <= 180

    position = (x_position, y_position)
    #structured_time = strptime(date_time,'%Y-%m-%d %H:%M:%S.%f')
    structured_time = strptime(date_time,'%Y-%m-%d %H:%M:%S')

    #converting do datetime
    structured_time = datetime.fromtimestamp(mktime(structured_time))
    
    #creating dict item
    my_dict = {"id":id, "position": position, "date_time":structured_time}
    return my_dict

def consumes_line(line):
    line = convert_to_dict(line)
    global previous_datetime
    global current_datetime
    global node_positions
    global clock

    node_id = line["id"]
    previous_datetime = current_datetime
    current_datetime = line["date_time"]
    node_positions[node_id] = line
    
    #updating the simulation clock
    if previous_datetime != UNINITIALIZED:
        time_increment = (current_datetime - previous_datetime).total_seconds()
        clock = clock + time_increment        
        assert time_increment >= 0

    verify_distance(line)
    close_still_open_connections()

def verify_distance(line):
    global node_positions
    global range
    global clock

    for key in node_positions.keys():
        if key != line["id"]:
            item = node_positions[key]
            #get the distance between the two point in meters
            distance = vincenty(item["position"],line["position"]).meters

            assert distance >= 0

            if distance <= range:
                #the nodes are in contact
                #print "the distance (%d,%d) is %d, a connection will be open" % (item["id"],line["id"],distance)
                open_connection(item["id"],line["id"],clock)
            else:
                #check if there are opens connections to close them
                close_connection(item["id"],line["id"],clock)

def close_connection(from_node,to_node,clock):
    global open_connections
    global args
    min_value = min (from_node,to_node)
    max_value = max (from_node,to_node)
    conn_index = "%d:%d" % (min_value,max_value)
    
    if conn_index in open_connections:
        #there is a connection to close
        line = "%d CONN %d %d DOWN\n" % (clock, min_value, max_value)

        with open(args.output,'a') as output_file:
            output_file.write(line)

        #remove the connn from the dict
        del open_connections[conn_index]
        
    

def open_connection(from_node,to_node,clock):
    global open_connections
    global args
    min_value = min (from_node,to_node)
    max_value = max (from_node,to_node)
    conn_index = "%d:%d" % (min_value,max_value)
    
    #if the connections isn't already open
    if conn_index not in open_connections:
        open_connections[conn_index] = {"from":min_value, "to":max_value, "clock":clock}
        
        line = "%d CONN %d %d UP\n" % (clock, min_value, max_value)

        with open(args.output,'a') as output_file:
            output_file.write(line)

def close_still_open_connections():
    global clock
    for conn_index in open_connections.keys():
        conn = open_connections[conn_index]
        close_connection(conn["from"],conn["to"],clock)
    
def main():
    global args
    args = conf_argparser()
    
    input_file = args.datatrace[0]
    #output_file = args.output

    global range
    range = args.range
    
    with open(input_file,'r') as input:
         for line in input:
             consumes_line(line)

if __name__ == "__main__":
    main()
