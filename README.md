![Boulangerie Milon Logo](assets/hot_plate_logo.avif)

# Boulangerie Milon Recipe Manager

A specialized recipe management and production optimization system designed
for [Boulangerie Milon](https://www.hotplate.com/boulangeriemilon).

## Description

This application helps professional and amateur bakers manage recipes and optimize production scheduling to maximize efficiency and
profit. It provides tools for recipe storage, production timeline planning, and resource optimization.

## Features

- Recipe Management
    - Store and organize bakery recipes
    - Track ingredients and quantities
    - Manage preparation steps and timing
- Production Optimization
    - Schedule multiple recipes concurrently
    - Optimize production timeline
    - Maximize kitchen resource utilization
- Profit Analysis
    - Track ingredient costs
    - Calculate profit margins
    - Optimize production for maximum profitability

## Installation

1. Clone this repository

## Usage

### Command Line Interface

The application can be run using the command line interface with various options:

Arguments:
- `directory`: Path to the directory containing your YAML recipe files

Options:
- `--db-url`: Database URL (default: sqlite:///recipes.db)
- `--debug`: Enable debug mode with detailed logging
- `--reset`: Delete existing database before loading
- `--gui`: Launch GUI after loading data

Example:

### Adding New Recipes

Recipes are stored in YAML format. There are two types of YAML files:

1. `shared_resources.yml` - Contains shared resources and ingredients:

### Database Management

- The application uses SQLite by default (recipes.db)
- Use `--reset` flag to clear existing data
- Custom database URLs can be specified with `--db-url`

### GUI Interface

Launch the graphical interface with:
The GUI provides:
- Recipe visualization and management
- Production schedule optimization
- Resource allocation view
- Cost analysis tools

## Supported Resource Types

- Stand Mixer
- Oven
- Cookie Sheet
- Mixing Bowl
- Workspace
- Chef (Labor)
- Proofing Cabinet

## Stage Types

Recipes can include various stage types for different parts of the baking process. Each stage must include:
- Stage type
- Sequence number
- Start and end times
- Labor cost per hour
- Required resources and their costs

## Troubleshooting

Common issues:
- Database errors: Use `--reset` to create a fresh database
- YAML parsing errors: Check your recipe file format
- Missing resources: Ensure all required resources are defined in shared_resources.yml

For detailed logs, run with the `--debug` flag.