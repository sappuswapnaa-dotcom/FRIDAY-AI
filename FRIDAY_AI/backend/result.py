from dataclasses import dataclass, field
from typing import Any

@dataclass
class Result:
    ok: bool
    verified: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    def as_dict(self):
        return {'ok':self.ok, 'verified':self.verified, 'message':self.message, 'data':self.data}
