from dataclasses import dataclass, field
import uuid

@dataclass
class Person:
    name: str
    tag: str
    image_path: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)