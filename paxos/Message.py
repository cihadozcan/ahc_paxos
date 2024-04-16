from adhoccomputing.Generics import *


class PaxosMessageTypes(Enum):
    P1aMessage = "P1aMessage"
    P1bMessage = "P1bMessage"
    P2aMessage = "P2aMessage"
    P2bMessage = "P2bMessage"
    DecisionMessage = "DecisionMessage"


class Message:
    def __init__(self, message_type, process_id, message_id, message_value):
        self.message_type = message_type
        self.process_id = process_id
        self.message_id = message_id
        self.message_value = message_value

    def is_p1a_message(self):
        return self.message_type == PaxosMessageTypes.P1aMessage

    def is_p1b_message(self):
        return self.message_type == PaxosMessageTypes.P1bMessage

    def is_p2a_message(self):
        return self.message_type == PaxosMessageTypes.P2aMessage

    def is_p2b_message(self):
        return self.message_type == PaxosMessageTypes.P2bMessage

    def is_decision_message(self):
        return self.message_type == PaxosMessageTypes.DecisionMessage
