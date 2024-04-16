from adhoccomputing.Generics import *
from adhoccomputing.Experimentation.Topology import Topology
from adhoccomputing.GenericModel import GenericModel, GenericMessageHeader, GenericMessagePayload, GenericMessage

from paxos.Message import Message, PaxosMessageTypes


class ProcessStatus(Enum):
    PROPOSER = "PROPOSER"
    ACCEPTOR = "ACCEPTOR"
    LEARNER = "LEARNER"


class Process:
    def __init__(self, process_id, quorum_size=1):
        self.quorum_size = quorum_size
        self.process_id = process_id
        self.process_status = ProcessStatus.LEARNER
        self.promised_id = None
        self.promised_value = None
        self.accepted_id = None
        self.accepted_value = None
        self.proposed_id = None
        self.proposed_value = None
        self.received_promises = set()
        self.received_acceptances = set()

    def transition_to_acceptor(self):
        self.process_status = ProcessStatus.ACCEPTOR
        self.promised_id = None
        self.promised_value = None

    def transition_to_proposer(self):
        self.process_status = ProcessStatus.PROPOSER
        self.promised_id = None
        self.promised_value = None
        self.proposed_id = None
        self.proposed_value = None
        self.received_promises = set()
        self.received_acceptances = set()


def transition_to_learner(self):
    self.process_status = ProcessStatus.LEARNER

    def receive_message(self, message):
        if message.is_decision_message():
            self.transition_to_learner()
            return self.receive_decision(message)
        elif self.process_status == ProcessStatus.ACCEPTOR or self.process_status == ProcessStatus.PROPOSER:
            if message.is_p1a_message():
                return self.receive_p1a(message)
            elif message.is_p2a_message():
                return self.receive_p2a(message)
        elif self.process_status == ProcessStatus.PROPOSER:
            if message.is_p1b_message():
                return self.receive_p1b(message)
            elif message.is_p2b_message():
                return self.receive_p2b(message)
        else:
            raise ValueError("Invalid process status")

    def receive_p1a(self, message):
        if message.is_p1a_message():
            if self.promised_id is None or message.message_id > self.promised_id:
                self.promised_id = message.message_id
                self.promised_value = message.message_value
                return Message(PaxosMessageTypes.P1bMessage, self.process_id, self.promised_id, self.promised_value)

    def receive_p2a(self, message):
        if message.is_p2a_message():
            if message.message_id >= self.promised_id:
                self.accepted_id = message.message_id
                self.accepted_value = message.message_value
                return Message(PaxosMessageTypes.P2bMessage, self.process_id, self.accepted_id, self.accepted_value)

    def receive_p1b(self, message):
        if message.is_p1b_message():
            if message.message_id == self.proposed_id:
                self.received_promises.add(message)

    def receive_p2b(self, message):
        if message.is_p2b_message():
            if message.message_id == self.proposed_id:
                self.received_acceptances.add(message)
                if len(self.received_acceptances) >= self.quorum_size:
                    return Message(PaxosMessageTypes.DecisionMessage, self.process_id, self.proposed_id,
                                   self.proposed_value)

    def prepare(self, proposal_value):
        self.proposed_id = self.accepted_id + 1
        self.proposed_value = proposal_value
        return Message(PaxosMessageTypes.P1aMessage, self.process_id, self.proposed_id, self.proposed_value)

    def propose(self):
        return Message(PaxosMessageTypes.P2aMessage, self.process_id, self.proposed_id, self.proposed_value)

    def receive_decision(self, message):
        if message.is_decision_message():
            if message.message_id > self.accepted_id:
                self.accepted_id = message.message_id
                self.accepted_value = message.message_value
