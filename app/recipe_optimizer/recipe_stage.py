"""Recipe stage management module for handling recipe preparation steps and their dependencies."""
from enum import Enum
from typing import Set
from datetime import datetime


class ResourceType(Enum):
    """Available resource types that can be required by recipe stages."""
    COUNTER_SPACE = "counter_space"
    OVEN = "oven"
    FRIDGE = "fridge"
    STOVETOP = "stovetop"
    MIXER = "mixer"
    FOOD_PROCESSOR = "food_processor"


class StageType(Enum):
    """Types of stages in recipe preparation."""
    PREP = "prep"
    COOK = "cook"
    BAKE = "bake"
    CHILL = "chill"
    REST = "rest"
    MIX = "mix"


class RecipeStage:
    """
    A recipe stage represents a single step in recipe preparation.

    Each stage has a type, start and end time, and required resources.
    """

    def __init__(self, stage_type: StageType, start_time: datetime, end_time: datetime):
        """
        Initialize a new recipe stage.

        Args:
            stage_type: The type of the stage (e.g., PREP, COOK)
            start_time: When the stage should start
            end_time: When the stage should end
        """
        self.stage_type = stage_type
        self.start_time = start_time
        self.end_time = end_time
        self.required_resources: Set[ResourceType] = set()

    def add_resource_dependency(self, resource: ResourceType) -> None:
        """Add a required resource for this stage."""
        self.required_resources.add(resource)

    def remove_resource_dependency(self, resource: ResourceType) -> None:
        """Remove a resource dependency from this stage."""
        self.required_resources.remove(resource)

    def get_duration(self) -> float:
        """Get the duration of this stage in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    def get_required_resources(self) -> Set[ResourceType]:
        """Get the set of resources required for this stage."""
        return self.required_resources
