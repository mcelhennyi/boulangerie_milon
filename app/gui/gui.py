import logging
from tkinter import ttk, messagebox
import tkinter as tk
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Optional
from app.recipe_optimizer.recipe import Recipe
from app.recipe_optimizer.recipe_stage import RecipeStage, StageType, ResourceType
from app.database.tables import (
    RecipeTable,
    StageTable,
    IngredientTable,
    ResourceTable,
    recipe_ingredient,
    stage_resource
)
import decimal

class RecipeManagerGUI:
    def __init__(self, root, session, debug=False):
        self.root = root
        self.root.title("Boulangerie Milon Recipe Manager")
        self.session = session
        self.debug = debug
        self.current_recipe_id = None
        
        # Setup logging
        self.setup_logging()
        self.logger.info("Initializing Recipe Manager GUI")
        
        self.setup_gui()
        
    def setup_logging(self):
        """Configure logging based on debug mode"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        
        # Create handlers
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if self.debug else logging.INFO)
        
        # Create formatters and add it to handlers
        if self.debug:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
        
        console_handler.setFormatter(formatter)
        
        # Add handlers to the logger
        self.logger.addHandler(console_handler)
        
    def refresh_recipe_selector(self):
        """Refresh the recipe selector with current database state"""
        self.logger.debug("Refreshing recipe selector")
        try:
            recipes = self.session.query(RecipeTable).all()
            recipe_names = ["-- Create New Recipe --"] + [recipe.name for recipe in recipes]
            self.recipe_selector['values'] = recipe_names
            self.logger.debug(f"Found {len(recipes)} recipes in database")
        except Exception as e:
            self.logger.error(f"Failed to refresh recipe selector: {str(e)}")
            raise

    def save_recipe_to_db(self):
        """Save current recipe state to database"""
        self.logger.debug("Attempting to save recipe to database")
        try:
            name = self.recipe_name.get()
            servings = int(self.servings.get())
            
            if not name:
                self.logger.warning("Attempted to save recipe without name")
                messagebox.showerror("Error", "Recipe name is required")
                return
                
            self.logger.debug(f"Saving recipe: {name} with {servings} servings")
            
            if self.current_recipe_id is None:
                self.logger.debug("Creating new recipe")
                db_recipe = RecipeTable(name=name, servings=servings)
                self.session.add(db_recipe)
                self.session.flush()
                self.current_recipe_id = db_recipe.id
                self.logger.info(f"Created new recipe with ID: {self.current_recipe_id}")
            else:
                self.logger.debug(f"Updating existing recipe ID: {self.current_recipe_id}")
                db_recipe = self.session.query(RecipeTable).get(self.current_recipe_id)
                db_recipe.name = name
                db_recipe.servings = servings

                self.session.commit()
                self.refresh_recipe_selector()
                self.logger.info(f"Successfully saved recipe: {name}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to save recipe: {str(e)}")
            self.session.rollback()
            messagebox.showerror("Error", f"Failed to save recipe: {str(e)}")
            return False

    def add_ingredient_to_db(self, name, quantity, unit, cost, description):
        """Add ingredient to database"""
        try:
            if self.current_recipe_id is None:
                if not self.save_recipe_to_db():
                    return False
                    
            db_recipe = self.session.query(RecipeTable).get(self.current_recipe_id)
            
            # Create or update ingredient
            ingredient = self.session.query(IngredientTable).filter_by(
                name=name, recipe_id=self.current_recipe_id).first()
                
            if ingredient is None:
                ingredient = IngredientTable(
                    name=name,
                    quantity=quantity,
                    unit=unit,
                    cost_per_unit=cost,
                    description=description
                )
                db_recipe.ingredients.append(ingredient)
            else:
                ingredient.quantity = quantity
                ingredient.unit = unit
                ingredient.cost_per_unit = cost
                ingredient.description = description
                
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Failed to save ingredient: {str(e)}")
            return False

    def add_stage_to_db(self, stage_type, duration, labor_cost):
        """Add stage to database"""
        try:
            if self.current_recipe_id is None:
                if not self.save_recipe_to_db():
                    return False
                    
            db_recipe = self.session.query(RecipeTable).get(self.current_recipe_id)
            
            # Calculate sequence number
            sequence_number = len(db_recipe.stages) + 1
            
            # Create stage
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=duration)
            
            stage = Stage(
                recipe=db_recipe,
                stage_type=stage_type,
                sequence_number=sequence_number,
                start_time=start_time,
                end_time=end_time,
                labor_cost_per_hour=labor_cost
            )
            
            self.session.add(stage)
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Failed to save stage: {str(e)}")
            return False

    def add_resource_to_stage(self, stage_id, resource_type, cost_per_hour):
        """Add resource to stage in database"""
        try:
            # Create or get resource
            resource = self.session.query(ResourceTable).filter_by(
                name=resource_type.name,
                resource_type=resource_type
            ).first()
            
            if resource is None:
                resource = ResourceTable(
                    name=resource_type.name,
                    resource_type=resource_type
                )
                self.session.add(resource)
            
            # Add to stage with cost
            stage = self.session.query(StageTable).get(stage_id)
            stage.resources.append(resource)
            
            # Set cost in association table
            self.session.execute(
                stage_resource.insert().values(
                    stage_id=stage.id,
                    resource_id=resource.id,
                    cost_per_hour=cost_per_hour
                )
            )
            
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Failed to save resource: {str(e)}")
            return False

    def on_recipe_selected(self, event):
        """Handle recipe selection"""
        selection = self.recipe_selector.get()
        
        if selection == "-- Create New Recipe --":
            self.current_recipe_id = None
            self.clear_all_fields()
            self.save_button.configure(text="Create Recipe")
            return
            
        # Load the selected recipe from database
        db_recipe = self.session.query(RecipeTable).filter(RecipeTable.name == selection).first()
        if db_recipe:
            self.current_recipe_id = db_recipe.id
            self.load_recipe_from_db(db_recipe)
            self.save_button.configure(text="Update Recipe")

    def load_recipe_from_db(self, db_recipe):
        """Load recipe data from database into GUI"""
        self.clear_all_fields()
        
        # Set basic info
        self.recipe_name.insert(0, db_recipe.name)
        self.servings.insert(0, str(db_recipe.servings))
        
        # Load ingredients
        for ingredient in db_recipe.ingredients:
            self.ingredients_tree.insert('', 'end', text=ingredient.name, values=(
                ingredient.quantity,
                ingredient.unit,
                f"${ingredient.cost_per_unit:.2f}",
                ingredient.description or ""
            ))
        
        # Load stages
        for stage in sorted(db_recipe.stages, key=lambda x: x.sequence_number):
            duration = int((stage.end_time - stage.start_time).total_seconds() / 60)
            resources = ", ".join([f"{r.name}: ${c}/hr" 
                             for r, c in stage.resource_costs.items()])
            
            self.stages_tree.insert('', 'end',
                              text=str(stage.sequence_number),
                              values=(stage.stage_type,
                                    f"{duration} min",
                                    f"${stage.labor_cost_per_hour}/hr",
                                    resources))

    def setup_recipe_selector(self, info_frame):
        # Recipe selector frame
        selector_frame = ttk.Frame(info_frame)
        selector_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        # Get all recipes from database
        recipes = self.session.query(RecipeTable).all()
        recipe_names = ["-- Create New Recipe --"] + [recipe.name for recipe in recipes]
        
        ttk.Label(selector_frame, text="Select Recipe:").pack(side=tk.LEFT, padx=5)
        self.recipe_selector = ttk.Combobox(selector_frame, values=recipe_names, state="readonly")
        self.recipe_selector.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.recipe_selector.set(recipe_names[0])
        
        # Bind selection event
        self.recipe_selector.bind('<<ComboboxSelected>>', self.on_recipe_selected)

    def setup_recipe_tab(self):
        # Recipe basic info frame
        info_frame = ttk.LabelFrame(self.recipe_tab, text="Recipe Information")
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        # Add recipe selector at the top
        self.setup_recipe_selector(info_frame)

        ttk.Label(info_frame, text="Recipe Name:").grid(row=1, column=0, padx=5, pady=5)
        self.recipe_name = ttk.Entry(info_frame)
        self.recipe_name.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(info_frame, text="Servings:").grid(row=2, column=0, padx=5, pady=5)
        self.servings = ttk.Spinbox(info_frame, from_=1, to=1000)
        self.servings.grid(row=2, column=1, padx=5, pady=5)

        # Add create/save recipe button
        self.save_button = ttk.Button(info_frame, text="Create Recipe",
                                    command=self.create_new_recipe)
        self.save_button.grid(row=3, column=0, columnspan=2, pady=5)

        # Rest of the setup remains the same...
        # [Previous ingredients frame setup code]

    def load_recipe_to_gui(self, recipe):
        """Load recipe data into GUI fields"""
        # Clear existing data
        self.clear_all_fields()
        
        # Set basic info
        self.recipe_name.delete(0, tk.END)
        self.recipe_name.insert(0, recipe.name)
        self.servings.delete(0, tk.END)
        self.servings.insert(0, str(recipe.servings))
        
        # Load ingredients
        for name, ingredient in recipe.ingredients.items():
            self.ing_name.delete(0, tk.END)
            self.ing_quantity.delete(0, tk.END)
            self.ing_unit.delete(0, tk.END)
            self.ing_cost.delete(0, tk.END)
            self.ing_desc.delete(0, tk.END)
            
            self.ing_name.insert(0, name)
            self.ing_quantity.insert(0, str(ingredient.quantity))
            self.ing_unit.insert(0, ingredient.unit)
            self.ing_cost.insert(0, str(ingredient.cost_per_unit))
            self.ing_desc.insert(0, ingredient.description or "")
            
            self.add_ingredient()
        
        # Load stages
        for stage in recipe.stages:
            duration_minutes = int((stage.end_time - stage.start_time).total_seconds() / 60)
            
            self.stage_type.set(stage.stage_type.name)
            self.stage_duration.delete(0, tk.END)
            self.stage_duration.insert(0, str(duration_minutes))
            self.labor_cost.delete(0, tk.END)
            self.labor_cost.insert(0, str(stage.labor_cost_per_hour))
            
            self.add_stage()
            
            # Add resources for this stage
            for resource_type, cost in stage.resource_costs.items():
                self.resource_type.set(resource_type.name)
                self.resource_cost.delete(0, tk.END)
                self.resource_cost.insert(0, str(cost))
                
                self.add_resource()

    def clear_all_fields(self):
        """Clear all fields in the GUI"""
        self.recipe_name.delete(0, tk.END)
        self.servings.delete(0, tk.END)
        self.servings.insert(0, "1")
        
        # Clear ingredients
        for item in self.ingredients_tree.get_children():
            self.ingredients_tree.delete(item)
        
        # Clear stages
        for item in self.stages_tree.get_children():
            self.stages_tree.delete(item)
        
        # Clear resources
        for item in self.resources_tree.get_children():
            self.resources_tree.delete(item)
        
        # Reset input fields
        self.clear_ingredient_inputs()
        self.clear_stage_inputs()
        self.resource_type.set('')
        self.resource_cost.delete(0, tk.END)
        
        # Reset cost fields
        self.overhead_cost.delete(0, tk.END)
        self.profit_margin.delete(0, tk.END)
        self.auto_calculate.set(False)

    def setup_gui(self):
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create tabs
        self.recipe_tab = ttk.Frame(self.notebook)
        self.stages_tab = ttk.Frame(self.notebook)
        self.resources_tab = ttk.Frame(self.notebook)
        self.costs_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.recipe_tab, text="Recipe Details")
        self.notebook.add(self.stages_tab, text="Stages")
        self.notebook.add(self.resources_tab, text="Resources")
        self.notebook.add(self.costs_tab, text="Costs & Pricing")

        self.setup_recipe_tab()
        self.setup_stages_tab()
        self.setup_resources_tab()
        self.setup_costs_tab()

    def setup_stages_tab(self):
        # Stages list frame
        stages_frame = ttk.LabelFrame(self.stages_tab, text="Recipe Stages")
        stages_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Stages list
        self.stages_tree = ttk.Treeview(stages_frame,
                                        columns=("Type", "Duration", "Labor", "Resources"))
        self.stages_tree.heading("#0", text="Stage")
        self.stages_tree.heading("Type", text="Type")
        self.stages_tree.heading("Duration", text="Duration")
        self.stages_tree.heading("Labor", text="Labor Cost/hr")
        self.stages_tree.heading("Resources", text="Resources")
        self.stages_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Add stage frame
        add_stage_frame = ttk.Frame(stages_frame)
        add_stage_frame.pack(fill=tk.X, padx=5, pady=5)

        # Stage type dropdown
        ttk.Label(add_stage_frame, text="Type:").grid(row=0, column=0, padx=2)
        self.stage_type = ttk.Combobox(add_stage_frame,
                                       values=[t.name for t in StageType])
        self.stage_type.grid(row=0, column=1, padx=2)

        # Duration inputs
        ttk.Label(add_stage_frame, text="Duration (min):").grid(row=0, column=2, padx=2)
        self.stage_duration = ttk.Spinbox(add_stage_frame, from_=1, to=1440)
        self.stage_duration.grid(row=0, column=3, padx=2)

        # Labor cost
        ttk.Label(add_stage_frame, text="Labor Cost/hr:").grid(row=0, column=4, padx=2)
        self.labor_cost = ttk.Entry(add_stage_frame)
        self.labor_cost.grid(row=0, column=5, padx=2)

        ttk.Button(add_stage_frame, text="Add Stage",
                   command=self.add_stage).grid(row=0, column=6, padx=2)

    def setup_resources_tab(self):
        # Resources frame
        resources_frame = ttk.LabelFrame(self.resources_tab, text="Stage Resources")
        resources_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Resources list
        self.resources_tree = ttk.Treeview(resources_frame,
                                           columns=("Type", "Cost"))
        self.resources_tree.heading("#0", text="Resource")
        self.resources_tree.heading("Type", text="Type")
        self.resources_tree.heading("Cost", text="Cost/hr")
        self.resources_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Add resource frame
        add_resource_frame = ttk.Frame(resources_frame)
        add_resource_frame.pack(fill=tk.X, padx=5, pady=5)

        # Resource type dropdown
        ttk.Label(add_resource_frame, text="Type:").grid(row=0, column=0, padx=2)
        self.resource_type = ttk.Combobox(add_resource_frame,
                                          values=[r.name for r in ResourceType])
        self.resource_type.grid(row=0, column=1, padx=2)

        # Cost per hour
        ttk.Label(add_resource_frame, text="Cost/hr:").grid(row=0, column=2, padx=2)
        self.resource_cost = ttk.Entry(add_resource_frame)
        self.resource_cost.grid(row=0, column=3, padx=2)

        ttk.Button(add_resource_frame, text="Add Resource",
                   command=self.add_resource).grid(row=0, column=4, padx=2)

    def setup_costs_tab(self):
        # Costs frame
        costs_frame = ttk.LabelFrame(self.costs_tab, text="Cost Analysis")
        costs_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Overhead costs
        ttk.Label(costs_frame, text="Overhead Cost:").grid(row=0, column=0, padx=5, pady=5)
        self.overhead_cost = ttk.Entry(costs_frame)
        self.overhead_cost.grid(row=0, column=1, padx=5, pady=5)

        # Target profit margin
        ttk.Label(costs_frame, text="Target Profit Margin (%):").grid(row=1, column=0, padx=5, pady=5)
        self.profit_margin = ttk.Entry(costs_frame)
        self.profit_margin.grid(row=1, column=1, padx=5, pady=5)

        # Auto calculate price checkbox
        self.auto_calculate = tk.BooleanVar()
        ttk.Checkbutton(costs_frame, text="Auto-calculate price",
                        variable=self.auto_calculate).grid(row=2, column=0, columnspan=2)

        # Cost breakdown display
        breakdown_frame = ttk.LabelFrame(costs_frame, text="Cost Breakdown")
        breakdown_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

        self.cost_labels = {}
        costs = ["Ingredients", "Labor", "Resources", "Overhead", "Total",
                 "Per Serving", "Selling Price", "Profit", "Margin"]

        for i, cost in enumerate(costs):
            ttk.Label(breakdown_frame, text=f"{cost}:").grid(row=i, column=0, padx=5, pady=2)
            self.cost_labels[cost] = ttk.Label(breakdown_frame, text="$0.00")
            self.cost_labels[cost].grid(row=i, column=1, padx=5, pady=2)

    def add_ingredient(self):
        """Handle add ingredient button click"""
        try:
            name = self.ing_name.get()
            if name == "Name":
                return
            
            quantity = float(self.ing_quantity.get())
            unit = self.ing_unit.get()
            cost = Decimal(self.ing_cost.get())
            desc = self.ing_desc.get()
            
            if self.add_ingredient_to_db(name, quantity, unit, cost, desc):
                self.refresh_ingredients_from_db()
                self.clear_ingredient_inputs()
                
        except (ValueError, decimal.InvalidOperation) as e:
            messagebox.showerror("Error", "Invalid input values")

    def add_stage(self):
        """Handle add stage button click"""
        try:
            stage_type = StageType[self.stage_type.get()]
            duration = int(self.stage_duration.get())
            labor_cost = Decimal(self.labor_cost.get())
        
            if self.add_stage_to_db(stage_type, duration, labor_cost):
                self.refresh_stages_from_db()
                self.clear_stage_inputs()
                
        except (ValueError, decimal.InvalidOperation) as e:
            messagebox.showerror("Error", "Invalid input values")

    def update_costs(self):
        if not self.current_recipe:
            return

        breakdown = self.current_recipe.get_cost_breakdown()

        self.cost_labels["Ingredients"].config(
            text=f"${breakdown['ingredients_cost']:.2f}")
        self.cost_labels["Labor"].config(
            text=f"${breakdown['labor_cost']:.2f}")
        self.cost_labels["Resources"].config(
            text=f"${breakdown['resource_cost']:.2f}")
        self.cost_labels["Overhead"].config(
            text=f"${breakdown['overhead_cost']:.2f}")
        self.cost_labels["Total"].config(
            text=f"${breakdown['total_cost']:.2f}")
        self.cost_labels["Per Serving"].config(
            text=f"${breakdown['cost_per_serving']:.2f}")
        self.cost_labels["Selling Price"].config(
            text=f"${breakdown['selling_price_per_serving']:.2f}")
        self.cost_labels["Profit"].config(
            text=f"${breakdown['profit']:.2f}")
        self.cost_labels["Margin"].config(
            text=f"{breakdown['profit_margin']:.1f}%")

    # Add this new method to your RecipeManagerGUI class
    def setup_placeholder(self, entry, placeholder):
        """Sets up placeholder text for an entry widget"""
        entry.insert(0, placeholder)
        entry.configure(foreground='gray')

        def on_focus_in(event):
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                entry.configure(foreground='black')

        def on_focus_out(event):
            if not entry.get():
                entry.insert(0, placeholder)
                entry.configure(foreground='gray')

        entry.bind('<FocusIn>', on_focus_in)
        entry.bind('<FocusOut>', on_focus_out)

    def add_resource(self):
        """Adds a resource to the current recipe"""
        try:
            resource_type = ResourceType[self.resource_type.get()]
            cost = Decimal(self.resource_cost.get())

            if self.current_recipe:
                # Add resource to treeview
                self.resources_tree.insert('', 'end', text=resource_type.name,
                                         values=(resource_type.name, f"${cost:.2f}/hr"))
            
                # Update costs
                self.update_costs()

            # Clear inputs
            self.resource_type.set('')
            self.resource_cost.delete(0, tk.END)

        except (ValueError, decimal.InvalidOperation) as e:
            messagebox.showerror("Error", "Invalid input values")

    def create_new_recipe(self):
        """Handle create/update recipe button click"""
        self.save_recipe_to_db()

    def clear_ingredient_inputs(self):
        """Clears all ingredient input fields"""
        self.ing_name.delete(0, tk.END)
        self.ing_quantity.delete(0, tk.END)
        self.ing_unit.delete(0, tk.END)
        self.ing_cost.delete(0, tk.END)
        self.ing_desc.delete(0, tk.END)
        # Reset placeholders
        self.setup_placeholder(self.ing_name, "Name")
        self.setup_placeholder(self.ing_quantity, "Quantity")
        self.setup_placeholder(self.ing_unit, "Unit")
        self.setup_placeholder(self.ing_cost, "Cost/Unit")
        self.setup_placeholder(self.ing_desc, "Description")

    def refresh_ingredients(self):
        """Refreshes the ingredients treeview with current recipe ingredients"""
        if not self.current_recipe:
            return
        
        # Clear existing items
        for item in self.ingredients_tree.get_children():
            self.ingredients_tree.delete(item)
        
        # Add current ingredients
        for name, ingredient in self.current_recipe.ingredients.items():
            self.ingredients_tree.insert('', 'end', text=name, values=(
                ingredient.quantity,
                ingredient.unit,
                f"${ingredient.cost_per_unit:.2f}",
                ingredient.description or ""
            ))

    def refresh_stages(self):
        """Update the display of stages in the GUI"""
        # Clear existing items
        for item in self.stages_tree.get_children():
            self.stages_tree.delete(item)
        
        # Add current stages
        if self.current_recipe and self.current_recipe.stages:
            for stage in self.current_recipe.stages:
                # Calculate duration in minutes
                duration = (stage.end_time - stage.start_time).total_seconds() / 60
                # Get resources as string
                resources = ", ".join([f"{r.name}: ${c}/hr" 
                                 for r, c in stage.resource_costs.items()])
                
                # Insert stage into tree
                self.stages_tree.insert('', 'end',
                                  text=str(len(self.stages_tree.get_children()) + 1),
                                  values=(stage.stage_type.name,
                                        f"{int(duration)} min",
                                        f"${stage.labor_cost_per_hour}/hr",
                                        resources))

    def clear_stage_inputs(self):
        """Clear all stage-related input fields"""
        self.stage_type.set('')  # Reset the stage type dropdown
        self.stage_duration.delete(0, tk.END)  # Clear duration field
        self.labor_cost.delete(0, tk.END)  # Clear labor cost field


if __name__ == "__main__":
    root = tk.Tk()
    app = RecipeManagerGUI(root)
    
    # Create a sample recipe
    app.recipe_name.insert(0, "Classic French Croissants")
    app.servings.delete(0, tk.END)
    app.servings.insert(0, "12")
    app.create_new_recipe()
    
    # Add sample ingredients
    ingredients = [
        ("bread flour", "500", "grams", "0.002", "High-protein bread flour"),
        ("salt", "10", "grams", "0.001", "Fine sea salt"),
        ("sugar", "55", "grams", "0.003", "Granulated sugar"),
        ("active dry yeast", "14", "grams", "0.04", "Fresh active dry yeast"),
        ("cold water", "150", "ml", "0.001", "Cold filtered water"),
        ("cold milk", "150", "ml", "0.003", "Cold whole milk"),
        ("unsalted butter", "280", "grams", "0.012", "High-quality European butter")
    ]
    
    for ing in ingredients:
        app.ing_name.delete(0, tk.END)
        app.ing_quantity.delete(0, tk.END)
        app.ing_unit.delete(0, tk.END)
        app.ing_cost.delete(0, tk.END)
        app.ing_desc.delete(0, tk.END)
        
        app.ing_name.insert(0, ing[0])
        app.ing_quantity.insert(0, ing[1])
        app.ing_unit.insert(0, ing[2])
        app.ing_cost.insert(0, ing[3])
        app.ing_desc.insert(0, ing[4])
        
        app.add_ingredient()
    
    # Add sample stages
    stages = [
        ("MIX", "15", "20.00"),  # 15 min mixing at $20/hr
        ("REST", "60", "0.00"),   # 60 min resting at $0/hr
        ("PREP", "30", "25.00"),  # 30 min lamination at $25/hr
        ("REST", "120", "0.00"),  # 120 min final proof at $0/hr
        ("BAKE", "20", "20.00")   # 20 min baking at $20/hr
    ]
    
    for stage in stages:
        app.stage_type.set(stage[0])
        app.stage_duration.delete(0, tk.END)
        app.stage_duration.insert(0, stage[1])
        app.labor_cost.delete(0, tk.END)
        app.labor_cost.insert(0, stage[2])
        
        app.add_stage()
    
    # Add sample resources
    resources = [
        ("MIXER", "5.00"),
        ("FRIDGE", "1.00"),
        ("OVEN", "3.00"),
        ("COUNTER_SPACE", "0.50")
    ]
    
    for resource in resources:
        app.resource_type.set(resource[0])
        app.resource_cost.delete(0, tk.END)
        app.resource_cost.insert(0, resource[1])
        
        app.add_resource()
    
    # Set sample costs
    app.overhead_cost.insert(0, "5.00")
    app.profit_margin.insert(0, "35")
    app.auto_calculate.set(True)
    
    root.mainloop()