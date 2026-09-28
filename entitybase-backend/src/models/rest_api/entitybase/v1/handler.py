from abc import ABC
from typing import Any

from pydantic import BaseModel


class Handler(ABC, BaseModel):
    state: Any  # This is the app state
