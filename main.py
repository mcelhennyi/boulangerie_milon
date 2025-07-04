import argparse
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.tables import Base, RecipeTable, StageTable, ResourceTable, IngredientTable, stage_resource
from app.recipe_optimizer.recipe_stage import StageType, ResourceType
from datetime import datetime
from decimal import Decimal, InvalidOperation
import yaml
import sys
from pathlib import Path
from typing import Dict, Any, List
import tkinter as tk
from app.gui.gui import RecipeManagerGUI
from sqlalchemy.orm import Session
from app.recipe_optimizer.recipe import Recipe
from app.database.tables import RecipeTable, StageTable, IngredientTable, ResourceTable
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

def setup_logging(debug_mode: bool) -> None:
    """Configure logging based on debug mode."""
    level = logging.DEBUG if debug_mode else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def parse_datetime(dt_str: str) -> datetime:
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError as e:
        logger.error(f"Failed to parse datetime: {dt_str}")
        raise ValueError(f"Invalid datetime format: {dt_str}") from e

def load_yaml_file(file_path: Path) -> Dict[str, Any]:
    """Load and parse a YAML file."""
    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error in {file_path}: {str(e)}")
        raise
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading {file_path}: {str(e)}")
        raise

def load_recipes_from_directory(directory: Path) -> Dict[str, Any]:
    """Load all recipe-related YAML files from a directory."""
    logger.info(f"Loading recipes from directory: {directory}")
    
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        raise FileNotFoundError(f"Directory not found: {directory}")

    # Initialize combined data structure
    combined_data = {
        'resources': [],
        'ingredients': [],
        'recipes': []
    }

    try:
        # Load shared resources and ingredients
        shared_resources = directory / 'shared_resources.yml'
        if shared_resources.exists():
            logger.debug("Loading shared_resources.yml")
            shared_data = load_yaml_file(shared_resources)
            if not isinstance(shared_data, dict):
                raise ValueError("shared_resources.yml must contain a dictionary")
            
            combined_data['resources'] = shared_data.get('resources', [])
            combined_data['ingredients'] = shared_data.get('ingredients', [])
            
            logger.debug(f"Loaded {len(combined_data['resources'])} resources and "
                        f"{len(combined_data['ingredients'])} ingredients")
        else:
            logger.warning("shared_resources.yml not found")

        # Load all recipe files
        recipe_files = list(directory.glob('*.yml'))
        logger.debug(f"Found {len(recipe_files)} YAML files")
        
        for recipe_file in recipe_files:
            if recipe_file.name != 'shared_resources.yml':
                logger.debug(f"Loading recipe file: {recipe_file.name}")
                try:
                    recipe_data = load_yaml_file(recipe_file)
                    if not isinstance(recipe_data, dict):
                        logger.warning(f"Skipping {recipe_file}: not a valid recipe file format")
                        continue
                        
                    if 'recipe' in recipe_data:
                        combined_data['recipes'].append(recipe_data['recipe'])
                        logger.debug(f"Added recipe: {recipe_data['recipe'].get('name', 'unnamed')}")
                    else:
                        logger.warning(f"Skipping {recipe_file}: missing 'recipe' key")
                except Exception as e:
                    logger.error(f"Error loading recipe file {recipe_file}: {e}")
                    raise

        logger.info(f"Successfully loaded {len(combined_data['recipes'])} recipes")
        return combined_data

    except Exception as e:
        logger.error(f"Error loading recipes from directory: {e}")
        raise

def load_db_from_directory(directory_path: str, connection_string: str = 'sqlite:///recipes.db'):
    """Load database from a directory containing YAML files."""
    directory = Path(directory_path)
    logger.info(f"Loading data from directory: {directory}")
    
    try:
        data = load_recipes_from_directory(directory)
        
        # Initialize database
        logger.debug(f"Initializing database with connection string: {connection_string}")
        engine = create_engine(connection_string)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Create resources lookup dictionary
            resources_dict = {}
            for resource_data in data.get('resources', []):
                try:
                    # Map resource names to their types
                    resource_type_mapping = {
                        'Stand Mixer': ResourceType.STAND_MIXER,
                        'Oven': ResourceType.OVEN,
                        'Cookie Sheet': ResourceType.COOKIE_SHEET,
                        'Mixing Bowl': ResourceType.MIXING_BOWL,
                        'Workspace': ResourceType.WORKSPACE,
                        'Chef': ResourceType.LABOR,
                        'Proofing Cabinet': ResourceType.PROOFING_CABINET
                    }
                    
                    resource_name = resource_data['name']
                    resource_type = resource_type_mapping.get(resource_name)
                    if not resource_type:
                        raise ValueError(f"Unknown resource type for: {resource_name}")

                    logger.debug(f"Creating resource: {resource_name} of type {resource_type}")
                    resource = ResourceTable(
                        name=resource_name,
                        resource_type=resource_type
                    )
                    session.add(resource)
                    resources_dict[resource.name] = resource
                except KeyError as e:
                    logger.error(f"Missing required field in resource data: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Error creating resource {resource_data.get('name', 'unknown')}: {e}")
                    raise

            # Create ingredients lookup dictionary
            ingredients_dict = {}
            for ingredient_data in data.get('ingredients', []):
                try:
                    logger.debug(f"Creating ingredient: {ingredient_data['name']}")
                    ingredient = IngredientTable(
                        name=ingredient_data['name'],
                        unit=ingredient_data['unit'],
                        cost_per_unit=Decimal(str(ingredient_data['cost_per_unit']))
                    )
                    session.add(ingredient)
                    ingredients_dict[ingredient.name] = ingredient
                except (KeyError, InvalidOperation) as e:
                    logger.error(f"Error in ingredient data {ingredient_data.get('name', 'unknown')}: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error creating ingredient: {e}")
                    raise

            # Create recipes with their stages and relationships
            for recipe_data in data.get('recipes', []):
                try:
                    logger.debug(f"Creating recipe: {recipe_data['name']}")
                    recipe = RecipeTable(
                        name=recipe_data['name'],
                        description=recipe_data.get('description'),
                        servings=recipe_data.get('servings')
                    )

                    # Add ingredients to recipe
                    for ingredient_ref in recipe_data.get('ingredients', []):
                        ingredient = ingredients_dict.get(ingredient_ref['name'])
                        if ingredient:
                            recipe.ingredients.append(ingredient)
                        else:
                            logger.warning(f"Ingredient not found: {ingredient_ref['name']}")

                    # Create stages
                    for stage_data in recipe_data.get('stages', []):
                        try:
                            stage_type_str = stage_data['stage_type']
                            try:
                                stage_type = StageType[stage_type_str]
                            except KeyError:
                                logger.error(f"Invalid stage type: {stage_type_str}")
                                raise ValueError(f"Invalid stage type: {stage_type_str}")

                            logger.debug(f"Creating stage: {stage_type} for recipe {recipe.name}")
                            stage = StageTable(
                                stage_type=stage_type,
                                sequence_number=stage_data['sequence_number'],
                                start_time=parse_datetime(stage_data['start_time']),
                                end_time=parse_datetime(stage_data['end_time']),
                                labor_cost_per_hour=Decimal(str(stage_data['labor_cost_per_hour']))
                            )

                            # Add resources to stage
                            for resource_ref in stage_data.get('resources', []):
                                resource = resources_dict.get(resource_ref['name'])
                                if resource:
                                    stage.resources.append(resource)
                                    # Update the association table with cost_per_hour
                                    session.execute(
                                        stage_resource.update().where(
                                            (stage_resource.c.stage_id == stage.id) &
                                            (stage_resource.c.resource_id == resource.id)
                                        ).values(
                                            cost_per_hour=Decimal(str(resource_ref['cost_per_hour']))
                                        )
                                    )
                                else:
                                    logger.warning(f"Resource not found: {resource_ref['name']}")

                            recipe.stages.append(stage)
                        except Exception as e:
                            logger.error(f"Error creating stage in recipe {recipe.name}: {e}")
                            raise

                    session.add(recipe)
                except Exception as e:
                    logger.error(f"Error creating recipe {recipe_data.get('name', 'unknown')}: {e}")
                    raise

            # Commit all changes
            session.commit()
            logger.info(f"Successfully loaded data from {directory_path}")

        except Exception as e:
            logger.error(f"Error loading database: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

def delete_database(connection_string: str) -> None:
    """Delete the database file if it exists."""
    try:
        # Extract database path from connection string
        if connection_string.startswith('sqlite:///'):
            db_path = Path(connection_string[10:])
            if db_path.exists():
                logger.info(f"Deleting database file: {db_path}")
                db_path.unlink()
                logger.info("Database deleted successfully")
            else:
                logger.info("No database file found to delete")
        else:
            logger.warning("Database deletion only supported for SQLite databases")
            
    except Exception as e:
        logger.error(f"Error deleting database: {e}")
        raise

def load_recipe_from_db(db_recipe: RecipeTable, session: Session) -> Recipe:
    """Convert a database recipe to a Recipe object."""
    recipe = Recipe(db_recipe.name, db_recipe.servings)
    
    # Load ingredients
    for db_ingredient in db_recipe.ingredients:
        recipe.add_ingredient(
            db_ingredient.name,
            1.0,  # Default quantity as it's not stored in DB
            db_ingredient.unit,
            db_ingredient.cost_per_unit,
            ""  # Default description
        )
    
    # Load stages
    for db_stage in sorted(db_recipe.stages, key=lambda x: x.sequence_number):
        stage = recipe.add_stage_from_db(
            db_stage.stage_type,
            db_stage.start_time,
            db_stage.end_time,
            db_stage.labor_cost_per_hour
        )
        
        # Add resources to stage
        for resource in db_stage.resources:
            cost_per_hour = next(
                (assoc.cost_per_hour 
                 for assoc in db_stage.resources 
                 if assoc.id == resource.id),
                Decimal('0')
            )
            stage.add_resource_dependency(resource.resource_type, cost_per_hour)
    
    return recipe

def launch_gui(session: Session, debug: bool = False) -> None:
    """
    Launch the GUI with data from the database.
    
    Args:
        session: SQLAlchemy session
        debug: Enable debug mode for detailed logging
    """
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    logger = logging.getLogger(__name__)
    logger.info("Launching Recipe Manager GUI")
    
    try:
        root = tk.Tk()
        app = RecipeManagerGUI(root, session, debug=debug)
        logger.debug("GUI initialized successfully")
        root.mainloop()
    except Exception as e:
        logger.error(f"Failed to launch GUI: {str(e)}", exc_info=True)
        raise

def main():
    parser = argparse.ArgumentParser(description='Load recipe database from YAML files directory')
    parser.add_argument('directory', help='Directory containing the YAML files')
    parser.add_argument('--db-url', default='sqlite:///recipes.db',
                      help='Database URL (default: sqlite:///recipes.db)')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug mode with detailed logging')
    parser.add_argument('--reset', action='store_true',
                      help='Delete existing database before loading')
    parser.add_argument('--gui', action='store_true',
                      help='Launch GUI after loading data')
    
    args = parser.parse_args()
    
    # Setup logging based on debug mode
    setup_logging(args.debug)
    
    try:
        if args.reset:
            delete_database(args.db_url)
        
        engine = load_db_from_directory(args.directory, args.db_url)
        
        if args.gui:
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                launch_gui(session, debug=args.debug)
            finally:
                session.close()
                
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()