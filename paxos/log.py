from paxos.utils import Command, CommandTypes


class LogEntry:
    def __init__(self, term, command: Command, creator_id, index=None):
        self.term = term
        self.command = command
        self.creator_id = creator_id
        self.index = index

    def __eq__(self, other):
        return self.term == other.term and self.command == other.command and self.creator_id == other.creator_id

    def __str__(self):
        return f"LogEntry(term={self.term}, command={self.command}, creator_id={self.creator_id}, index={self.index})"


class PaxosLog:
    def __init__(self):
        self.entries = []
        self.entries.append(LogEntry(0, Command(0, CommandTypes.NOOP, 0), None))

    def append_entry(self, log_entry: LogEntry):
        self.entries.append(log_entry)

    # Remove all log entries coming after given index
    def truncate(self, index):
        self.entries = self.entries[:index]

    def append_entries(self, entries):
        self.entries.extend(entries)
