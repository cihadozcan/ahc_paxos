import random
import time

from adhoccomputing.GenericModel import GenericModel
from adhoccomputing.Generics import Event

from paxos.utils import NodeStatus, PaxosEventTypes, SLEEP_TRIGGER_INTERVAL, SLEEP_LEADER, SLEEP_TIME, \
    NUMBER_OF_NODES_TO_SLEEP


class SleepTriggerNode(GenericModel):
    """
    This class is responsible for sending sleep trigger event to a random set of Raft or Paxos nodes.
    Sleep trigger is used to simulate crashes or other failures in the system.
    """

    def __init__(self, componentname, componentinstancenumber, numberofnodes, context=None,
                 configurationparameters=None,
                 num_worker_threads=1, topology=None):
        super().__init__(componentname, componentinstancenumber, context, configurationparameters,
                         num_worker_threads, topology)
        self.expected_state_machine_value = 0
        self.state = NodeStatus.SLEEP_TRIGGER
        self.node_id = componentname + '_' + str(componentinstancenumber)
        self.number_of_nodes = numberofnodes

    def on_init(self, eventobj: Event):
        while True:
            time.sleep(SLEEP_TRIGGER_INTERVAL)
            payload = {'target_node_ids': self.get_random_node_ids(NUMBER_OF_NODES_TO_SLEEP), 'sleep_leader': SLEEP_LEADER, 'time_to_sleep': SLEEP_TIME}
            trigger_sleep_event = Event(self, PaxosEventTypes.SLEEP_TRIGGER, payload)
            self.send_up(trigger_sleep_event)

    # Select number_of_nodes_to_select among all, randomly
    def get_random_node_ids(self, number_of_nodes_to_select):
        node_ids = []
        for i in range(self.number_of_nodes):
            node_ids.append("PaxosNode_" + str(i + 1))
        # Randomly select number_of_nodes_to_select nodes
        return random.sample(node_ids, number_of_nodes_to_select)
