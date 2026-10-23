from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class Role(Enum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"


@dataclass
class User:
    name: str
    email: str
    password_hash: str  # never the password itself, see werkzeug.security
    role: Role = Role.CUSTOMER
    id: str = field(default_factory=lambda: uuid4().hex)

    def is_admin(self) -> bool:
        return self.role == Role.ADMIN
