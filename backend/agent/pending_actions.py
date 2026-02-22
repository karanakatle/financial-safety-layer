pending_actions = {}

def set_pending_action(user_id, action_type, data):
    pending_actions[user_id] = {
        "type": action_type,
        "data": data
    }
    #print("SETTING ACTION:", user_id, action_type, data)

def get_pending_action(user_id):
    return pending_actions.get(user_id)

def clear_pending_action(user_id):
    if user_id in pending_actions:
        del pending_actions[user_id]