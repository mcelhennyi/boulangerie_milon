from sqlalchemy import create_engine, Column, Integer, String, Enum as SQLEnum, DateTime, DECIMAL, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.recipe_optimizer.recipe_stage import StageType, ResourceType

Base = declarative_base()

# Association table for RecipeTable and IngredientTable
recipe_ingredient = Table(
    'recipe_ingredient',
    Base.metadata,
    Column('recipe_id', Integer, ForeignKey('recipes.id'), primary_key=True),
    Column('ingredient_id', Integer, ForeignKey('ingredients.id'), primary_key=True)
)

# Association table for StageTable and ResourceTable
stage_resource = Table(
    'stage_resource',
    Base.metadata,
    Column('stage_id', Integer, ForeignKey('stages.id'), primary_key=True),
    Column('resource_id', Integer, ForeignKey('resources.id'), primary_key=True),
    Column('cost_per_hour', DECIMAL(10, 2), default=0.00)
)

class RecipeTable(Base):
    __tablename__ = 'recipes'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    servings = Column(Integer)

    def __init__(self, name: str, description: str = None, servings: int = None):
        self.name = name
        self.description = description
        self.servings = servings

    # Relationships
    stages = relationship("StageTable", back_populates="recipe")
    ingredients = relationship("IngredientTable", secondary=recipe_ingredient, back_populates="recipes")

class StageTable(Base):
    __tablename__ = 'stages'

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipes.id'))
    stage_type = Column(SQLEnum(StageType), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    labor_cost_per_hour = Column(DECIMAL(10, 2), default=0.00)
    sequence_number = Column(Integer, nullable=False)  # To maintain stage order

    # Relationships
    recipe = relationship("RecipeTable", back_populates="stages")
    resources = relationship("ResourceTable", secondary=stage_resource, back_populates="stages")

class ResourceTable(Base):
    __tablename__ = 'resources'

    id = Column(Integer, primary_key=True)
    resource_type = Column(SQLEnum(ResourceType), unique=True, nullable=False)
    name = Column(String(255), nullable=False)

    # Relationships
    stages = relationship("StageTable", secondary=stage_resource, back_populates="resources")

class IngredientTable(Base):
    __tablename__ = 'ingredients'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=False)  # e.g., grams, cups, pieces
    cost_per_unit = Column(DECIMAL(10, 2))

    # Relationships
    recipes = relationship("RecipeTable", secondary=recipe_ingredient, back_populates="recipes")

# Create the database and tables
def init_db(connection_string):
    engine = create_engine(connection_string)
    Base.metadata.create_all(engine)
    return engine