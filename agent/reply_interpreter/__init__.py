"""
Act III — Reply Interpreter module.

Pure reasoning layer: interprets prospect replies and decides what the system
should do next, independent of webhooks and transport.
"""
from .reply_interpreter import interpret_reply

__all__ = ["interpret_reply"]
