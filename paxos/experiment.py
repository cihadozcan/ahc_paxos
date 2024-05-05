from adhoccomputing.Experimentation.Topology import Topology
from adhoccomputing.GenericModel import GenericModel
from adhoccomputing.Generics import *

from paxos.client_node import ClientNode
from paxos.heartbeat_node import HeartbeatNode
from paxos.paxos_node import PaxosNode
from paxos.sleep_trigger_node import SleepTriggerNode
from paxos.utils import EXPERIMENT_EXECUTION_IN_SECS, NUMBER_OF_PAXOS_NODES, TIMEOUT_IN_MS


class Node(GenericModel):
    """
    This class is the main class of the experiment. It creates Paxos or Raft nodes and connects them as peers. It also creates
    a client, a heartbeat node and a sleep trigger node at the bottom of the topology in order to send client requests,
    simulate timeouts, and manage experiment by implementing sleep trigger mechanism.
    """

    def get_name(self):
        return self.name

    def on_init(self, eventobj: Event):
        pass

    def __init__(self, componentname, componentinstancenumber, context=None, configurationparameters=None,
                 num_worker_threads=1, topology=None):
        super().__init__(componentname, componentinstancenumber, context, configurationparameters, num_worker_threads,
                         topology)
        self.name = componentname + str(componentinstancenumber)
        self.number_of_nodes = NUMBER_OF_PAXOS_NODES

        # Create Paxos Nodes and connect them as peers
        for i in range(self.number_of_nodes):
            self.components.append(PaxosNode("PaxosNode", i + 1, self.number_of_nodes, TIMEOUT_IN_MS / 1000.0))
        for i in range(self.number_of_nodes):
            for j in range(self.number_of_nodes):
                if i != j:
                    self.components[i].connect_me_to_component(ConnectorTypes.PEER, self.components[j])

        # Create a client at bottom
        self.client = ClientNode("ClientNode", 0)
        self.components.append(self.client)
        for i in range(self.number_of_nodes):
            self.client.connect_me_to_component(ConnectorTypes.UP, self.components[i])
            self.components[i].connect_me_to_component(ConnectorTypes.DOWN, self.client)

        # Create a heartbeat node at bottom
        self.heartbeat = HeartbeatNode("HeartbeatNode", 0)
        self.components.append(self.heartbeat)
        for i in range(self.number_of_nodes):
            self.heartbeat.connect_me_to_component(ConnectorTypes.UP, self.components[i])
            self.components[i].connect_me_to_component(ConnectorTypes.DOWN, self.heartbeat)

        # Create a sleep trigger node at bottom
        self.sleep_trigger = SleepTriggerNode("SleepTriggerNode", 0, self.number_of_nodes)
        self.components.append(self.sleep_trigger)
        for i in range(self.number_of_nodes):
            self.sleep_trigger.connect_me_to_component(ConnectorTypes.UP, self.components[i])
            self.components[i].connect_me_to_component(ConnectorTypes.DOWN, self.sleep_trigger)

        # self.client.connect_me_to_component(ConnectorTypes.DOWN, self)
        # self.connect_me_to_component(ConnectorTypes.UP, self.client)


def main():
    setAHCLogLevel(CRITICAL)
    topo = Topology()
    topo.construct_single_node(Node, 0)
    topo.start()
    logger.applog("Topology started")
    time.sleep(EXPERIMENT_EXECUTION_IN_SECS)
    logger.applog("Topology stopped")
    topo.exit()


if __name__ == "__main__":
    main()
