# Audio Threshold Parser. Takes the result from pleep-search (stdin) and
# returns an array.

import json
import sys
from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin

FILTER_AWAY_THRESHOLD = 0.2
THRESHOLD = 0.8


@dataclass
class AudioThreshold(DataClassJsonMixin):
    """
    A data class for audio thresholds.
    """
    title: str
    mse: float
    confidence: float


@dataclass
class Matches(DataClassJsonMixin):
    """
    A data class for matches.
    """
    matches: list[AudioThreshold]


data_raw = Matches.from_json(sys.stdin.read()).matches
data = [x.confidence >= THRESHOLD for x in data_raw
        if x.confidence > FILTER_AWAY_THRESHOLD]
print(json.dumps(data))
