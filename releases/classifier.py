import re
from dataclasses import dataclass


CLASSIFIER_VERSION = "rules-2"


@dataclass(frozen=True)
class Classification:
    change_type: str
    rule: str


RULES = [
    ("security", "security-explicit", re.compile(r"\b(?:security|vulnerabilit\w*|cve-\d{4}-\d+)\b", re.IGNORECASE)),
    ("fixed", "fix-leading-verb", re.compile(r"^(?:fix\w*|correct\w*|prevent\w*|repair\w*|avoid\w*)\b", re.IGNORECASE)),
    ("deprecated", "deprecation-leading-verb", re.compile(r"^(?:deprecat\w*|mark\w+ .{0,100}\bdeprecated)\b", re.IGNORECASE)),
    ("removed", "removal-leading-verb", re.compile(r"^(?:remov\w*|disallow\w*|drop(?:ped|ping)? support)\b", re.IGNORECASE)),
    ("added", "addition-leading-verb", re.compile(r"^(?:add(?:ed|ing)?|introduc\w*|implement\w*|allow(?:ed|ing)?|support(?:ed|ing)?|provid\w*|creat\w*|enabl\w*|new)\b", re.IGNORECASE)),
    ("added", "addition-can-now", re.compile(r"\bcan now\b", re.IGNORECASE)),
    ("deprecated", "deprecation-explicit", re.compile(r"\bdeprecated\b", re.IGNORECASE)),
    ("removed", "removal-no-longer", re.compile(r"\bno longer\b", re.IGNORECASE)),
    ("changed", "change-leading-verb", re.compile(r"^(?:chang\w*|improv\w*|updat\w*|adjust\w*|renam\w*)\b", re.IGNORECASE)),
]


def classify_change(text):
    for change_type, rule, pattern in RULES:
        if pattern.search(text):
            return Classification(change_type=change_type, rule=rule)
    return Classification(change_type="other", rule="no-explicit-keyword")
