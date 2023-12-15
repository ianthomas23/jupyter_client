from __future__ import annotations


def iant_debug(msg):
    if 0:
        pass  # Needed for testing
    else:
        if msg[0] != " ":
            msg = "==> " + msg
        if 0:
            print(msg)
        else:
            with open("debug_client.txt", "a") as f:
                f.write(f"{msg}\n")
