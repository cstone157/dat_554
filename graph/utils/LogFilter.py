import logging

class LogFilter(logging.Filter):
    def __init__(self, agent_id="None"):
        self.agent_id = agent_id

    def set_agent_id(self, agent_id):
        self.agent_id = agent_id

    """
    A filter that the agent/session id into the record
    """
    def filter(self, record):
        # Dynamically inject fields directly into the record object
        record.agent_id = self.agent_id
        return True