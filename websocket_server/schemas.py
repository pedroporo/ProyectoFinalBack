from typing import Dict, Any, Callable, Optional
import json


class FunctionCallItem:
    def __init__(self, name: str, arguments: str, call_id: Optional[str] = None):
        self.name = name
        self.arguments = arguments
        self.call_id = call_id


class FunctionSchema:
    def __init__(self, name: str, parameters: Dict[str, Any], description: Optional[str] = None):
        self.name = name
        self.type = "function"
        self.description = description
        self.parameters = parameters

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "parameters": self.parameters,
        }

    def toJSON(self):
        return json.dumps(self.to_dict(), indent=4)


class FunctionHandler:
    def __init__(self, schema: FunctionSchema, handler: Callable[[Any], Any]):
        self.schema = schema
        self.handler = handler
