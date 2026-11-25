"""dial - a one-machine simulation of the v1 sync engine.

Two local folders stand in for Device A and Device B.  Nothing goes over a
network; every message is handed straight to the other device and its bytes
are counted as if they had been sent.
"""

__all__ = ["keys", "chunker", "store", "thumb", "manifest", "wire",
           "router", "checker", "jlog", "device"]
