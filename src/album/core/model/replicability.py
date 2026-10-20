"""What keeps a deployed solution from being technically replicable (#265).

Technically replicable means that the same solution call gives the same computational
result. album deploy names what stands against it, stores it with the solution and deploys
some of it only with --no-replicability.
"""

from typing import NamedTuple


class ReplicabilityReason(NamedTuple):
    """Something that keeps a solution from being technically replicable.

    Attributes:
        text:
            What it is, e.g. 'resource "model" has no hash, its content is not verified'.
        needs_flag:
            Whether album deploy only deploys the solution with --no-replicability.
    """

    text: str
    needs_flag: bool = False
