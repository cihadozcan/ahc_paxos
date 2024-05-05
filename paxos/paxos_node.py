import random

from adhoccomputing.Generics import *
from adhoccomputing.GenericModel import GenericModel, GenericMessage

from paxos.utils import NodeStatus, PaxosEventTypes, PaxosMessageHeader, PaxosMessageTypes, CommandTypes, Command
from paxos.log import PaxosLog, LogEntry


class PaxosNode(GenericModel):
    """
    The PaxosNode class represents a node in the Paxos consensus algorithm. It inherits from the GenericModel
    class and includes methods for handling required events in the Paxos algorithm. Paxos Nodes are connected to
    each other as peers and can send messages to each other. They can also receive messages from clients and
    send responses back to them. They can be in one of three states: FOLLOWER, CANDIDATE, or PROPOSER.
    """

    def __init__(self, componentname, componentinstancenumber, numberofnodes, timeout, context=None,
                 configurationparameters=None,
                 num_worker_threads=1, topology=None):
        """
        Initializes a PaxosNode object with the given parameters.
        :param numberofnodes: The number of Paxos nodes in the system.
        :param timeout: The timeout value for the Paxos node, in milliseconds.
        """
        super().__init__(componentname, componentinstancenumber, context, configurationparameters,
                         num_worker_threads, topology)
        self.state_machine_value = 0
        self.state = NodeStatus.FOLLOWER
        self.current_term = componentinstancenumber  # latest term node has seen (initialized to instance number and increases as factors)
        self.promised_term = 0  # term for which vote was promised
        self.node_id = componentname + '_' + str(componentinstancenumber)
        self.log = PaxosLog()
        self.commit_index = 0
        self.last_applied = 0
        self.number_of_nodes = numberofnodes

        # Last timer reset time, is used by followers and candidates to detect timeout
        self.last_timer_reset_time = time.time()
        self.timeout = timeout

        # Following two are for leader and reinitialized after election
        self.next_index = {}  # for each node, index of the next log entry to send to that server (initialized to leader last log index + 1)
        self.match_index = {}  # for each node, index of highest log entry known to be replicated on server (initialized to 0, increases monotonically)

        # Reinitialized after transitioning to candidate
        self.promises_received = set()
        self.promoted_entries = []

        self.eventhandlers[PaxosEventTypes.PROPOSE] = self.on_propose
        self.eventhandlers[PaxosEventTypes.ACCEPT] = self.on_accept
        self.eventhandlers[PaxosEventTypes.PREPARE] = self.on_prepare
        self.eventhandlers[PaxosEventTypes.PROMISE] = self.on_promise
        self.eventhandlers[PaxosEventTypes.CLIENT_REQUEST] = self.on_client_request
        self.eventhandlers[PaxosEventTypes.HEARTBEAT] = self.on_heartbeat
        self.eventhandlers[PaxosEventTypes.SLEEP_TRIGGER] = self.on_sleep_trigger

    def on_init(self, eventobj: Event):
        """
        Initializes the Paxos node object.
        """
        if self.componentinstancenumber == self.number_of_nodes:
            self.transition_to_proposer()

    # PHASE 1 (PREPARE - PROMISE) EVENTS
    def create_prepare_payload(self):
        """
        Creates a payload for the prepare message.
        :return: The payload for the prepare message as a dictionary,
        containing current term, node ID, and commit index of sender.
        """
        return {
            'term': self.current_term,
            'proposerId': self.node_id,
            'proposerCommitIndex': self.commit_index
        }

    def on_prepare(self, eventobj: Event):
        """
        Handles the prepare message received by the node. It checks the term of the message and responds with a promise
        if the term is greater than the biggest term receiver has seen. If response is positive, it also sends the entries
        that are not yet committed by the proposer. So that, proposer can update its log before being a leader. Success
        response means that the node is ready to accept the proposer as a leader, if no other prepare message with higher
        term is received before proposer reaches majority.
        :param eventobj: The event object containing the prepare message.
        :return: Response payload including voteGranted boolean result, current term, and entries to be promoted.
        """
        given_term = eventobj.eventcontent.payload['term']

        vote_granted = False
        if given_term > self.current_term and given_term > self.promised_term:
            self.transition_to_acceptor(given_term)
            vote_granted = True

        prepare_response_payload = {
            'voteGranted': vote_granted,
            'term': self.current_term,
            'entries': self.log.entries[eventobj.eventcontent.payload['proposerCommitIndex'] + 1:]
        }

        request_vote_response_header = PaxosMessageHeader(PaxosMessageTypes.PROMISE, self.node_id,
                                                          eventobj.eventcontent.header.messagefrom)
        response_message = GenericMessage(request_vote_response_header, prepare_response_payload)
        self.send_peer(Event(self, PaxosEventTypes.PROMISE, response_message))

    def on_promise(self, eventobj: Event):
        """
        Handles the promise message received by the node. If the response is positive, the node adds the respondent to
        the set of nodes that have promised to vote for it. If the number of promises received reaches majority, the
        node transitions to proposer (leader) state. For each promise, voter also sends the entries that are not yet
        committed by the proposer. These entries are merged with the already promoted entries obtained from other nodes.
        :param eventobj: The event object containing the promise message.
        """
        if eventobj.eventcontent.header.messageto != self.node_id or NodeStatus.CANDIDATE != self.state:
            return
        logger.info(f"{self.node_id} received promise from {eventobj.eventcontent.header.messagefrom}")
        respondent_id = eventobj.eventcontent.header.messagefrom
        if eventobj.eventcontent.payload['voteGranted']:
            self.promises_received.add(respondent_id)
            self.merge_promoted_entries(eventobj.eventcontent.payload['entries'])
            if len(self.promises_received) > self.number_of_nodes / 2:
                self.transition_to_proposer()

    # For each new entry, compares with already obtained entities to be promoted.
    # Promoted entries are updated with current, proposed term.
    # Gaps are filled with no-op entries.
    def merge_promoted_entries(self, newEntries):
        """
        Helper method to merge the new entries with the already promoted entries. For each new entry, compares with
        already obtained entities to be promoted, and those with higher term overwrite the lower term if a conflict
        occurs in the same index. Gaps are filled with no-op entries when there is a gap between the indexes of the
        merged promoted entries list. These promoted entries are updated with the current, proposed term before being
        sent by the proposer.
        """
        merged_entries = self.promoted_entries + newEntries
        merged_entries.sort(key=lambda promoted_entry: promoted_entry.index)

        merged_list = []  # Handled index conflicts
        prev_index = None
        for entry in merged_entries:
            if entry.index == prev_index:
                # Higher term overwrites lower term in same index
                valid_command = entry.command if merged_list[-1].term < entry.term else merged_list[-1].command
                merged_list[-1] = LogEntry(max(merged_list[-1].term, entry.term), valid_command, self.node_id, entry.index)
            else:
                merged_list.append(entry)
                prev_index = entry.index

        final_list = []  # Filled with no-op entries
        prev_index = None
        for entry in merged_list:
            if prev_index is not None and entry.index - prev_index > 1:
                filler_index = prev_index + 1
                while filler_index < entry.index:
                    logger.error(f"filler_index: {filler_index}")
                    no_op_command = Command(0, CommandTypes.NOOP, 0)
                    filler_entry = LogEntry(0, no_op_command, self.node_id, filler_index)
                    final_list.append(filler_entry)
                    filler_index += 1
            final_list.append(entry)
            prev_index = entry.index

        return final_list

    def send_prepare_to_peers(self):
        """
        Sends the prepare message to all peers of the node.
        """
        self.reset_timer()
        self.current_term += self.number_of_nodes
        logger.error(f"{self.node_id} is sending prepare for term {self.current_term}")
        self.promised_term = self.current_term
        self.promises_received = {self.node_id}
        self.promoted_entries = self.log.entries[self.commit_index + 1:]
        message = self.create_prepare_payload()
        header = PaxosMessageHeader(PaxosMessageTypes.PREPARE, self.node_id, None)
        self.send_peer(Event(self, PaxosEventTypes.PREPARE, GenericMessage(header, message)))

    # PHASE 2 (PROPOSE-ACCEPT) EVENTS
    def send_propose_to_peers(self):
        """
        Sends the propose message to all peers of the node.
        """
        for peer_id in self.get_peer_ids():
            self.send_propose_to_peer(peer_id)

    def send_propose_to_peer(self, peer_id):
        """
        Helper method to send the propose message to a specific peer.
        """
        message = self.create_propose_payload(peer_id)
        header = PaxosMessageHeader(PaxosMessageTypes.PROPOSE, self.node_id, peer_id)
        self.send_peer(Event(self, PaxosEventTypes.PROPOSE, GenericMessage(header, message)))

    def create_propose_payload(self, peer_id):
        """
        Helper method to create the payload for the propose message.
        :param peer_id: The ID of the peer to send the propose message to.
        :return: The payload for the propose message as a dictionary, containing current term, previous log index
         as well as the term of the previous log entry expected to match with receiver's copy of the log,
         new entries to be sent, and the commit index of the leader.
        """
        next_index_to_send = self.next_index[peer_id]
        for entry in self.log.entries[next_index_to_send:]:
            entry.term = self.current_term
        return {
            'term': self.current_term,
            'prevLogIndex': next_index_to_send - 1,
            'prevLogTerm': self.log.entries[next_index_to_send - 1].term,
            'entries': self.log.entries[next_index_to_send:],
            'leaderCommit': self.commit_index
        }

    def on_propose(self, eventobj: Event):
        """
        Handles the propose message received by the node. If the message is a heartbeat, it simply resets timer and
        updates according to the leader's commit index. If the message contains entries, it checks the term of the
        message and responds with a boolean result. If the term is greater than the current term and previous log
        of new entries in proposer matches with the receiver's log, the node accepts the new entries and updates
        itself. Otherwise, it responds with a negative result, expecting the leader to update itself by trying to
        send older entries or updating its term.
        """
        if eventobj.eventcontent.header.messageto != self.node_id:
            return
        # Handle periodic heartbeats
        if eventobj.eventcontent.payload['entries'] is None:
            self.handle_heartbeat_from_leader(eventobj.eventcontent.payload)
        else:
            self.reset_timer()
            append_entries_response_payload = {
                'success': self.handle_propose(eventobj.eventcontent.payload),  # boolean result
                'term': self.current_term,  # for leader to update itself
                'index': eventobj.eventcontent.payload['prevLogIndex'] + len(eventobj.eventcontent.payload['entries'])
            }
            append_entries_response_header = PaxosMessageHeader(PaxosMessageTypes.ACCEPT, self.node_id,
                                                                eventobj.eventcontent.header.messagefrom)
            response_message = GenericMessage(append_entries_response_header, append_entries_response_payload)
            self.send_peer(Event(self, PaxosEventTypes.ACCEPT, response_message))

    def send_heartbeat_to_peers(self):
        """
        Periodic heartbeat messages are sent to all peers by the leader to keep them updated with the latest commit
        index and to prevent them from starting an election.
        """
        message = {
            'term': self.current_term,
            'prevLogIndex': None,
            'prevLogTerm': None,
            'entries': None,
            'leaderCommit': self.commit_index
        }
        for peer_id in self.get_peer_ids():
            header = PaxosMessageHeader(PaxosMessageTypes.PROPOSE, self.node_id, peer_id)
            self.send_peer(Event(self, PaxosEventTypes.PROPOSE, GenericMessage(header, message)))

    def handle_heartbeat_from_leader(self, payload):
        """
        Handles the heartbeat message obtained from the leader.
        """
        given_term = payload['term']
        if given_term > self.current_term:
            self.transition_to_follower()
            self.apply_new_entries_as_follower(payload['leaderCommit'])

    def handle_propose(self, payload):
        """
        Handles the propose message obtained as a helper to on_propose method.
        """
        given_term = payload['term']
        if given_term < self.current_term:
            return False
        else:
            self.transition_to_follower()

        given_entries = payload['entries']
        prev_log_index = payload['prevLogIndex']
        prev_log_term = payload['prevLogTerm']
        leader_commit = payload['leaderCommit']

        # Reply false if log does not contain an entry at prevLogIndex whose term matches prevLogTerm
        if len(self.log.entries) < prev_log_index + 1 or self.log.entries[prev_log_index].term != prev_log_term:
            return False
        # If an existing entry at given index conflicts with a new one, delete the one from older term
        start_index = prev_log_index
        offset = 1
        if start_index + offset < len(self.log.entries) and self.log.entries[start_index + offset] is not None and offset < len(given_entries):
            given_entry = given_entries[offset]
            conflicting_entry_term = self.log.entries[given_entry.index].term
            if conflicting_entry_term != given_entry.term:
                self.log.truncate(prev_log_index + 1)
            offset += 1
            if offset == len(given_entries):
                return True
        # Append new entries
        self.log.append_entries(given_entries[offset:])
        # If leaderCommit > commitIndex, apply new entries to state machine and update commitIndex
        self.apply_new_entries_as_follower(leader_commit)
        return True

    def apply_new_entries_as_follower(self, leader_commit):
        """
        When a follower receives new entries from the leader, it applies the new entries to its state machine and
        updates the commit index.
        """
        if leader_commit > self.commit_index:
            last_applicable_entry = min(leader_commit, len(self.log.entries) - 1)
            applicable_entries = range(self.commit_index + 1, last_applicable_entry + 1)
            self.commit_index = last_applicable_entry
            for index in applicable_entries:
                if index > self.last_applied:
                    self.apply_command(self.log.entries[index].command)
                    self.last_applied = index

    def on_accept(self, eventobj: Event):
        """
        Leader handles the accept message received from peers. If the response is positive, it updates the match index
        to use for future proposals. If the response is negative, it decrements the next index to try to send the
        older entries until it reaches a common point with the follower.
        """
        if eventobj.eventcontent.header.messageto != self.node_id or NodeStatus.PROPOSER != self.state:
            return
        logger.critical(f"Accepted from {eventobj.eventcontent.header.messagefrom} as success: {eventobj.eventcontent.payload['success']}")
        logger.info(f"{self.node_id} received accept from {eventobj.eventcontent.header.messagefrom} as success: {eventobj.eventcontent.payload['success']}")
        respondent_id = eventobj.eventcontent.header.messagefrom
        respondent_term = eventobj.eventcontent.payload['term']
        entry_index = eventobj.eventcontent.payload['index']
        if eventobj.eventcontent.payload['success']:
            # Ignore if response is for an outdated entry
            if entry_index == self.match_index[respondent_id]:
                return
            self.match_index[respondent_id] = self.next_index[respondent_id] + len(self.promoted_entries) - 1
            self.next_index[respondent_id] += len(self.promoted_entries)
            self.commit_entries()
        elif respondent_term > self.current_term:
            self.current_term = respondent_term
            self.transition_to_follower()
        else:
            self.next_index[respondent_id] -= 1

    def commit_entries(self):
        """
        Commits the entries that are replicated by majority of the nodes. After that, it applies the new commits to the
        state machine as leader and send response to the client if needed.
        """
        # Finds uncommitted commands with current term that are replicated by majority
        last_log_committed = self.commit_index
        for index in range(self.commit_index + 1, len(self.log.entries)):
            if self.log.entries[index].term == self.current_term:
                if sum(1 for peer_id in self.get_peer_ids() if
                       self.match_index[peer_id] >= index) + 1 > self.number_of_nodes / 2:
                    self.commit_index = index
        # Applies new commits to state machine as leader and updates last applied index
        if self.commit_index > last_log_committed:
            for index in range(last_log_committed + 1, self.commit_index + 1):
                self.apply_command(self.log.entries[index].command)
                self.last_applied = index
                if self.last_applied == len(self.log.entries) - 1:
                    self.send_heartbeat_to_peers()
                    self.send_client_response()
            self.promoted_entries = []

    # CLIENT RELATED EVENTS
    def on_client_request(self, eventobj: Event):
        """
        Handles the client request received by the node. If the node is a proposer, it appends the new entry to the log
        and sends the propose message to peers. Nodes other than proposer just ignores the request.
        """
        if NodeStatus.PROPOSER != self.state:
            return
        logger.info(f"{self.node_id} received client request for command id {eventobj.eventcontent.id}")
        new_entry = LogEntry(self.current_term, eventobj.eventcontent, self.node_id, self.commit_index + len(self.promoted_entries) + 1)
        self.promoted_entries.append(new_entry)
        self.log.append_entry(new_entry)
        self.send_propose_to_peers()

    def send_client_response(self):
        response_payload = {
            'success': True,
            'command': self.log.entries[self.last_applied].command
        }
        response_header = PaxosMessageHeader(PaxosMessageTypes.CLIENT_RESPONSE, self.node_id, None)
        response_message = GenericMessage(response_header, response_payload)
        self.send_down(Event(self, PaxosEventTypes.CLIENT_RESPONSE, response_message))

    def apply_command(self, command: Command):
        old_state_machine_value = self.state_machine_value
        if command.type == CommandTypes.ADD.value:
            self.state_machine_value += command.value
        elif command.type == CommandTypes.SUBTRACT.value:
            self.state_machine_value -= command.value
        logger.info(
            f"{self.node_id} APPLIED COMMAND id: {command.id}\n"
            f"{old_state_machine_value} {command.type == CommandTypes.ADD.value and '+' or '-'} {command.value} = {self.state_machine_value}")

    # STATE TRANSITIONS
    def transition_to_proposer(self):
        logger.error(f"{self.node_id} is transitioning to proposer")
        self.state = NodeStatus.PROPOSER
        peer_ids = self.get_peer_ids()
        self.next_index = {peer_id: self.commit_index + 1 for peer_id in peer_ids}
        self.match_index = {peer: 0 for peer in peer_ids}
        self.send_heartbeat_to_peers()
        if self.log.entries[self.last_applied].command.id != 0:
            self.send_client_response()

    def transition_to_candidate(self):
        self.state = NodeStatus.CANDIDATE
        self.reset_timer()

    def transition_to_follower(self):
        self.state = NodeStatus.FOLLOWER
        self.promised_term = None
        self.reset_timer()

    def transition_to_acceptor(self, given_term):
        self.promised_term = given_term
        self.state = NodeStatus.ACCEPTOR
        self.reset_timer()

    # All ids created with numbers in range self.number_of_nodes + 1 except node's id
    def get_peer_ids(self):
        return [f'PaxosNode_{i}' for i in range(1, self.number_of_nodes + 1) if f'PaxosNode_{i}' != self.node_id]

    def on_heartbeat(self, eventobj):
        if self.state == NodeStatus.PROPOSER:
            self.send_heartbeat_to_peers()
        elif self.state == NodeStatus.FOLLOWER and self.is_timeout() and self.promised_term is None:
            self.transition_to_candidate()
        elif self.state == NodeStatus.CANDIDATE and self.is_timeout() > self.timeout:
            self.send_prepare_to_peers()

    def reset_timer(self):
        self.last_timer_reset_time = time.time()

    def on_sleep_trigger(self, eventobj: Event):
        """
        Handles the sleep trigger event received by the node. A special node periodically sends the sleep trigger
        event to some random nodes to simulate the crash or slow response.
        """
        time_to_sleep = eventobj.eventcontent['time_to_sleep']
        sleep_leader = eventobj.eventcontent['sleep_leader']
        target_nodes = eventobj.eventcontent['target_node_ids']
        if self.node_id in target_nodes:
            if self.state == NodeStatus.PROPOSER and not sleep_leader:
                non_leader_peer = self.choose_random_non_leader_peer(target_nodes)
                payload = {'target_node_ids': non_leader_peer, 'sleep_leader': sleep_leader,
                           'time_to_sleep': time_to_sleep}
                trigger_sleep_event = Event(self, PaxosEventTypes.SLEEP_TRIGGER, payload)
                self.send_peer(trigger_sleep_event)
            else:
                logger.error(f"{self.node_id} is sleeping for {time_to_sleep} seconds")
                time.sleep(time_to_sleep)
                self.transition_to_follower()

    def choose_random_non_leader_peer(self, exempt_list):
        """
        As a type of configuration, the leader node can be exempted from the sleep trigger event. In this case, the
        leader randomly selects a non-leader peer to send the sleep trigger event to.
        """
        peer_ids = self.get_peer_ids()
        exempt_list.remove(self.node_id)
        for peer_id in exempt_list:
            peer_ids.remove(peer_id)
        return [random.choice(peer_ids)]

    def is_timeout(self):
        return time.time() - self.last_timer_reset_time > self.timeout
