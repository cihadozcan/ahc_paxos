import random
import time

from adhoccomputing.GenericModel import GenericModel
from adhoccomputing.Generics import Event, logger

from paxos.utils import NodeStatus, PaxosEventTypes, CommandTypes, Command, CLIENT_REQUEST_INTERVAL_IN_MS


class ClientNode(GenericModel):
    """
    Client node sends requests to the cluster. It generates random commands and sends them to upper layer
    involving Paxos or Raft nodes. It waits for the response and if the response is successful, it sends another request.
    CLIENT_REQUEST_INTERVAL_IN_MS constant is used to define the interval between requests.
    """

    def __init__(self, componentname, componentinstancenumber, context=None, configurationparameters=None,
                 num_worker_threads=1, topology=None):
        super().__init__(componentname, componentinstancenumber, context, configurationparameters,
                         num_worker_threads, topology)
        self.expected_state_machine_value = 0
        self.state = NodeStatus.CLIENT
        self.last_command = None
        self.node_id = componentname + '_' + str(componentinstancenumber)

        self.eventhandlers[PaxosEventTypes.CLIENT_RESPONSE] = self.on_client_response

    def on_init(self, eventobj: Event):
        first_command = Command(1, CommandTypes.ADD, 33)
        self.last_command = first_command
        first_client_request_event = Event(self, PaxosEventTypes.CLIENT_REQUEST, self.last_command)
        self.send_up(first_client_request_event)

    def on_client_response(self, eventobj: Event):
        print(f"Client {self.node_id} received response: {eventobj.eventcontent.payload}")
        print(f"Last command: {self.last_command}")
        if eventobj.eventcontent.payload['success'] and eventobj.eventcontent.payload['command'] == self.last_command:
            self.apply_command(self.last_command)
            time.sleep(CLIENT_REQUEST_INTERVAL_IN_MS / 1000.0)
            self.last_command = self.generate_command()
            client_request_event = Event(self, PaxosEventTypes.CLIENT_REQUEST, self.last_command)
            self.send_up(client_request_event)
        else:
            logger.error(f"Client {self.node_id} received REPEATED response: for command id: {eventobj.eventcontent.payload['command'].id}")
            client_request_event = Event(self, PaxosEventTypes.CLIENT_REQUEST, self.last_command)
            self.send_up(client_request_event)

    # Choose random number to add, between -100 and 100
    def generate_command(self):
        value = random.randint(-100, 100)
        command_type = CommandTypes.ADD if value > 0 else CommandTypes.SUBTRACT
        return Command(self.last_command.id + 1, command_type, abs(value))

    def apply_command(self, command):
        old_state_machine_value = self.expected_state_machine_value
        if command.type == CommandTypes.ADD.value:
            self.expected_state_machine_value += command.value
        elif command.type == CommandTypes.SUBTRACT.value:
            self.expected_state_machine_value -= command.value
        logger.error(
            f"{self.node_id} APPLIED COMMAND id: {command.id}\n"
            f"{old_state_machine_value} {command.type == CommandTypes.ADD.value and '+' or '-'} {command.value} = {self.expected_state_machine_value}")