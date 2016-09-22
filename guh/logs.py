# -*- coding: UTF-8 -*-

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#                                                                         #
#  Copyright (C) 2015 Simon Stuerz <simon.stuerz@guh.guru>                 #
#                                                                         #
#  This file is part of guh-cli.                                          #
#                                                                         #
#  guh-cli is free software: you can redistribute it and/or modify        #
#  it under the terms of the GNU General Public License as published by   #
#  the Free Software Foundation, version 2 of the License.                #
#                                                                         #
#  guh-cli is distributed in the hope that it will be useful,             #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the           #
#  GNU General Public License for more details.                           #
#                                                                         #
#  You should have received a copy of the GNU General Public License      #
#  along with guh. If not, see <http://www.gnu.org/licenses/>.            #
#                                                                         #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

import datetime
import curses
import sys
import socket
import json
import select
import telnetlib
import string
import time

import guh
import states
import devices
import actions
import events
import rules

global stateTypeIdCache
global actionTypeIdCache
global eventTypeIdCache
global deviceIdCache
global ruleIdCache
global logFilter


def log_window(guhHost, guhPort, params = None):
    global screen
    global screenHeight
    global allLines
    global topLineNum
    global highlightLineNum
    global up
    global down
    global commandId

    global stateTypeIdCache
    global actionTypeIdCache
    global eventTypeIdCache
    global deviceIdCache
    global ruleIdCache
    global logFilter

    stateTypeIdCache = {}
    actionTypeIdCache = {}
    eventTypeIdCache = {}
    deviceIdCache = {}
    ruleIdCache = {}
    logFilter = params
    
    commandId = 0
    
    # Create notification handler
    print "Connecting notification handler..."
    try:
        tn = telnetlib.Telnet(guhHost, guhPort)
    except :
        print "ERROR: notification socket could not connect the to guh-server. \n"
        return None
    print "...OK \n"
    
    #enable_notification(notificationSocket)
    enable_notification(tn.get_socket())
    create_log_window()
    
    try:
        x = None
        while (x !=ord('\n') and x != 27):
            socket_list = [sys.stdin, tn.get_socket()]
            read_sockets, write_sockets, error_sockets = select.select(socket_list , [], [])
            for sock in read_sockets:
                # notification messages:
                if sock == tn.get_socket():
                    packet = tn.read_until("\n}\n")
                    packet = json.loads(packet)
                    if 'notification' in packet:
                        if packet['notification'] == "Logging.LogEntryAdded":
                            entry = packet['params']['logEntry']
                            line = get_log_entry_line(entry, True)
                            # scroll to bottom if curser was at the bottom
                            if topLineNum + highlightLineNum == len(allLines) - 1:
                                if line != None:
                                    allLines.append(line)
                                    scroll_to_bottom()
                            else:
                                if line != None:
                                    allLines.append(line)
                                    # flash to tell that there is a new entry
                                    curses.flash()
                    draw_screen()
                else:
                    x = screen.getch() # timeout of 50 ms (screen.timout(50))
                    if x == curses.KEY_UP:
                        moveUpDown(up)
                        draw_screen()
                    elif x == curses.KEY_DOWN:
                        moveUpDown(down)
                        draw_screen()
                    elif x == ord(' '):
                        scroll_to_bottom()
                        draw_screen()
    finally:
        curses.endwin()
        print "Log window closed."
        tn.close()
        print "Notification socket closed."

    
    
def create_log_window():
    global screen
    global screenHeight
    global allLines
    global topLineNum
    global highlightLineNum
    global up
    global down

    
    # init
    up = -1
    down = 1
    screen = curses.initscr()
    curses.start_color() 
    curses.init_pair(1,curses.COLOR_BLACK, curses.COLOR_GREEN) 
    curses.noecho()
    curses.cbreak()
    screen.keypad(1)
    screen.timeout(50)
    screen.clear()
    screenHeight = curses.LINES - 2
    #screen.addstr(1, 2, "Loading...", curses.COLOR_GREEN)
    #draw_screen()
    allLines = get_log_entry_lines()
    scroll_to_bottom()

def scroll_to_bottom():
    global screenHeight
    global allLines
    global topLineNum
    global highlightLineNum
    
    # scroll to bottom
    if len(allLines) <= screenHeight:
        topLineNum = 0
        highlightLineNum = len(allLines) - 1 
    else:
        topLineNum = len(allLines) - screenHeight
        highlightLineNum = screenHeight - 1
    

def enable_notification(notifySocket):
    global commandId
    
    params = {}
    commandObj = {}
    commandObj['id'] = commandId
    commandObj['method'] = "JSONRPC.SetNotificationStatus"
    params['enabled'] = "true"
    commandObj['params'] = params
    command = json.dumps(commandObj) + '\n'
    commandId = commandId + 1
    notifySocket.send(command)


def draw_screen():
    global screen
    global topLineNum
    global screenHeight
    global allLines
    global highlightLineNum
    
    hilightColors = curses.color_pair(1) 
    normalColors = curses.A_NORMAL 
    
    screen.erase()
    screen.border(0)
    curses.curs_set(1)   
    curses.curs_set(0)
    top = topLineNum
    bottom = topLineNum + screenHeight
    for (index,line,) in enumerate(allLines[top:bottom]):
        linenum = topLineNum + index 
        # highlight current line            
        if index != highlightLineNum:
            screen.addstr(index + 1, 2, line, normalColors)
        else:
            screen.addstr(index + 1, 2, line, hilightColors)
    screen.refresh()


def moveUpDown(direction):
    global screenHeight
    global allLines
    global topLineNum
    global highlightLineNum
    global up
    global down
    
    nextLineNum = highlightLineNum + direction

    # paging
    if direction == up and highlightLineNum == 0 and topLineNum != 0:
        topLineNum += up
        return
    elif direction == down and nextLineNum == screenHeight and (topLineNum + screenHeight) != len(allLines):
        topLineNum += down
        return
    # scroll highlight line
    if direction == up and (topLineNum != 0 or highlightLineNum != 0):
        highlightLineNum = nextLineNum
    elif direction == down and (topLineNum + highlightLineNum + 1) != len(allLines) and highlightLineNum != screenHeight:
        highlightLineNum = nextLineNum


def list_logEntries():
    params = {}
    lines = []
    response = guh.send_command("Logging.GetLogEntries", params)
    for i in range(len(response['params']['logEntries'])):
        line = get_log_entry_line(response['params']['logEntries'][i])
        print line


def get_log_entry_lines():
    global logFilter
    lines = []
    response = guh.send_command("Logging.GetLogEntries", logFilter)
    for i in range(len(response['params']['logEntries'])):
        line = get_log_entry_line(response['params']['logEntries'][i])
        lines.append(line)
    return lines


def get_log_entry_line(entry, checkFilter = False):
    global stateTypeIdCache
    global actionTypeIdCache
    global eventTypeIdCache
    global deviceIdCache
    global ruleIdCache
    
    global logFilter

    if checkFilter:
        if not verify_filter(entry):
            return None

    if entry['loggingLevel'] == "LoggingLevelInfo":
        levelString = "(I)"
        error = "-"
    else:
        levelString = "(A)"
        error = entry['errorCode']
    if entry['source'] == "LoggingSourceSystem":
        deviceName = "Guh Server"
        sourceType = "System"
        symbolString = "->"
        sourceName = "Active changed"
        if entry['active'] == True:
            value = "active"
        else:
            value = "inactive"
    if entry['source'] == "LoggingSourceStates":
        typeId = entry['typeId']
        sourceType = "State Changed"
        symbolString = "->"
        if typeId in stateTypeIdCache:
            sourceName = stateTypeIdCache[typeId]
        else:
            stateType = states.get_stateType(typeId)
            if stateType is not None:
                sourceName = stateType["name"]
                stateTypeIdCache[typeId] = sourceName
            else:
                sourceName = typeId
        value = entry['value']
        deviceName = get_device_name(entry)
    if entry['source'] == "LoggingSourceActions":
        typeId = entry['typeId']
        sourceType = "Action executed"
        symbolString = "()"
        if typeId in actionTypeIdCache:
            sourceName = actionTypeIdCache[typeId]
        else:
            actionType = actions.get_actionType(typeId)
            if actionType is not None:
                sourceName = actionType['name']
            else:
                sourceName = typeId
            actionTypeIdCache[typeId] = sourceName
        value = entry['value']
        deviceName = get_device_name(entry)
    if entry['source'] == "LoggingSourceEvents":
        typeId = entry['typeId']
        sourceType = "Event triggered"
        symbolString = "()"
        if typeId in eventTypeIdCache:
            sourceName = eventTypeIdCache[typeId]
        else:
            eventType = events.get_eventType(typeId)
            sourceName = eventType['name']
            eventTypeIdCache[typeId] = sourceName
        value = entry['value']
        deviceName = get_device_name(entry)
    if entry['source'] == "LoggingSourceRules":
        typeId = entry['typeId']
        if entry['eventType'] == "LoggingEventTypeTrigger":
            sourceType = "Rule triggered"
            sourceName = "triggered"
            symbolString = "()"
            value = ""
        elif entry['eventType'] == "LoggingEventTypeActionsExecuted":
            sourceType = "Rule executed"
            sourceName = "actions"
            symbolString = "()"
            value = ""      
        elif entry['eventType'] == "LoggingEventTypeExitActionsExecuted":
            sourceType = "Rule executed"
            sourceName = "exit actions"
            symbolString = "()" 
            value = ""
        elif entry['eventType'] == "LoggingEventTypeEnabledChange":
            sourceType = "Rule changed"
            sourceName = "enabled"
            symbolString = "->" 
            if entry['active']:
                value = "true"
            else:
                value = "false"
                
        else:             
            sourceType = "Rule changed"
            symbolString = "()"
            sourceName = "active"
            if entry['active']:
                value = "active"
            else:
                value = "inactive"
        
        if typeId in ruleIdCache:
            deviceName = ruleIdCache[typeId]
        else:
            rule = rules.get_rule_description(typeId)
            if rule is not None and 'name' in rule:
                deviceName = rule['name']
            else:
                deviceName = typeId
            ruleIdCache[typeId] = deviceName
    timestamp = datetime.datetime.fromtimestamp(entry['timestamp']/1000)
    line = "%s %s | %19s | %38s | %20s %3s %20s | %10s" %(levelString.encode('utf-8'), timestamp, sourceType.encode('utf-8'), deviceName.encode('utf-8'), sourceName.encode('utf-8'), symbolString.encode('utf-8'), value.encode('utf-8'), error.encode('utf-8'))
    return line


def create_device_logfilter():
    params = {}
    deviceIds = []
    deviceId = devices.select_configured_device()
    if not deviceId:
        return None
    deviceIds.append(deviceId)
    params['deviceIds'] = deviceIds
    return params


def create_device_state_logfilter():
    params = {}
    deviceIds = []
    typeIds = []
    loggingSources = []
    loggingSources.append("LoggingSourceStates")
    params['loggingSources'] = loggingSources
    deviceId = devices.select_configured_device()
    if not deviceId:
        return None
    deviceIds.append(deviceId)
    params['deviceIds'] = deviceIds
    device = devices.get_device(deviceId)
    stateType = states.select_stateType(device['deviceClassId'])
    if not stateType:
        return None
    typeIds.append(stateType['id'])
    params['typeIds'] = typeIds
    return params



def create_rule_logfilter():
    params = {}
    sources = []
    ruleIds = []
    rule = rules.select_rule()
    if not rule:
        return None
        
    ruleIds.append(rule['id'])
    sources.append("LoggingSourceRules")
    params['loggingSources'] = sources
    params['typeIds'] = ruleIds
    return params

def create_last_time_logfilter(minutes):
    offsetSeconds = 60 * minutes;
    params = {}
    timeFilters = []
    timeFilter = {}
    timeFilter['startDate'] = int(time.time()) - offsetSeconds
    timeFilters.append(timeFilter)        
    params['timeFilters'] = timeFilters
    return params


def create_logfilter():
    params = {}
    boolTypes = ["yes","no"]
    
    # Devices
    selection = guh.get_selection("Do you want to filter for \"Devices\"? ", boolTypes)
    if boolTypes[selection] == "yes":
        deviceIds = []
        deviceId = devices.select_configured_device()
        deviceIds.append(deviceId)
        
        
        finished = False
        while not finished:
            selection = guh.get_selection("Do you want to add an other \"Device\"? ", boolTypes)
            if boolTypes[selection] == "no":
                finished = True
                break
            deviceId = devices.select_configured_device()
            if not deviceId:
                params['deviceIds'] = deviceIds
                return params
            deviceIds.append(deviceId)
            
      
        params['deviceIds'] = deviceIds
    
    # LoggingSources
    selection = guh.get_selection("Do you want to filter for \"LoggingSource\"? ", boolTypes)
    if boolTypes[selection] == "yes":
        sources = []
        finished = False
        loggingSources = ["LoggingSourceSystem", "LoggingSourceEvents", "LoggingSourceActions", "LoggingSourceStates", "LoggingSourceRules"]
        selection = guh.get_selection("Please select a \"LoggingSource\": ", loggingSources)
        if selection:
            sources.append(loggingSources[selection])
        else:
            finished = True

        while not finished:
            selection = guh.get_selection("Do you want to add an other \"LoggingSource\"? ", boolTypes)
            if boolTypes[selection] == "no":
                finished = True
                break
            
            selection = get_selection("Please select a \"LoggingSource\": ", loggingSources)
            if selection:
                sources.append(loggingSources[selection])
            else:
                finished = True
                break
        params['loggingSources'] = sources
    
    # LoggingLevel
    selection = guh.get_selection("Do you want to filter for \"LoggingLevel\"? ", boolTypes)
    if boolTypes[selection] == "yes":
        levels = []
        loggingLevels = ["LoggingLevelInfo", "LoggingLevelAlert"]
        selection = guh.get_selection("Please select a \"LoggingLevel\": ", loggingLevels)
        if selection:
            levels.append(loggingLevels[selection])

        params['loggingLevels'] = levels
    
    # LoggingEventType
    selection = guh.get_selection("Do you want to filter for \"LoggingEventType\"? ", boolTypes)
    if boolTypes[selection] == "yes":
        types = []
        loggingEventTypes = ["LoggingEventTypeTrigger", "LoggingEventTypeActiveChange", "LoggingEventTypeEnabledChange", "LoggingEventTypeActionsExecuted", "LoggingEventTypeExitActionsExecuted"]
        selection = guh.get_selection("Please select a \"LoggingEventType\": ", loggingEventTypes)
        if selection:
            types.append(loggingEventTypes[selection])

        params['eventTypes'] = types
    
    # Value
    selection = guh.get_selection("Do you want to filter for certain log \"Values\"? ", boolTypes)
    if boolTypes[selection] == "yes":
        values = []
        finished = False
        value = raw_input("Please enter value which should be filtered out: ")
        values.append(value)
        
        while not finished:
            selection = guh.get_selection("Do you want to add an other \"Value\"? ", boolTypes)
            if boolTypes[selection] == "no":
                finished = True
                break
            value = raw_input("Please enter value which should be filtered out: ")
            values.append(value)
        
        params['values'] = values
    
    # Times
    selection = guh.get_selection("Do you want to add a \"TimeFilter\"? ", boolTypes)
    if boolTypes[selection] == "yes":
        timeFilters = []  
        finished = False
        
        timeFilters.append(create_time_filter())
        while not finished:
            selection = guh.get_selection("Do you want to add an other \"TimeFilter\"? ", boolTypes)
            if boolTypes[selection] == "no":
                finished = True
                break

            timeFilters.append(create_time_filter())
            
        params['timeFilters'] = timeFilters
        
    guh.print_json_format(params)
    guh.debug_stop()
    return params
    

def create_time_filter():
    timeFilter = {}
    boolTypes = ["yes","no"]
    selection = guh.get_selection("Do you want to define a \"Start date\"?", boolTypes)
    if boolTypes[selection] == "yes":
        timeFilter['startDate'] = raw_input("Please enter the \"Start date\": ")
    selection = guh.get_selection("Do you want to define a \"End date\"?", boolTypes)
    if boolTypes[selection] == "yes":
        timeFilter['endDate'] = raw_input("Please enter the \"End date\": ")
    return timeFilter
        

def get_device_name(entry):
    global deviceIdCache
    
    deviceName = None
    name = None
    
    if entry['deviceId'] in deviceIdCache:
            deviceName = deviceIdCache[entry['deviceId']]
    else:
        device = devices.get_device(entry['deviceId'])
        deviceName = device['name']
        deviceIdCache[entry['deviceId']] = deviceName
    
    return deviceName


def verify_filter(entry):
    global logFilter
    
    if not logFilter:
        return True
    
    # check if we should filter for deviceIds
    if 'deviceIds' in logFilter:
        found = False
        for deviceId in logFilter['deviceIds']:
            if deviceId == entry['deviceId']:
                found = True
                break
        if not found:
            return False

    # check if we should filter for ruleId
    if 'typeIds' in logFilter:
        found = False
        for ruleId in logFilter['typeIds']:
            if ruleId == entry['typeId']:
                found = True
                break
        if not found:
            return False
    
    # check if we should filter for loggingSource
    if 'loggingSources' in logFilter:
        found = False
        for loggingSource in logFilter['loggingSources']:
            if loggingSource == entry['source']:
                found = True
                break
        if not found:
            return False

    # check if we should filter for values
    if 'values' in logFilter:
        found = False
        for value in logFilter['values']:
            if value == entry['value']:
                found = True
                break
        if not found:
            return False

    # check if we should filter for loggingLevels
    if 'loggingLevels' in logFilter:
        found = False
        for loggingLevel in logFilter['loggingLevels']:
            if loggingLevel == entry['loggingLevel']:
                found = True
                break
        if not found:
            return False
        

    return True
    
