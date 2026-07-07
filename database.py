import json
import os
from typing import List
from models import Person

class Database:
    def __init__(self, path="data.json"):
        self.path = path
        if not os.path.exists(self.path):
            with open(self.path, "w") as f:
                json.dump([], f)

    def load(self) -> List[Person]:
        with open(self.path, "r") as f:
            data = json.load(f)
        return [Person(**p) for p in data]

    def save(self, people: List[Person]):
        with open(self.path, "w") as f:
            json.dump([p.__dict__ for p in people], f, indent=2)

    def add_person(self, person: Person):
        people = self.load()
        people.append(person)
        self.save(people)
