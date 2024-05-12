.. include:: substitutions.rst

Distributed Consensus Algorithms: Paxos and Raft
=========================================


Background and Related Work
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since both algorithms serve the same purpose with similar approaches, the main commonalities will be discussed together in the background section.

As explained in introduction, distributed systems should be fault tolerant and consistent. A common technique for that is replicating the server state to several physical machines. This is called state machine replication [Schneider1990]_. Constructing a replicated state machine involves representing the service with a deterministic state machine and creating multiple copies placed on independent nodes. State machines are typically log-based. During operations, replicas receive client commands, execute them on agreed order, and update their state as a result. Commands should alter the state deterministically, to have consistency across replicas. The most crucial task in a replicated state machine (RSM) is agreeing on the order of commands to prevent divergence among replicas. Safely achieving this necessitates employing a consensus protocol, like Raft or Paxos.

A log-based replicated state machine implementation, which is applied in both Paxos and Raft, is depicted in figure [SkrzypzcakAndSchintke2020]_ given below:

.. figure:: figures/ReplicatedStateMachine.png
  :width: 600
  :alt: Log-Based Replicated State Machine

Commands sent by clients are appended at next available slot (index) of the log after being accepted by consensus module.
Consensus protocols, including Paxos and Raft, usually depend on majority to agree on a value [Vukolic2012]_.
Then, the command is executed by the state machine and the result is returned to the client.

After it was introduced by Leslie Lamport [Lamport1998]_, Paxos has been very dominant in the field of distributed systems.
However, it is also famous for its complexity and difficulty to implement. There are many variations of Paxos, created to clarify ambiguities or to make it more effective.
Event Lamport himself has published another paper for simplified definition of Paxos [Lamport2001]_.
Raft [OngaroAndOusterhout2014]_ was created as a response to the complexities inherent in Paxos.
Its goal is to be more comprehensible and simpler to implement compared to Paxos.
It possesses the same fault-tolerance capabilities as Paxos but allegedly achieves them through a simpler and more prescriptive approach.

In the following sections, the algorithms will be detailed respectively, while at the same time highlighting their important differences.
Then, the correctness proofs of the algorithms will be presented together under one heading.

Distributed Algorithm: |paxos|
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Paxos is considered a family of algorithms rather than a single, precisely defined algorithm.
Generality of its definition results in varying approaches across different papers and implementations, sometimes to a significant extent.
To solve this issue, I employed a simpler form of Paxos outlined in a recent article [Howard2020]_ that compared Paxos and Raft.
This version better reflects how Paxos is currently applied, while still remaining in line with its original principles.

System agents can play multiple roles in Paxos; proposers, acceptors, and learners.
Agents change roles dynamically based on the phase of the algorithm and their current state.
It operates in three phases: preparation, submission and learning.
While learning is not a phase in itself, it is a part of the algorithm that ensures all agents are aware of the decisions made earlier.

Each node in Paxos consensus has a unique identifier. I simply used sequential numbers as id's, beginning from 1.
It is important because message sources are differentiated by these numbers.

Similarly, each node stores a current term number, which increases monotonically over time.
This term number is used to differentiate between different rounds of the algorithm.
When a proposer starts a new round, it increments its term number and sends it to acceptors.
Acceptors compare this term number with their own and accept proposer if it has a higher term.
Different proposers choose their numbers from disjoint sets of numbers, so two different proposers never issue a proposal with the same number.
This way, the algorithm decides which proposer is active. Terms are also used in log entries, to ensure that entries from different terms are not mixed up.
For each index in the log, the term number of its proposer is stored along with the command.
Utilizing terms, the algorithm keeps logs in the order they were committed. This will be clearer when phases are further explained below.

Normally, a single server is chosen as the leader and takes the responsibility of being proposer.
It obtains commands from clients, and decides the order of commands in the log by issuing proposals and getting them accepted.
Even if no commands are received from clients, the leader periodically sends empty proposals called heartbeats to maintain its leadership.
Other nodes know that the leader is still alive if they receive heartbeats.
If the leader fails or gets so slow that it can't send heartbeats, learners/acceptors can start a new leader election by sending a prepare message with a higher term number to its peers.
They detect leader unavailability by keeping track of the last time they received a heartbeat from the leader and comparing it with a timeout value.

In the prepare message, a proposer picks next possible number as a proposed term and asks other nodes whether they’re ready to accept a proposal with this term.
When an acceptor gets this request, it checks whether the term in the request is higher than any it’s seen before, including their own term. If it is, the
acceptor promises not to accept any lower numbers and tells the proposer the highest number it has accepted so far, by sending promise message.

Below, :ref:`algorithm <PreparationLabel>` for the preparation phase is given.

.. _PreparationLabel:

.. code-block:: RST
    :linenos:
    :caption: Pseudocode for Preparation Phase.

    OnTimeout: () do
    Set current term to next term.
    Create prepare message with current term and commit index.
    Send prepare message.
    Reset timeout.

    OnPrepare: (prepare_message) do
        If term in prepare message is less than last promised term:
            Reject and return promised term.
        If term in prepare message is greater than last promised term:
            Accept and send promise message with term, by adding existing log entries greater than proposer's commit index.
            If commit index in prepare message is greater than current commit index:
                Update commit index.

    OnPromise: (promise_message) do
        If received promises from majority before timeout:
            Merge log entries from promises with log entries of itself.
            Proceed to submission phase.
        Else:
            Retry prepare phase with higher term.


We need to explain two more things in :ref:`prepare phase algorithm <PreparationLabel>` above.

First, the select_next_term() function is used to select the next term number for the proposer,
such that it is higher than any term number it has seen before and it is chosen from a disjoint set of numbers.
It is important to use a disjoint set of numbers for each node to prevent two proposers from choosing the same term number.
Disjoint sets can be created by incrementing the term number by the number of nodes in the system, after initializing the term number to node number.
For example, next term number t will be calculated as t = t + N, where N is the number of nodes in the system.
It can be formulated as t mod N = i, where i is the node number or 0 for the last node since node numbers start from 1.

Secondly, it is important to understand the usage of commitIndex variable in the promise message. It is used to keep track of the highest index that has been committed by the proposer.
When an acceptor receives a prepare message, it checks the commitIndex in the message and creates a list of entries from its log that have an index greater than proposer commitIndex.
This list is sent back to the proposer in the promise message, so that the proposer can update its log with the missing entries.
These entries obtained from all positive promises are merged with proposer's log entry, such that conflicting indexes are resolved by taking the entry with the higher term number.
Also, proposer uses its new term while adding these new entries coming from promises. This way, the proposer's log is ensured to be up-to-date with the latest entries from the majority of acceptors.
Examples for how this log merging is shown for some situation in the :ref:`figure <MergeFigureLabel>` below:

.. _MergeFigureLabel:

.. figure:: figures/LogMergeExample.png
  :width: 600
  :alt: Log Merge Example

If most acceptors agree, the proposer moves to the next step, submission phase. It asks all acceptors to accept the proposal.
Once most accept, the proposer applies command and tells everyone including client, and the decision is final.
If an acceptor has promised for a proposal number, it accepts propose unless it has already responded to a prepare request with a higher number meanwhile.

Below, :ref:`algorithm <SubmissionLabel>` for the submission phase is given.

.. _SubmissionLabel:

.. code-block:: RST
    :linenos:
    :caption: Pseudocode for Submission Phase.

    OnPropose: (event) do

        If message is not intended for this node:
            Ignore.

        If it's a heartbeat message:
            Handle the heartbeat by resetting timer and updating commit index.
        Else:
            Reset timer.
            Handle the proposed entries, accept them if their term is not less than current or promised term.
            Respond with the result.

    OnAccept: (event) do

        If message is not intended for this node or it's not in proposer state:
            Ignore.

        If accepted:
            Update match index and next index, which are used to keep track of the log replication status of this acceptor.
            Commit entries if majority of acceptors have accepted them.
            If there are more entries to send:
                Send them directly.
        Else if term is greater than current term:
            Update term and transition to follower.
        Else:
            Decrement next index and retry proposing with lower index.


:ref:`General workflow <PaxosWorkflowLabel>` as a summary for Paxos algorithm [Xiong2022]_ is provided below.
This figure shows the general workflow of Paxos algorithm, including the preparation and submission phases for a typical round.
After that, a new round may start with a new term number if proposer needs to change, otherwise same term number is used.

.. _PaxosWorkflowLabel:

.. image:: figures/PaxosWorkflow.png
  :width: 500
  :alt: Paxos Workflow


Distributed Algorithm: Raft
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Raft divides the consensus problem into more manageable sub-problems, which are relatively independent.
It is designed to be easier to understand and implement than Paxos.
Moreover, it fills in the gaps in Paxos, that were left to the implementer to figure out.
But in the end, both algorithms are equivalent in terms of their capabilities.
Since we have already explained the log-based replicated state machine solution, and details of Paxos algorithm deeply,
we will focus on the differences between Paxos and Raft in this section.

Raft makes sure that only one chosen leader talks to clients at a time. Nodes can be in one of three roles: leader, follower, or candidate.
The leader handles the log and copies it to followers. Followers mostly just listen to the leader's instructions. Candidates are nodes trying to become the leader.
Actually, we can call Raft's Leader as Proposer in Paxos naming, and follower as Acceptor or Learner according to the phase of the algorithm.
Only Candidate state seems to be new but even it is not a new concept, it is just like naming an Acceptor/Learner as Candidate while trying to be a Proposer in Paxos.
Therefore, same transitions hold for Paxos as well, only with different names. :ref:`These state transitions <PaxosWorkflowLabel>` are given in figure [Brun2021]_ below:

.. _RaftLeaderElectionLabel:

.. image:: figures/RaftLeaderElection.png
  :width: 400
  :alt: Raft State Transitions for Leader Election

In Raft, it's made sure that the leader always knows the latest log updates.
If a follower has newer log entries than the candidate/leader, it won't vote for candidate and accept the leader's log updates.
In this case, the proposer steps down, and another candidate with better logs becomes the new leader.
This is a significant difference from Paxos, where the proposer can continue to propose even if it doesn't have the latest log entries.
In Paxos, the proposer can still be elected as the leader, but it will not be able to commit its proposals to the log until it gets the latest log entries from the majority of acceptors
using log entries sent along with their promise messages. This is a more complex process compared to Raft, and it requires more messages to be exchanged.
Raft doesn't require this extra step, as it ensures that the leader always has the latest log entries.
Followers decide more up-to-date log by considering the higher term number in the log entries.
If the term number is the same, the log with the higher index is considered more up-to-date and voting process is done accordingly.

After successful election, leader adds client requests to its log and shares it with its followers.
The followers then add a valid entry to their logs and confirm back to the leader.
Once the leader reaches a quorum of followers, it commits the entry to the log, notifies followers and informs the client.
Leader continues to send heartbeats to followers to maintain its leadership, and when it fails to do so, a new leader election is triggered.
This part is again same as Paxos. But detecting leader failure is somehow different in Raft, as followers have different timeout values.
Paxos makes sure that proposers use distinct term numbers to avoid conflicts,
while Raft allows candidates to request vote with same term number.
But here, voting is done for the candidate itself, not like promising for a term number in Paxos.
To prevent split votes, stemming from multiple candidates requesting votes at the same time, Raft uses randomized timeouts for candidates.
So that, early requesters have a higher chance to get elected as the leader. Even if it fails in the first round,
randomness will help converge to a single leader in the next rounds.



Correctness of Paxos and Raft
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Since both Paxos and Raft satisfy the same safety properties, their correctness proofs are similar.
Therefore, they will be presented together in this section.

1.3.4.1 Safety
-----------

According to [Lamport2001]_, the safety requirements for consensus are:

- Only a value that has been proposed may be chosen,
- Only a single value is chosen, and
- A process never learns that a value has been chosen unless it actually has been.

These criteria should be met in scenarios where agents can function at varying speeds, are prone to failure by halting,
and where message delivery may encounter delays, duplication, or loss.
Proofs for how both Paxos and Raft satisfies these safety properties mentioned above:

- They ensure acceptors only vote for values that have been proposed by the leader. So, the first safety property is satisfied trivially.
- If there are 2k+1 acceptors, then at least k+1 acceptors must vote for a value to satisfy the quorum. Since only one quorum can be formed, only one value can be chosen. Thanks to this, leaders can never delete or overwrite entries.
- Learners can receive a value to learn only if it has been voted by a quorum of acceptors. Moreover leaders are elected by majority and only up-to-date leaders can commit a value to the log, the third safety property is also satisfied.

1.3.4.2 Liveness
-----------
If more than one proposer starts off new rounds concurrently, the algorithms may not make progress because of split votes.
By prioritizing higher term numbers and making sure that nodes use disjoint sets of term numbers, Paxos effectively prevent split votes.
Raft uses randomized timeouts to prevent split votes, so that it is expected to converge to a single leader in the next rounds.
But still, it is possible that a split vote occurs in Raft, if multiple candidates with very close timeouts request votes at the same time.
Especially considering that Raft only accepts candidates with fully up-to-date logs,
it decreases number of proper candidates and long unavailability of a leader may cause some liveness issues.
On the other hand, choosing timeouts correctly will almost definitely guarantee that a leader is elected in a short time.

1.3.4.3 Complexity
-----------

In a single round of each algorithm, every node participates in both the Prepare (Phase 1) and Accept (Phase 2) stages (only naming changes for Raft).
Throughout these phases, proposers interact with acceptors by transmitting propose and accept messages, while acceptors reply with promise and accepted messages.
Hence, each of these 2 phases requires 2 messages per node.

Once a quorum of acceptors has been reached and a decision is reached, the proposer disseminates this decision to all nodes within the system,
considering them as potential learners.
Learn phase ensures that all nodes ultimately become aware of the determined value, thereby concluding the consensus process.

As a result, the number of messages exchanged per Paxos/Raft round is roughly 5N, where N denotes the total number of nodes in the system.


.. [Lamport1998] Leslie Lamport, KThe part-time parliament. ACM Trans. Comput. Syst. 1998, 16, 133–169.
.. [Lamport2001] Lamport, Leslie. (2001). Paxos Made Simple. Sigact News - SIGACT. 32.
.. [Xiong2022] Xiong, Huanliang & Chen, Muxi & Wu, Canghai & Zhao, Yingding & Yi, Wenlong. (2022). Research on Progress of Blockchain Consensus Algorithm: A Review on Recent Progress of Blockchain Consensus Algorithms. Future Internet. 14. 47.
.. [OngaroAndOusterhout2014] Diego Ongaro and John Ousterhout. 2014. In search of an understandable consensus algorithm. In Proceedings of the 2014 USENIX conference on USENIX Annual Technical Conference (USENIX ATC'14). USENIX Association, USA, 305–320.
.. [Brun2021] Le Brun, M.A., Attard, D.P., & Francalanza, A. (2021). Graft: general purpose raft consensus in Elixir. Proceedings of the 20th ACM SIGPLAN International Workshop on Erlang.
.. [Schneider1990] Schneider, Fred B. (1990). Implementing fault-tolerant services using the state machine approach: A tutorial. ACM Computing Surveys, 22(4), 299-319.
.. [SkrzypzcakAndSchintke2020] Skrzypzcak, J., Schintke, F. Towards Log-Less, Fine-Granular State Machine Replication. Datenbank Spektrum 20, 231–241 (2020).
.. [Vukolic2012] Vukolic M (2012) Quorum systems: with applications to storage and consensus. Morgan & Claypool, San Rafael.
.. [Howard2020] Heidi Howard and Richard Mortier. 2020. Paxos vs Raft: have we reached consensus on distributed consensus? In Proceedings of the 7th Workshop on Principles and Practice of Consistency for Distributed Data (PaPoC '20). Association for Computing Machinery, New York, NY, USA, Article 8, 1–9.
