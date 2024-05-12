.. include:: substitutions.rst

Introduction
============

When we design distributed systems, one of the main goals is to prevent the entire system from breaking down when some partial failures occur. We call this quality fault tolerance. Consensus algorithms are used to ensure groups of nodes in a system keep system state consistent, even if some nodes fail. This is crucial for creating distributed systems that work correctly as a whole. So, by coordinating the nodes in the system to reach consensus, we can make it seem like there's only one smooth process that serves clients correctly.

To clarify how consensus algorithms which are the main focus of this review, can tackle this issue, we first need to explain some terms.

When a system can't do its job correctly, we call it a failure. Errors, such as mistakes or issues in the system, lead to these failures. Faults cause these errors. There are different ways to handle faults, such as: preventing them in the beginning or removing them when encountered. The handling method we will focus on in this review is fault tolerance, which is based on the idea of masking the faults and maintaining service as if nothing happened. The main way to have fault tolerance in a distributed system is by grouping some equivalent nodes together. If some node stops working, hopefully, others can step in to do its job [GuerraouiAndSchiper1997]_. A system is called k-fault tolerant if it can keep meeting its requirements even if k nodes fail.

The ways in which failures occur also vary, and so do the approaches to tolerating them. A crash failure happens when a server suddenly stops working, even though it was working as expected until it halts. In contrast, Byzantine failures, also known as arbitrary failures, occur when servers give faulty responses at any time. These failures may also be considered to involve malicious acts like a node sending wrong information deliberately.

The term fault tolerance should be considered alongside the term dependability, which can be informally defined as "ensuring that the system remains dependable for the end user". According to [KopetzAndVerissimo1993]_, dependability covers these requirements for distributed systems:

- Available: System should be available to the user at a given instant in time.
- Reliable: System can run continuously without failure, for a given period of time.
- Safe: System should not cause any harm to the user because of failures.
- Maintainable: System can be repaired from a failed state to a working state.

For the consensus algorithms Raft and Paxos, we suppose the system is not Byzantine, but we don't expect it to be synchronized. Messages might take a long time to reach or get lost, and servers might work at different speeds. However, we do assume that message exchange is reliable and in-order, like when we use TCP/IP.

For such a system with 2k+1 nodes, Raft or Paxos can be used to maintain consensus in a k-fault tolerant way. This ongoing fault tolerance makes system dependable by ensuring requirements explained above, unless more than k crash failures happen at the same time.

Our main contributions consist of the following points:

- Implementing both Raft and Paxos algorithms on the AHCv2 platform. Section 1.3 delves into algorithm specifics and compares their features.
- Exploring implementation approaches to simulate systems and presenting the results obtained by assessing the performance of these algorithms across various topologies in section 1.4.
- Section 1.5 outlines the conclusion drawn from our findings and discusses potential future research directions.

.. [KopetzAndVerissimo1993] Kopetz H. and Verissimo P. Real Time and Dependability Concepts. In Mullender S., editor, Distributed Systems, pages 411–446. Addison-Wesley, Wokingham, 2nd edition, 1993.
.. [GuerraouiAndSchiper1997] Guerraoui R. and Schiper A. Software-Based Replication for Fault Tolerance. Computer, 30(4):68–74, Apr. 1997