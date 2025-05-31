class Recipe:
    def __init__(self, name):
        self.name = name
        self.ingredients = {}

    def add_ingredient(self, ingredient_name: str, quantity: float, unit: str):
        self.ingredients[ingredient_name] = {"quantity": quantity, "unit": unit}

    def remove_ingredient(self, ingredient_name: str):
        if ingredient_name in self.ingredients:
            del self.ingredients[ingredient_name]

    def get_ingredient(self, ingredient_name: str) -> dict:
        return self.ingredients.get(ingredient_name)

    def get_all_ingredients(self) -> dict:
        return self.ingredients

    def get_name(self) -> str:
        return self.name


