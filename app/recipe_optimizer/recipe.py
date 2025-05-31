from typing import List, Dict
from recipe_stage import RecipeStage
from dataclasses import dataclass
from typing import Optional

from dataclasses import dataclass
from typing import Optional
from decimal import Decimal


@dataclass
class Ingredient:
    """Class representing a recipe ingredient with its quantity, unit, and cost."""
    name: str
    quantity: float
    unit: str
    cost_per_unit: Decimal
    description: Optional[str] = None

    def scale(self, factor: float) -> None:
        """Scale the ingredient quantity by a factor."""
        self.quantity *= factor

    def get_cost(self) -> Decimal:
        """Calculate the total cost of the ingredient."""
        return Decimal(str(self.quantity)) * self.cost_per_unit

    def to_dict(self) -> dict:
        """Convert ingredient to dictionary representation."""
        return {
            "quantity": self.quantity,
            "unit": self.unit,
            "cost_per_unit": str(self.cost_per_unit),
            "total_cost": str(self.get_cost()),
            "description": self.description
        }

class Recipe:
    def __init__(self, name: str, selling_price: Decimal = Decimal('0'), 
                 overhead_cost: Decimal = Decimal('0')):
        self.name = name
        self.ingredients: Dict[str, Ingredient] = {}
        self.stages: List[RecipeStage] = []
        self.selling_price = selling_price
        self.overhead_cost = overhead_cost
        self.servings: int = 1

    def add_ingredient(self, name: str, quantity: float, unit: str, 
                      cost_per_unit: Decimal, description: Optional[str] = None) -> None:
        """Add a new ingredient to the recipe."""
        self.ingredients[name] = Ingredient(name, quantity, unit, cost_per_unit, description)

    def remove_ingredient(self, ingredient_name: str) -> bool:
        """Remove an ingredient from the recipe."""
        if ingredient_name in self.ingredients:
            del self.ingredients[ingredient_name]
            return True
        return False

    def get_ingredient(self, ingredient_name: str) -> Optional[Ingredient]:
        """Get an ingredient by name."""
        return self.ingredients.get(ingredient_name)

    def get_all_ingredients(self) -> Dict[str, Ingredient]:
        """Get all ingredients in the recipe."""
        return self.ingredients.copy()

    def scale_recipe(self, factor: float) -> None:
        """Scale all ingredient quantities by a factor."""
        for ingredient in self.ingredients.values():
            ingredient.scale(factor)
        self.servings = int(self.servings * factor)

    def set_servings(self, count: int) -> None:
        """Set the number of servings for the recipe."""
        if count > 0:
            factor = count / self.servings
            self.scale_recipe(factor)

    def get_ingredients_cost(self) -> Decimal:
        """Calculate the total cost of all ingredients."""
        return Decimal(sum(ingredient.get_cost() for ingredient in self.ingredients.values()))

    def get_labor_cost(self) -> Decimal:
        """Calculate the total labor cost across all stages."""
        return Decimal(sum(stage.get_labor_cost() for stage in self.stages))

    def get_resource_cost(self) -> Decimal:
        """Calculate the total resource cost across all stages."""
        return Decimal( sum(stage.get_resource_cost() for stage in self.stages))

    def get_total_production_cost(self) -> Decimal:
        """Calculate the total production cost including overhead."""
        return (self.get_ingredients_cost() + 
                self.get_labor_cost() + 
                self.get_resource_cost() + 
                self.overhead_cost)

    def get_cost_per_serving(self) -> Decimal:
        """Calculate the cost per serving."""
        return self.get_total_production_cost() / Decimal(str(self.servings))

    def get_revenue(self) -> Decimal:
        """Calculate total revenue for all servings."""
        return self.selling_price * Decimal(str(self.servings))

    def get_profit(self) -> Decimal:
        """Calculate total profit."""
        return self.get_revenue() - self.get_total_production_cost()

    def get_profit_margin(self) -> Decimal:
        """Calculate the profit margin as a percentage."""
        if self.selling_price == 0:
            return Decimal('0')
        total_cost = self.get_total_production_cost()
        if total_cost == 0:
            return Decimal('100')
        return ((self.get_revenue() - total_cost) / total_cost) * Decimal('100')

    def set_selling_price(self, price: Decimal) -> None:
        """Set the selling price per serving."""
        self.selling_price = price

    def set_overhead_cost(self, cost: Decimal) -> None:
        """Set the overhead cost for the recipe."""
        self.overhead_cost = cost

    def get_cost_breakdown(self) -> dict:
        """Get a detailed breakdown of all costs."""
        return {
            "ingredients_cost": self.get_ingredients_cost(),
            "labor_cost": self.get_labor_cost(),
            "resource_cost": self.get_resource_cost(),
            "overhead_cost": self.overhead_cost,
            "total_cost": self.get_total_production_cost(),
            "cost_per_serving": self.get_cost_per_serving(),
            "selling_price_per_serving": self.selling_price,
            "total_revenue": self.get_revenue(),
            "profit": self.get_profit(),
            "profit_margin": self.get_profit_margin(),
            "servings": self.servings
        }

    def get_name(self) -> str:
        return self.name

    def add_stage(self, stage: RecipeStage) -> None:
        """Add a new stage to the recipe."""
        self.stages.append(stage)

    def remove_stage(self, stage: RecipeStage) -> bool:
        """Remove a stage from the recipe."""
        if stage in self.stages:
            self.stages.remove(stage)
            return True
        return False

    def get_stages(self) -> List[RecipeStage]:
        """Get all stages in the recipe."""
        return self.stages.copy()

    def get_total_duration(self) -> float:
        """Calculate the total duration of all stages in seconds."""
        return sum(stage.get_duration() for stage in self.stages)

    def suggest_selling_price(self, target_margin: Decimal) -> Decimal:
        """Calculate suggested selling price to achieve target profit margin."""
        cost_per_serving = self.get_cost_per_serving()
        suggested_price = cost_per_serving * (1 + target_margin / Decimal('100'))
        return suggested_price.quantize(Decimal('0.01'))


def main():
    """Test the Recipe class functionality with cost analysis."""
    from datetime import datetime, timedelta
    from recipe_stage import StageType, ResourceType
    from decimal import Decimal

    # Create a new recipe with selling price and overhead
    croissant = Recipe(
        "Classic French Croissants",
        selling_price=Decimal('3.50'),  # $3.50 per croissant
        overhead_cost=Decimal('5.00')   # $5.00 fixed overhead per batch
    )
    croissant.set_servings(12)  # One batch makes 12 croissants

    # Add ingredients with costs
    croissant.add_ingredient(
        "bread flour", 500, "grams", 
        cost_per_unit=Decimal('0.002'),  # $2 per kg
        description="High-protein bread flour, preferably 12-13% protein content"
    )
    croissant.add_ingredient(
        "salt", 10, "grams",
        cost_per_unit=Decimal('0.001'),  # $1 per kg
        description="Fine sea salt"
    )
    croissant.add_ingredient(
        "sugar", 55, "grams",
        cost_per_unit=Decimal('0.003'),  # $3 per kg
        description="Granulated sugar"
    )
    croissant.add_ingredient(
        "active dry yeast", 14, "grams",
        cost_per_unit=Decimal('0.04'),  # $40 per kg
        description="Fresh active dry yeast"
    )
    croissant.add_ingredient(
        "cold water", 150, "ml",
        cost_per_unit=Decimal('0.001'),  # $1 per liter
        description="Cold filtered water"
    )
    croissant.add_ingredient(
        "cold milk", 150, "ml",
        cost_per_unit=Decimal('0.003'),  # $3 per liter
        description="Cold whole milk"
    )
    croissant.add_ingredient(
        "unsalted butter", 280, "grams",
        cost_per_unit=Decimal('0.012'),  # $12 per kg
        description="High-quality European-style butter, cold"
    )

    # Create stages with labor and resource costs
    base_time = datetime.now()
    
    # 1. Initial mixing stage
    mixing = RecipeStage(
        StageType.MIX,
        base_time,
        base_time + timedelta(minutes=15),
        labor_cost_per_hour=Decimal('20.00')  # $20/hour labor
    )
    mixing.add_resource_dependency(ResourceType.MIXER, Decimal('5.00'))  # $5/hour for mixer
    croissant.add_stage(mixing)

    # 2. First rest/proof
    first_rest = RecipeStage(
        StageType.REST,
        base_time + timedelta(minutes=15),
        base_time + timedelta(minutes=75),
        labor_cost_per_hour=Decimal('0.00')  # No labor cost during proofing
    )
    first_rest.add_resource_dependency(ResourceType.FRIDGE, Decimal('1.00'))  # $1/hour for fridge
    croissant.add_stage(first_rest)

    # 3. Lamination
    lamination = RecipeStage(
        StageType.PREP,
        base_time + timedelta(minutes=75),
        base_time + timedelta(minutes=105),
        labor_cost_per_hour=Decimal('25.00')  # $25/hour for skilled labor
    )
    lamination.add_resource_dependency(ResourceType.COUNTER_SPACE, Decimal('0.50'))
    croissant.add_stage(lamination)

    # 4. Final proofing
    final_proof = RecipeStage(
        StageType.REST,
        base_time + timedelta(minutes=105),
        base_time + timedelta(hours=3),
        labor_cost_per_hour=Decimal('0.00')
    )
    final_proof.add_resource_dependency(ResourceType.COUNTER_SPACE, Decimal('0.50'))
    croissant.add_stage(final_proof)

    # 5. Baking
    baking = RecipeStage(
        StageType.BAKE,
        base_time + timedelta(hours=3),
        base_time + timedelta(hours=3, minutes=20),
        labor_cost_per_hour=Decimal('20.00')
    )
    baking.add_resource_dependency(ResourceType.OVEN, Decimal('3.00'))  # $3/hour for oven
    croissant.add_stage(baking)

    # Print detailed cost analysis
    cost_breakdown = croissant.get_cost_breakdown()
    
    print(f"\nRecipe: {croissant.get_name()}")
    print(f"Batch size: {cost_breakdown['servings']} servings")
    print("\nCost Breakdown:")
    print(f"Ingredients cost: ${cost_breakdown['ingredients_cost']:.2f}")
    print(f"Labor cost: ${cost_breakdown['labor_cost']:.2f}")
    print(f"Resource cost: ${cost_breakdown['resource_cost']:.2f}")
    print(f"Overhead cost: ${cost_breakdown['overhead_cost']:.2f}")
    print(f"Total production cost: ${cost_breakdown['total_cost']:.2f}")
    print(f"Cost per serving: ${cost_breakdown['cost_per_serving']:.2f}")
    
    print("\nRevenue Analysis:")
    print(f"Selling price per serving: ${cost_breakdown['selling_price_per_serving']:.2f}")
    print(f"Total revenue: ${cost_breakdown['total_revenue']:.2f}")
    print(f"Total profit: ${cost_breakdown['profit']:.2f}")
    print(f"Profit margin: {cost_breakdown['profit_margin']:.1f}%")

    # Test price suggestions
    target_margins = [25, 50, 75]
    print("\nSuggested Prices for Different Target Margins:")
    for margin in target_margins:
        suggested_price = croissant.suggest_selling_price(Decimal(str(margin)))
        print(f"For {margin}% margin: ${suggested_price:.2f} per serving")

    # Test recipe scaling
    print("\nScaling recipe to 24 servings...")
    croissant.set_servings(24)
    new_cost = croissant.get_cost_breakdown()
    print(f"New cost per serving: ${new_cost['cost_per_serving']:.2f}")
    print(f"New total cost: ${new_cost['total_cost']:.2f}")
    print(f"New total revenue: ${new_cost['total_revenue']:.2f}")
    print(f"New profit: ${new_cost['profit']:.2f}")

if __name__ == "__main__":
    main()