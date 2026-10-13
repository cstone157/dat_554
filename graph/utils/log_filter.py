import logging

_LOG_FORMAT = "\"%(asctime)s\", \"[%(agent_id)s]\", \"%(levelname)s\", \"%(message)s\""


class AgentFormatter(logging.Formatter):
    """A formatter that injects agent_id into every log record.

    If the record already has an agent_id (set by LogFilter or otherwise),
    it is used as-is.  Otherwise it defaults to "None" so the format string
    never raises KeyError.
    """

    def __init__(self, fmt=None, datefmt=None, style="%", agent_id="None"):
        super().__init__(fmt, datefmt, style)
        self.agent_id = agent_id

    def format(self, record):
        if not hasattr(record, "agent_id"):
            record.agent_id = self.agent_id
        # Escape double quotes in the message to preserve log format integrity
        msg_text = (record.msg % record.args) if record.args else str(record.msg)
        if '"' in msg_text:
            record.msg = msg_text.replace('"', '\\"')
            record.args = ()
        return super().format(record)


def _make_formatter(agent_id="None"):
    """Create a new AgentFormatter with the given agent_id."""
    return AgentFormatter(fmt=_LOG_FORMAT, agent_id=agent_id)


def setup_global_logging():
    """Configure the root logger with an AgentFormatter and StreamHandler.

    All child loggers (from other modules) will inherit this formatter
    automatically, so every module gets agent_id in its output.
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Remove any handlers that basicConfig may have added previously
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(_make_formatter("None"))
    root.addHandler(stream_handler)


def set_global_agent_id(agent_id):
    """Update the default agent_id used by all handlers on the root logger."""
    root = logging.getLogger()
    for handler in root.handlers:
        fmt = handler.formatter
        if isinstance(fmt, AgentFormatter):
            fmt.agent_id = agent_id


def add_file_handler(filepath):
    """Add a FileHandler with the AgentFormatter to the root logger."""
    root = logging.getLogger()
    file_handler = logging.FileHandler(filepath)
    file_handler.setFormatter(_make_formatter("None"))
    root.addHandler(file_handler)