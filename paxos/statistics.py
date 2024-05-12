import time

from adhoccomputing.Generics import logger


class Statistics:
    number_of_leader_changes = 0
    total_time_during_elections = 0
    time_of_election = None
    first_election = True

    @classmethod
    def increment_leader_changes(cls):
        cls.number_of_leader_changes += 1

    @classmethod
    def add_time_during_election(cls):
        if cls.time_of_election is not None:
            if cls.first_election:
                cls.number_of_leader_changes = 0
                cls.total_time_during_elections = 0
                cls.time_of_election = None
                cls.first_election = False
                return  # Skip the first election
            cls.total_time_during_elections += (time.time() - cls.time_of_election)
            logger.info(
                f"Average time during elections: {cls.total_time_during_elections / cls.number_of_leader_changes}")
        cls.time_of_election = None

    @classmethod
    def start_time_for_election(cls):
        if cls.time_of_election is None:
            logger.info("Election started")
            cls.time_of_election = time.time()
