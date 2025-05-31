"""Module for managing recipe stages and their dependencies."""
from enum import Enum
from typing import Set
from datetime import datetime


class ResourceType(Enum):
    """Enumeration of resources required for recipe stages."""
    COUNTER_SPACE = "counter"
    OVEN = "oven"
    FRIDGE = "fridge"
    STOVETOP = "stovetop"
    MIXER = "mixer"
    FOOD_PROCESSOR = "food_processor"


class StageType(Enum):
    """Enumeration of possible recipe stage types."""
    PREP = "preparation"
    COOK = "cooking"
    BAKE = "baking"
    CHILL = "chilling"
    REST = "resting"
    MIX = "mixing"


class RecipeStage:
    """A class representing a stage in a recipe with timing and resource requirements."""

    def __init__(self, stage_type: StageType, start_time: datetime, end_time: datetime):
        """
        Initialize a recipe stage.

        Args:
            stage_type: Type of the stage (prep, cook, etc.)
            start_time: When the stage starts
            end_time: When the stage ends
        """
        self.stage_type = stage_type
        self.start_time = start_time
        self.end_time = end_time
        self.required_resources: Set[ResourceType] = set()

    def add_resource_dependency(self, resource: ResourceType) -> None:
        """Add a required resource for this stage."""
        self.required_resources.add(resource)

    def remove_resource_dependency(self, resource: ResourceType) -> None:
        """Remove a resource requirement from this stage."""
        self.required_resources.remove(resource)

    def get_duration(self) -> float:
        """Calculate the duration of this stage in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    def get_required_resources(self) -> Set[ResourceType]:
        """Get all resources required for this stage."""
        return self.required_resources
