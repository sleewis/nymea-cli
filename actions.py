import guh
import devices

def get_actionType(actionTypeId):
    params = {}
    params['actionTypeId'] = actionTypeId
    response = guh.send_command("Actions.GetActionType", params)
    return response['params']['actionType']


def create_actions():
    enough = False
    actions = []
    while not enough:
        print "\nCreating Action:"
        deviceId = devices.select_configured_device()
        device = devices.get_device(deviceId)
        actionType = select_actionType(device['deviceClassId'])
        params = guh.read_params(actionType['paramTypes'])
        action = {}
        action['deviceId'] = deviceId
        action['actionTypeId'] = actionType['id']
        if len(params) > 0:
            action['params'] = params
            
        actions.append(action)
        input = raw_input("Do you want to add another action? (y/N): ")
        if not input == "y":
            enough = True
            
    return actions


def execute_action():
    deviceId = devices.select_configured_device()
    device = devices.get_device(deviceId)
    actionType = select_actionType(device['deviceClassId'])
    if actionType == "":
        print "\n    This device has no actions"
        return
    
    actionTypeId = actionType['id']
    params = {}
    params['actionTypeId'] = actionTypeId
    params['deviceId'] = deviceId
    actionType = get_actionType(actionTypeId)
    actionParams = guh.read_params(actionType['paramTypes'])
    params['params'] = actionParams
    response = guh.send_command("Actions.ExecuteAction", params)
    guh.print_device_error_code(response['params']['deviceError'])
    
    
def select_actionType(deviceClassId):
    actions = get_action_types(deviceClassId)
    if not actions:
	return None
    
    actionList = []
    print "got actions", actions
    for i in range(len(actions)):
        print "got actiontype", actions[i]
        actionList.append(actions[i]['name'])
        
    selection = guh.get_selection("Please select an action type:", actionList)
    return actions[selection]


def get_action_types(deviceClassId):
    params = {}
    params['deviceClassId'] = deviceClassId
    return guh.send_command("Devices.GetActionTypes", params)['params']['actionTypes']

