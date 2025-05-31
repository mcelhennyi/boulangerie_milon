from enum import Enum
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Set, Dict
from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray


class ResourceType(Enum):
    OVEN = "oven"
    OVEN_RACK = "oven_rack"
    COOKIE_SHEET = "cookie_sheet"
    MIXING_BOWL = "mixing_bowl"
    ITEM = "item"
    STAND_MIXER = "stand_mixer"
    WORKSPACE = "workspace"
    REFRIGERATOR = "refrigerator"
    PROOFING_CABINET = "proofing_cabinet"


@dataclass
class Dimensions:
    length: float
    width: float

    @property
    def area(self) -> float:
        return self.length * self.width


@dataclass
class PlacedItem:
    dimensions: Dimensions
    position: Tuple[int, int]  # (x, y) coordinates
    rotated: bool = False

    @property
    def occupied_cells(self) -> Set[Tuple[int, int]]:
        length = int(self.dimensions.length)
        width = int(self.dimensions.width)
        if self.rotated:
            length, width = width, length

        cells = set()
        for x in range(self.position[0], self.position[0] + length):
            for y in range(self.position[1], self.position[1] + width):
                cells.add((x, y))
        return cells

class Resource(ABC):
    def __init__(self, resource_type: ResourceType):
        self.type = resource_type

    def print_contents(self, indent: int = 0) -> None:
        """Print the contents of this resource and its children."""
        print(" " * indent + self._get_description())
        for child in self.get_children():
            child.print_contents(indent + 2)

    @abstractmethod
    def get_children(self) -> List['Resource']:
        """Get list of child resources."""
        pass

    @abstractmethod
    def _get_description(self) -> str:
        """Get a description of the resource's current state."""
        pass

    @abstractmethod
    def can_add_child(self, child: 'Resource') -> bool:
        """Check if the resource can accommodate a new child resource."""
        pass

    @abstractmethod
    def add_child_resource(self, child: 'Resource') -> bool:
        """Add a child resource if space permits."""
        pass

    @abstractmethod
    def remove_child_resource(self, child: 'Resource') -> bool:
        """Remove a child resource."""
        pass

    @abstractmethod
    def is_full(self) -> bool:
        pass

    @abstractmethod
    def is_empty(self) -> bool:
        pass

    @abstractmethod
    def get_utilization(self) -> float:
        pass


class QuantityResource(Resource):
    def __init__(self, resource_type: ResourceType, max_items: int, unit: str = "items"):
        super().__init__(resource_type)
        self.max_items = max_items
        self.unit = unit
        self._children: List[Resource] = []

    def get_children(self) -> List[Resource]:
        return self._children.copy()

    def _get_description(self) -> str:
        return (f"{self.type.value}: {len(self._children)} {self.unit} "
                f"(capacity: {self.max_items} {self.unit}, "
                f"utilization: {self.get_utilization():.1%})")

    def can_add_child(self, child: Resource) -> bool:
        return len(self._children) < self.max_items

    def add_child_resource(self, child: Resource) -> bool:
        if not self.can_add_child(child):
            return False
        self._children.append(child)
        return True

    def remove_child_resource(self, child: Resource) -> bool:
        if child in self._children:
            self._children.remove(child)
            return True
        return False

    def is_full(self) -> bool:
        return len(self._children) >= self.max_items

    def is_empty(self) -> bool:
        return len(self._children) == 0

    def get_utilization(self) -> float:
        return len(self._children) / self.max_items


class SpatialResource(Resource):
    def __init__(
        self, 
        resource_type: ResourceType, 
        length: float, 
        width: float, 
        unit: str = "inches",
        grid_precision: float = 1.0
    ):
        super().__init__(resource_type)
        self.dimensions = Dimensions(length=length, width=width)
        self.unit = unit
        self.grid_precision = grid_precision
        
        # Calculate grid dimensions based on precision
        grid_length = int(length / grid_precision)
        grid_width = int(width / grid_precision)
        self.grid = np.zeros((grid_length, grid_width), dtype=bool)
        
        # Track children and their placements
        self._children_placements: Dict[Resource, PlacedItem] = {}

    def get_children(self) -> List[Resource]:
        return list(self._children_placements.keys())

    def add_child_resource(self, child: Resource) -> bool:
        if not isinstance(child, (SpatialResource, Item)):
            return False

        child_length = self._to_grid_units(child.dimensions.length)
        child_width = self._to_grid_units(child.dimensions.width)
        placement = self._find_optimal_placement_on_grid(
            child_length, child_width, self.grid
        )

        if placement is None:
            return False

        # Update grid with new item
        x, y = placement.position
        l, w = ((child_width, child_length) if placement.rotated 
                else (child_length, child_width))
        self.grid[x:x + l, y:y + w] = True
        
        # Store child and its placement
        self._children_placements[child] = placement
        return True

    def remove_child_resource(self, child: Resource) -> bool:
        if child not in self._children_placements:
            return False

        placement = self._children_placements[child]
        x, y = placement.position
        l, w = self._to_grid_units(placement.dimensions.length), self._to_grid_units(placement.dimensions.width)
        if placement.rotated:
            l, w = w, l

        # Clear grid space
        self.grid[x:x + l, y:y + w] = False
        
        # Remove child tracking
        del self._children_placements[child]
        return True

    def get_child_position(self, child: Resource) -> Optional[Tuple[float, float]]:
        """Get the position of a child resource in real units."""
        if child not in self._children_placements:
            return None
        grid_pos = self._children_placements[child].position
        return (self._from_grid_units(grid_pos[0]), 
                self._from_grid_units(grid_pos[1]))

    def is_child_rotated(self, child: Resource) -> Optional[bool]:
        """Check if a child resource is rotated from its original orientation."""
        placement = self._children_placements.get(child)
        return placement.rotated if placement else None

    def _to_grid_units(self, value: float) -> int:
        """Convert real units to grid units based on precision."""
        return int(value / self.grid_precision)

    def _from_grid_units(self, value: int) -> float:
        """Convert grid units back to real units."""
        return value * self.grid_precision

    def can_add_child(self, child: Resource) -> bool:
        if not isinstance(child, (SpatialResource, Item)):
            return False
        
        # Create a temporary grid to test placement
        temp_grid = self.grid.copy()
        
        # Account for all existing children
        for existing_child in self.get_children():
            child_length = self._to_grid_units(existing_child.dimensions.length)
            child_width = self._to_grid_units(existing_child.dimensions.width)
            placement = self._find_optimal_placement_on_grid(
                child_length, child_width, temp_grid
            )
            if placement:
                x, y = placement.position
                l, w = ((child_width, child_length) 
                           if placement.rotated 
                           else (child_length, child_width))
                temp_grid[x:x + l, y:y + w] = True

        # Try to find space for the new child
        new_length = self._to_grid_units(child.dimensions.length)
        new_width = self._to_grid_units(child.dimensions.width)
        placement = self._find_optimal_placement_on_grid(
            new_length, new_width, temp_grid
        )
        return placement is not None

    def _find_optimal_placement_on_grid(
        self, 
        length: int, 
        width: int, 
        grid: NDArray[np.bool_]
    ) -> Optional[PlacedItem]:
        """Find optimal placement on a specific grid."""
        best_placement = None
        min_waste = float('inf')

        orientations = [
            (length, width, False),
            (width, length, True)
        ]

        for l, w, rotated in orientations:
            for x in range(grid.shape[0] - l + 1):
                for y in range(grid.shape[1] - w + 1):
                    if not grid[x:x + l, y:y + w].any():
                        temp_grid = grid.copy()
                        temp_grid[x:x + l, y:y + w] = True
                        
                        placed_rows = np.any(temp_grid, axis=1)
                        placed_cols = np.any(temp_grid, axis=0)
                        
                        if not placed_rows.any() or not placed_cols.any():
                            min_x, max_x = 0, l
                            min_y, max_y = 0, w
                        else:
                            min_x = np.where(placed_rows)[0][0]
                            max_x = np.where(placed_rows)[0][-1] + 1
                            min_y = np.where(placed_cols)[0][0]
                            max_y = np.where(placed_cols)[0][-1] + 1

                        used_cells = temp_grid[min_x:max_x, min_y:max_y].sum()
                        total_area = (max_x - min_x) * (max_y - min_y)
                        waste = total_area - used_cells

                        if waste < min_waste:
                            min_waste = waste
                            best_placement = PlacedItem(
                                dimensions=Dimensions(
                                    length=self._from_grid_units(l),
                                    width=self._from_grid_units(w)
                                ),
                                position=(x, y),
                                rotated=rotated
                            )

        return best_placement

    def _get_description(self) -> str:
        return (f"{self.type.value}: {len(self.get_children())} items "
                f"({self.dimensions.length}x{self.dimensions.width} {self.unit}, "
                f"grid: {self.grid_precision} {self.unit}, "
                f"utilization: {self.get_utilization():.1%})")

    def _can_place_at(self, length: int, width: int, pos_x: int, pos_y: int) -> bool:
        """Check if an item can be placed at the specified position."""
        if pos_x + length > self.grid.shape[0] or pos_y + width > self.grid.shape[1]:
            return False

        return not self.grid[pos_x:pos_x + length, pos_y:pos_y + width].any()

    def _find_optimal_placement(self, length: float, width: float) -> Optional[PlacedItem]:
        """Find the optimal placement for a new item that minimizes wasted space."""
        length_int = int(length)
        width_int = int(width)
        best_placement = None
        min_waste = float('inf')

        # Try both orientations
        orientations = [
            (length_int, width_int, False),
            (width_int, length_int, True)
        ]

        for l, w, rotated in orientations:
            # Try each possible position
            for x in range(self.grid.shape[0] - l + 1):
                for y in range(self.grid.shape[1] - w + 1):
                    if self._can_place_at(l, w, x, y):
                        # Calculate waste as the minimum rectangular area that contains
                        # this item and all existing items
                        temp_grid = self.grid.copy()
                        temp_grid[x:x + l, y:y + w] = True
                        
                        # Find the bounds of all placed items
                        placed_rows = np.any(temp_grid, axis=1)
                        placed_cols = np.any(temp_grid, axis=0)
                        
                        if not placed_rows.any() or not placed_cols.any():
                            min_x, max_x = 0, l
                            min_y, max_y = 0, w
                        else:
                            min_x = np.where(placed_rows)[0][0]
                            max_x = np.where(placed_rows)[0][-1] + 1
                            min_y = np.where(placed_cols)[0][0]
                            max_y = np.where(placed_cols)[0][-1] + 1

                        # Calculate waste as unused space in the bounding rectangle
                        used_cells = temp_grid[min_x:max_x, min_y:max_y].sum()
                        total_area = (max_x - min_x) * (max_y - min_y)
                        waste = total_area - used_cells

                        if waste < min_waste:
                            min_waste = waste
                            best_placement = PlacedItem(
                                dimensions=Dimensions(length=length, width=width),
                                position=(x, y),
                                rotated=rotated
                            )

        return best_placement

    def add_item(self, length: float, width: float) -> bool:
        """Add an item with specific dimensions at the optimal position."""
        placement = self._find_optimal_placement(length, width)
        
        if placement is None:
            return False

        # Update the grid with the new item
        l, w = (int(width), int(length)) if placement.rotated else (int(length), int(width))
        x, y = placement.position
        self.grid[x:x + l, y:y + w] = True
        # self.placed_items.append(placement)
        return True

    def remove_item(self, length: float, width: float) -> bool:
        """Remove an item with specific dimensions."""
        # for i, item in enumerate(self.placed_items):
        #     if (abs(item.dimensions.length - length) < 0.0001 and 
        #         abs(item.dimensions.width - width) < 0.0001):
        #         # Clear the grid space
        #         for x, y in item.occupied_cells:
        #             self.grid[x, y] = False
        #         self.placed_items.pop(i)
        #         return True
        return False

    def get_grid_representation(self) -> NDArray[np.bool_]:
        """Return the current grid state."""
        return self.grid.copy()

    def is_full(self) -> bool:
        """Check if no more items can be placed."""
        # Try to find any empty 1x1 space
        return not np.any(self.grid == False)

    def is_empty(self) -> bool:
        """Check if the space is completely empty."""
        return not np.any(self.grid)

    def get_utilization(self) -> float:
        """Calculate the utilization ratio."""
        return np.sum(self.grid) / self.grid.size

    def get_dimensions(self) -> Dimensions:
        return self.dimensions
    

class Item(Resource):
    def __init__(
        self,
        length: float,
        width: float,
        name: str,
        unit: str = "inches"
    ):
        super().__init__(ResourceType.ITEM)
        self.dimensions = Dimensions(length=length, width=width)
        self.name = name
        self.unit = unit

    def get_children(self) -> List['Resource']:
        return []

    def _get_description(self) -> str:
        return (f"{self.name}: {self.dimensions.length}x{self.dimensions.width} "
                f"{self.unit}")

    def can_add_child(self, child: 'Resource') -> bool:
        return False

    def add_child_resource(self, child: 'Resource') -> bool:
        return False
    
    def remove_child_resource(self, child: 'Resource') -> bool:
        return False

    def is_full(self) -> bool:
        return True

    def is_empty(self) -> bool:
        return True

    def get_utilization(self) -> float:
        return 1.0

    def get_dimensions(self) -> Dimensions:
        return self.dimensions

    

def main():
    # Create an oven that can hold 2 racks
    oven = QuantityResource(
        resource_type=ResourceType.OVEN,
        max_items=2,
        unit="racks"
    )

    # Create rack with 2 feet x 3 feet dimensions with 0.5 inch precision
    rack1 = SpatialResource(
        resource_type=ResourceType.OVEN_RACK,
        length=24.0,
        width=36.0,
        unit="inches",
        grid_precision=0.5  # Half-inch precision
    )
    
    # Create cookie sheet with 0.25 inch precision for more precise cookie placement
    cookie_sheet = SpatialResource(
        resource_type=ResourceType.COOKIE_SHEET,
        length=18.0,
        width=13.0,
        unit="inches",
        grid_precision=0.25  # Quarter-inch precision
    )

    # Add rack to oven
    oven.add_child_resource(rack1)

    # Add cookie sheet to rack
    rack1.add_child_resource(cookie_sheet)

    # Create and add some precisely-sized cookies
    cookie1 = Item(
        length=2.75,
        width=2.75,
        name="Chocolate Chip Cookie",
        unit="inches"
    )
    
    cookie2 = Item(
        length=2.25,
        width=2.25,
        name="Sugar Cookie",
        unit="inches"
    )

    cookie_sheet.add_child_resource(cookie1)
    cookie_sheet.add_child_resource(cookie2)

    # Print the hierarchy with grid precision information
    print("\nCurrent kitchen setup:")
    oven.print_contents()

if __name__ == "__main__":
    main()