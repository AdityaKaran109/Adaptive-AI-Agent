"""The scripted conversations for the chat demo.

One project-specific fact, stated five times by a simulated user across five separate
sessions, each phrased differently. The fact is not inferable from the error message or
from general knowledge - protobuf stubs being gitignored is a local convention - so a
cold session cannot produce it by reasoning. That is what makes it a fair test.
"""

from __future__ import annotations

from typing import NamedTuple

# The thing the assistant has to learn. Checked literally, so keep it short.
KEY_FACT = "make proto"

USER_ID = "chat-demo-user"


class Exchange(NamedTuple):
    question: str
    correction: str


SESSIONS: list[Exchange] = [
    Exchange(
        "My build is failing with ImportError: cannot import name 'order_pb2' from "
        "'acme.orders'. What should I do?",
        "No, that's not it. In this repo the protobuf stubs are gitignored - you have to "
        "run `make proto` after every pull.",
    ),
    Exchange(
        "Fresh clone and pytest won't even collect: ModuleNotFoundError for order_pb2. Ideas?",
        "Clearing caches won't help. The fix is `make proto` - the generated stubs are not "
        "checked in.",
    ),
    Exchange(
        "I pulled main this morning and now everything fails on order_pb2. Did someone break "
        "the build?",
        "Nothing is broken. The .proto files changed, so you need to run `make proto` again.",
    ),
    Exchange(
        "CI is green but locally I get cannot import name 'order_pb2'. Why the difference?",
        "Because CI runs `make proto` in its setup step and your local environment does not. "
        "Run `make proto`.",
    ),
    Exchange(
        "New laptop, just set the repo up, and I immediately get an ImportError on order_pb2. "
        "Missing dependency?",
        "Not a dependency. Run `make proto` to generate the stubs - it is a required setup "
        "step on this project.",
    ),
]

# The question asked in the evaluation sessions. Same problem, wording it has not seen.
EVAL_QUESTION = (
    "Just pulled the latest main and now I'm getting ImportError: cannot import name "
    "'order_pb2'. What now?"
)
