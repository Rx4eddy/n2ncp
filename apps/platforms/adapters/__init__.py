from .atcoder import AtCoder
from .base import Adapter, PlatformError
from .codechef import CodeChef
from .codeforces import Codeforces


class CSES(Adapter):
    key = "cses"
    limitation = "CSES has no supported public bio-token verification source. Log solves manually."


ADAPTERS = {a.key: a for a in [Codeforces(), AtCoder(), CodeChef(), CSES()]}
CONTEST_PLATFORMS = tuple(k for k, adapter in ADAPTERS.items() if adapter.can_contests)


def get_adapter(platform):
    # LeetCode is deliberately absent: never instantiate a network integration for it.
    if platform not in ADAPTERS:
        raise PlatformError("This platform has no network integration")
    return ADAPTERS[platform]
