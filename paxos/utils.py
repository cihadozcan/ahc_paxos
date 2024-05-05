from enum import Enum

from adhoccomputing.Generics import GenericMessageHeader

TIMEOUT_IN_MS = 200

EXPERIMENT_EXECUTION_IN_SECS = 30
NUMBER_OF_PAXOS_NODES = 5

HEARTBEAT_IN_MS = 30
CLIENT_REQUEST_INTERVAL_IN_MS = 200

SLEEP_LEADER = False
SLEEP_TRIGGER_INTERVAL = 2
SLEEP_TIME = 1
NUMBER_OF_NODES_TO_SLEEP = 1


class NodeStatus(Enum):
    FOLLOWER = "FOLLOWER"  # Learner
    ACCEPTOR = "ACCEPTOR"
    CANDIDATE = "CANDIDATE"
    PROPOSER = "PROPOSER"
    CLIENT = "CLIENT"
    HEARTBEAT = "HEARTBEAT"
    SLEEP_TRIGGER = "SLEEP_TRIGGER"


class PaxosEventTypes(Enum):
    # Paxos Specific
    PREPARE = "PREPARE"
    PROMISE = "PROMISE"
    PROPOSE = "PROPOSE"
    ACCEPT = "ACCEPT"

    # Client
    CLIENT_REQUEST = "CLIENT_REQUEST"  # Come from bottom layer
    CLIENT_RESPONSE = "CLIENT_RESPONSE"  # Goes to bottom layer from leader

    # Organizational
    HEARTBEAT = "HEARTBEAT"  # Come from bottom layer
    SLEEP_TRIGGER = "SLEEP_TRIGGER"  # Come from bottom layer


class PaxosMessageTypes(Enum):
    PREPARE = "PREPARE"
    PROMISE = "PROMISE"
    PROPOSE = "PROPOSE"
    ACCEPT = "ACCEPT"
    CLIENT_REQUEST = "CLIENT_REQUEST"
    CLIENT_RESPONSE = "CLIENT_RESPONSE"


class PaxosMessageHeader(GenericMessageHeader):

    def __init__(self, messageType, messageFrom, messageTo, nextHop=float('inf'), interfaceID=float('inf'),
                 sequenceID=-1):
        super().__init__(messageType, messageFrom, messageTo, nextHop, interfaceID, sequenceID)


class CommandTypes(Enum):
    NOOP = "NOOP"
    ADD = "ADD"
    SUBTRACT = "SUBTRACT"
    MULTIPLY = "MULTIPLY"
    DIVIDE = "DIVIDE"


class Command:

    def __init__(self, command_id, command_type: CommandTypes, command_value):
        self.id = command_id
        self.type = command_type.value
        self.value = command_value

    def __eq__(self, other):
        return (self.id == other.id and
                self.type == other.type and
                self.value == other.value)

    def __str__(self):
        return f"Command(id={self.id}, type={self.type}, value={self.value})"
