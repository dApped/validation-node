import time


# ------------------------------------------------------------------------------
# event data -------------------------------------------------------------------


def get_events():
    """
        Info:
            Function that returns all event data for all events
    """
    # TODO read all events node is signed up for
    return []


def get_event_id(contract_address):
    return contract_address

def get_event_data(event_id):
    """
        Info:
            Function that returns event all data for one event
    """
    # return in memory event data
    return {}

def get_event_users(event_address):
    """
        Info:
            Function that returns all users that joined (confirmed) the event (their addresses)
    """
    #TODO read from blockchain with web3
    return []



def get_event_user_ids(event_id):
    """
        Info:
            Function that returns all users that joined (confirmed) the event (their addresses)
    """
    users = get_event_user_ids(event_id)
    return list(map(lambda u: u.id, users))

def save_event_stats(stats, event_id):
    pass

def get_event_fields(event_id):
    """
        Info:
            Function that returns all event fields
    """
    #TODO read from blockchain
    # what is difference from get_event_data

# ------------------------------------------------------------------------------
# event stats ------------------------------------------------------------------

def get_event_consensus_answer(event_id):

    return [True]

# ------------------------------------------------------------------------------
# event joining ----------------------------------------------------------------


def join_event(user_address, event_address):
    """
        Info:
            Function to add a user to the event
    """
    # TODO web3 join event
    pass




def verify_join(user_address, event_address):
    """
        Info:
            Function to verify a user to the event
    """
    #TODO read from blockhcain if user has joined
    pass



# ------------------------------------------------------------------------------
# event voting -----------------------------------------------------------------


def vote_event(user_id, event_id, before_consensus, answers, ip_address):
    '''
        Info:
            Function to cast a vote on an event
    '''

    #event = get_event_address()
    #user = get_user_address()
    current_timestamp = int(round(time.time() * 1000))


    for answer in answers:
        field_id = answer["field_id"]
        field_value = answer["field_value"]

    # TODO vote with web3
    pass

# ------------------------------------------------------------------------------
# event votes ------------------------------------------------------------------


def get_event_votes(event_id):
    """
        Info:
            Function that returns all votes on an event
    """
    # TODO read rewards from blockchain



def get_event_votes_count(event_id):

    # TODO return in memory event votes cound
    return 0


def get_events_votes(event_ids):
    """
        Info:
            Function that returns all votes on events (event_ids)
    """
    # TODO return in memory event votes
    return []


# ------------------------------------------------------------------------------
# event end --------------------------------------------------------------------


def end_event(event_id, consensus_reached, consensus_time):
    """
        Info:
            Function that sets the end_flag to 1 on an event
    """
    #TODO read from blockchain
    pass


# ------------------------------------------------------------------------------
# event rewards ----------------------------------------------------------------


def set_rewards(event_id, users, rewards):
    """
        Info:
            Function to set rewards for users that were part of the consensus
    """
    # TODO write rewards to blockchain if master node
    pass
