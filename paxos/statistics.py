from adhoccomputing.Generics import logger


class Statistics:

    number_of_leader_changes = 0
    total_time_during_elections = 0

    @classmethod
    def increment_leader_changes(cls):
        cls.number_of_leader_changes += 1

    @classmethod
    def add_time_during_election(cls, time):
        cls.total_time_during_elections += time
        logger.error(f"Average time during elections: {cls.total_time_during_elections / cls.number_of_leader_changes}")