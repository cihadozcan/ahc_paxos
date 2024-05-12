.. include:: substitutions.rst
========
Abstract
========

Ensuring agreement on the system state is essential for fault tolerance in distributed systems.
This study presents an implementation and review of two of the most important algorithms used to reach this agreement, Raft and Paxos.
These algorithms are designed to manage crash failures, where a process halts unexpectedly.
However, they do not account for Byzantine failures, where a process might display unpredictable behavior.

Detailed explanations of the algorithms, a comparison of their features, and a discussion of their performance are included in the report.

The implementation of the Raft and Paxos algorithms was done in Python, and the performance of the algorithms was evaluated using a series of experiments
trying to simulate different scenarios and configurations similar to those found in real-world systems.

Consequently, both algorithms found to show strict consistency requiring a similar number of messages to achieve consensus.
In terms of performance, they align with theoretical expectations, with notable differences in the time taken to select a new leader and message sizes during leader election
after a failure. The performance discussion emphasizes that Paxos typically selects a new leader with near-constant time,
while Raft's selection time is influenced by the arrangement of node timeouts.
Raft's leader election tends to be faster and close to Paxos when timeouts are sufficiently spaced,
although it may suffer from vote splitting otherwise.
Additionally, Raft's leader election involves shorter message lengths compared to Paxos due to its restriction on electing only up-to-date nodes as leaders.
Overall, both algorithms offer efficient solutions for different systems, with the choice depending on specific system requirements.