.. include:: substitutions.rst

Conclusion
==========


In conclusion, the comparison between the two algorithms reveals their consistent behavior and efficiency in achieving consensus with a similar message overhead.
While both algorithms perform in accordance with theoretical expectations, there are notable distinctions in their leader
selection processes and message sizes during leader election following a failure event.
Paxos demonstrates a steady leader selection time, whereas Raft's timing is influenced by node timeout arrangements.
When timeouts are adequately spaced, Raft's leader election tends to be faster and close to Paxos, though.
Moreover, Raft's approach to leader election results in shorter message lengths compared to Paxos.
Ultimately, both algorithms offer effective solutions tailored to diverse system requirements.
Both algorithms were found similar in terms of understandability, too, with Raft being slightly easier to understand due to its well-defined processes.

For the future work directions, followings are suggested:
- Investigate the performance of the algorithms under conditions, like multiple clients independently proposing values.
- For the sake of simplicity, topology accepted to be static in this study. However, it would be interesting to investigate the performance of the algorithms under dynamic topologies.
- There can be improvements in the algorithms to