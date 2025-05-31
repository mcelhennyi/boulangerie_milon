from enum import Enum
from typing import Set
from datetime import datetime
from decimal import Decimal

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

    def __init__(self, stage_type: StageType, start_time: datetime, end_time: datetime, 
                 labor_cost_per_hour: Decimal = Decimal('0')):
        self.stage_type = stage_type
        self.start_time = start_time
        self.end_time = end_time
        self.labor_cost_per_hour = labor_cost_per_hour
        self.required_resources: Set[ResourceType] = set()
        self.resource_costs: dict[ResourceType, Decimal] = {}

    def add_resource_dependency(self, resource: ResourceType, cost_per_hour: Decimal = Decimal('0')) -> None:
        """Add a required resource and its cost for this stage."""
        self.required_resources.add(resource)
        self.resource_costs[resource] = cost_per_hour

    def get_duration(self) -> float:
        """Calculate the duration of this stage in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    def get_duration_hours(self) -> Decimal:
        """Calculate the duration of this stage in hours."""
        return Decimal(str(self.get_duration() / 3600))

    def get_labor_cost(self) -> Decimal:
        """Calculate the labor cost for this stage."""
        return self.labor_cost_per_hour * self.get_duration_hours()

    def get_resource_cost(self) -> Decimal:
        """Calculate the total resource cost for this stage."""
        duration_hours = self.get_duration_hours()
        return Decimal(sum(cost * duration_hours for cost in self.resource_costs.values()))

    def get_total_cost(self) -> Decimal:
        """Calculate the total cost including labor and resources."""
        return self.get_labor_cost() + self.get_resource_cost()