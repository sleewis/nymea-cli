# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#                                                                         #
#  Copyright (C) 2015 guh                                                 #
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

import sys
import telnetlib
import socket
import json
import curses
import os

import devices
import events
import actions
import rules

commandId=0

def init_connection():
    global tn
    HOST='localhost'
    PORT=1234
    if len(sys.argv) > 1:
	HOST = sys.argv[1]
    try:
	tn = telnetlib.Telnet(HOST, PORT)
	packet = tn.read_until("\n}\n")
	packet = json.loads(packet)
	print "connected to", packet["server"], "\nserver version:", packet["version"], "\nprotocol version:", packet["protocol version"], "\n"
	return True
    except socket.error, e:
	print "ERROR:", e[1]," -> could not connect to guh."
	print "       Please check if guh is running on", HOST
	return False
    
def send_command(method, params = None):
    global commandId
    global tn
    commandObj = {}
    commandObj['id'] = commandId
    commandObj['method'] = method
    if not params == None and len(params) > 0:
        commandObj['params'] = params
    command = json.dumps(commandObj) + '\n'
    commandId = commandId + 1
    tn.write(command)
    response = json.loads(tn.read_until("\n}\n"))
    if response['status'] != "success":
        print "JSON error happened: \n%s" % print_json_format(response)
        return None
    return response


def get_selection(title, options):
    global screen
    global normalColor
    global highlightColor
    global menuData
    
    # create menu data from options
    menuData = {}
    menuData['type'] = "menu" 
    menuData['title'] = title
    menuOptions = []
    for i in range(0,len(options)):
	menuItem = {}
	menuItem['title'] = options[i]
	menuItem['type'] = "option" 
	menuItem['id'] = i
	menuOptions.append(menuItem)
    menuData['options'] = menuOptions
    
    # create screen and get selection    
    screen = curses.initscr()
    try:
	curses.noecho()
	curses.cbreak() 
	curses.start_color() 
	screen.clear()
	screen.keypad(1)
	curses.init_pair(1,curses.COLOR_BLACK, curses.COLOR_GREEN)
	selection = process_selection_menu(menuData)
	curses.endwin()
	if selection != None:
	    return int(selection)
	return None
    finally:
	curses.endwin()

def process_selection_menu(menu):
    global screen
    global menuData
    optioncount = len(menu['options'])

    i = runmenu(menu)
    if i != optioncount:
	curses.endwin()
	screen = curses.initscr()
	screen.clear()
	curses.reset_prog_mode()
	curses.curs_set(1)
	curses.curs_set(0)
	return menuData['options'][i]['id']
    else:
	return None
    
    
def runmenu(menu):
    global screen
    global normalColor
    global highlightColor

    highlightColor = curses.color_pair(1) 
    normalColor = curses.A_NORMAL 
    optioncount = len(menu['options']) 
    pos=0 
    oldpos=None 
    x = None 
    
    # Loop until return key is pressed
    while x !=ord('\n'):
	if pos != oldpos:
	    oldpos = pos
	screen.border(0)
	screen.addstr(2,2, menu['title'], curses.A_STANDOUT) 
	# Display all the menu items, showing the 'pos' item highlighted
	for index in range(optioncount):
	    textstyle = normalColor
	    if pos==index:
		textstyle = highlightColor
		screen.addstr(5+index,4, "%d - %s" % (index+1, menu['options'][index]['title']), textstyle)
	textstyle = normalColor
	if pos==optioncount:
	    textstyle = highlightColor
	    screen.addstr(5+optioncount,4, "%d - %s" % (optioncount+1, "Cancel"), textstyle)
	screen.refresh()
	# get user input
	x = screen.getch()
	#if x == curses.KEY_UP:
	#    moveUpDown(up)
	#elif x == curses.KEY_DOWN:
	#    moveUpDown(down)
	#screen.refresh() 
	if x == curses.KEY_DOWN:
	    if pos < optioncount:
		pos += 1
	    else: pos = 0
	elif x == curses.KEY_UP: 
	    if pos > 0:
		pos += -1
	    else: pos = optioncount
	elif x == curses.KEY_BACKSPACE:
	    pos = optioncount
	elif x == 27:
	    pos = optioncount    
	screen.refresh()
    # return index of the selected item
    return pos

def moveUpDown(self, direction):
    nextLineNum = self.highlightLineNum + direction
    # paging
    if direction == self.up and self.highlightLineNum == 0 and self.topLineNum != 0:
	self.topLineNum += self.up
	return
    elif direction == self.down and nextLineNum == self.screenHeight and (self.topLineNum + self.screenHeight) != len(self.allLines):
	self.topLineNum += self.down
	return
    # scroll highlight line
    if direction == self.up and (self.topLineNum != 0 or self.highlightLineNum != 0):
	self.highlightLineNum = nextLineNum
    elif direction == self.down and (self.topLineNum + self.highlightLineNum + 1) != len(self.allLines) and self.highlightLineNum != self.screenHeight:
	self.highlightLineNum = nextLineNum


def get_valueOperator_string(valueOperator):
    if valueOperator == "ValueOperatorEquals":
        return "="
    elif valueOperator == "ValueOperatorNotEquals":
        return "!="
    elif valueOperator == "ValueOperatorLess":
        return "<" 
    elif valueOperator == "ValueOperatorGreater":
        return ">" 
    elif valueOperator == "ValueOperatorLessOrEqual":
        return "<=" 
    elif valueOperator == "ValueOperatorGreaterOrEqual":
        return ">=" 
    else:
        return "<unknown value operator>"
    
    
def get_stateEvaluator_string(stateEvaluator):
    if stateEvaluator == "StateOperatorAnd":
        return "&"
    elif stateEvaluator == "StateOperatorOr":
        return "|"
    else:
        return "<unknown state evaluator>"


def print_device_error_code(deviceError):
    if deviceError == "DeviceErrorNoError":
        print "\nSuccess! (", deviceError, ")"
    elif deviceError == "DeviceErrorPluginNotFound":
        print "\nERROR: the plugin could not be found. (", deviceError, ")"
    elif deviceError == "DeviceErrorDeviceNotFound":
        print "\nERROR: the device could not be found. (", deviceError, ")"
    elif deviceError == "DeviceErrorDeviceClassNotFound":
        print "\nERROR: the deviceClass could not be found. (", deviceError, ")"
    elif deviceError == "DeviceErrorActionTypeNotFound":
        print "\nERROR: the actionType could not be found. (", deviceError, ")"
    elif deviceError == "DeviceErrorStateTypeNotFound":
        print "\nERROR: the stateType could not be found. (", deviceError, ")"
    elif deviceError == "DeviceErrorEventTypeNotFound":
        print "\nERROR: the eventType could not be found. (", deviceError, ")"
    elif deviceError == "DeviceErrorDeviceDescriptorNotFound":
        print "\nERROR: the deviceDescriptor could not be found. (", deviceError, ")"
    elif deviceError == "DeviceErrorMissingParameter":
        print "\nERROR: some parameters are missing. (", deviceError, ")"
    elif deviceError == "DeviceErrorInvalidParameter":
        print "\nERROR: invalid parameter. (", deviceError, ")"
    elif deviceError == "DeviceErrorSetupFailed":
        print "\nERROR: setup failed. (", deviceError, ")"
    elif deviceError == "DeviceErrorDuplicateUuid":
        print "\nERROR: uuid allready exists. (", deviceError, ")"
    elif deviceError == "DeviceErrorCreationMethodNotSupported":
        print "\nERROR: the selected CreationMethod is not supported for this device. (", deviceError, ")"
    elif deviceError == "DeviceErrorSetupMethodNotSupported":
        print "\nERROR: the selected SetupMethod is not supported for this device. (", deviceError, ")"
    elif deviceError == "DeviceErrorHardwareNotAvailable":
        print "\nERROR: the hardware is not available. (", deviceError, ")"
    elif deviceError == "DeviceErrorHardwareFailure":
        print "\nERROR: hardware failure. Something went wrong with the hardware. (", deviceError, ")"
    elif deviceError == "DeviceErrorAsync":
        print "\nINFO: the response will need some time. (", deviceError, ")"
    elif deviceError == "DeviceErrorDeviceInUse":
        print "\nERROR: the device is currently in use. Try again later. (", deviceError, ")"
    elif deviceError == "DeviceErrorPairingTransactionIdNotFound":
        print "\nERROR: the pairingTransactionId could not be found. (", deviceError, ")"
    else:
        print "\nERROR: Unknown error code: ", deviceError,  "Please take a look at the newest API version."


def print_rule_error_code(ruleError):
    if ruleError == "RuleErrorNoError":
        print "\nSuccess! (", ruleError, ")"
    elif ruleError == "RuleErrorInvalidRuleId":
        print "\nERROR: the ruleId is not valid. (", ruleError, ")"
    elif ruleError == "RuleErrorRuleNotFound":
        print "\nERROR: the rule could not be found. (", ruleError, ")"
    elif ruleError == "RuleErrorDeviceNotFound":
        print "\nERROR: the device could not be found for this rule. (", ruleError, ")"
    elif ruleError == "RuleErrorEventTypeNotFound":
        print "\nERROR: the eventType could not be found for this rule. (", ruleError, ")"
    elif ruleError == "RuleErrorActionTypeNotFound":
        print "\nERROR: the actionType could not be found for this rule. (", ruleError, ")"
    elif ruleError == "RuleErrorInvalidParameter":
        print "\nERROR: invalid parameter in this rule. (", ruleError, ")"
    elif ruleError == "RuleErrorMissingParameter":
        print "\nERROR: missing parameter in this rule. (", ruleError, ")"
    else:
        print "\nERROR: Unknown error code: ", ruleError,  "Please take a look at the newest API version."


def print_server_version():
    response = send_command("JSONRPC.Version")
    print "guh version: %5s" % (response['params']['version'])
    print "API version: %5s" % (response['params']['protocol version'])


def print_api():
    print_json_format(send_command("JSONRPC.Introspect"))


def print_json_format(string):
    print json.dumps(string, sort_keys=True, indent=4, separators=(',', ': '))
    print "\n"


def print_api_method():
    methods = send_command("JSONRPC.Introspect")['params']['methods']
    #print_json_format(methods)
    methodList = []
    for item in methods:
	methodList.append(item)
    selection = get_selection("Please select a method:", methodList)
    if selection == None:
	return None
    method = {}
    method[methodList[selection]] = methods[methodList[selection]]
    print print_json_format(method)


def print_api_notifications():
    notifications = send_command("JSONRPC.Introspect")['params']['notifications']
    notificationList = []
    for item in notifications:
	notificationList.append(item)
    selection = get_selection("Please select a notification:", notificationList)
    if selection == None:
	return None
    notification = {}
    notification[notificationList[selection]] = notifications[notificationList[selection]]
    print print_json_format(notification)


def print_api_type():
    types = send_command("JSONRPC.Introspect")['params']['types']
    typesList = []
    for item in types:
	typesList.append(item)
    selection = get_selection("Please select a notification:", typesList)
    if selection == None:
	return None
    type = {}
    type[typesList[selection]] = types[typesList[selection]]
    print print_json_format(type)


def select_valueOperator(value):
    valueOperators = ["ValueOperatorEquals", "ValueOperatorNotEquals", "ValueOperatorLess", "ValueOperatorGreater", "ValueOperatorLessOrEqual", "ValueOperatorGreaterOrEqual"]
    valueOperatorsSymbols = []
    for i in valueOperators:
	valueOperatorsSymbols.append(get_valueOperator_string(i))
    selection = get_selection("Please select an operator to compare this value: \n %s" % value, valueOperatorsSymbols)
    if selection != None:
        return valueOperators[selection]
    return None


def select_stateOperator():
    stateOperators = ["StateOperatorAnd", "StateOperatorOr"]
    stateOperatorsSymbols = []
    for i in stateOperators:
	stateOperatorsSymbols.append(get_stateEvaluator_string(i))
    selection = get_selection("Please select a state operator to compare this states: ", stateOperatorsSymbols)
    if selection != None:
        return stateOperators[selection]
    return None