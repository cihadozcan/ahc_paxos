import time

from adhoccomputing.GenericModel import GenericModel
from adhoccomputing.Generics import Event

from paxos.utils import NodeStatus, PaxosEventTypes, HEARTBEAT_IN_MS


class HeartbeatNode(GenericModel):
    """
    Heartbeat node sends heartbeat events to the cluster. It sends heartbeat events to upper layer so that
    Paxos or Raft nodes can check time passed since the last time they heard from the leader or can follow
    timeout durations before transitioning to another state.
    """

    def __init__(self, componentname, componentinstancenumber, context=None, configurationparameters=None,
                 num_worker_threads=1, topology=None):
        super().__init__(componentname, componentinstancenumber, context, configurationparameters,
                         num_worker_threads, topology)
        self.expected_state_machine_value = 0
        self.state = NodeStatus.HEARTBEAT
        self.node_id = componentname + '_' + str(componentinstancenumber)

    def on_init(self, eventobj: Event):
        heartbeat_event = Event(self, PaxosEventTypes.HEARTBEAT, None)
        while True:
            self.send_up(heartbeat_event)
            time.sleep(HEARTBEAT_IN_MS / 1000.0)
