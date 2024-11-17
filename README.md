# Meal Mate 🍳

## Overview
Meal Mate is a smart recipe generation platform built with Django that transforms your available ingredients into personalized recipes. Powered by OpenAI's GPT-4, it creates custom recipes tailored to your dietary preferences and serving needs, complete with an AI chatbot for cooking guidance.

## 🌟 Key Features

### Core Functionality
- **Sign Up / Log In**: Users create an account and log in to manage ingredients and recipes.
- **Smart Recipe Generation**: Leverages GPT-4 to create unique recipes from your available ingredients
- **Ingredient Management**: Track and manage your pantry inventory
- **Recipe Customization**: Adjust serving sizes and dietary preferences
- **AI Recipe Assistant**: Get real-time cooking advice and ingredient substitutions

### User Experience
- **Intuitive Interface**: Clean, responsive design using Tailwind CSS
- **Recipe Lifecycle**: Accept, reject, or modify generated recipes
- **Personal Recipe Library**: Save and manage your favorite recipes
- **Multi-Diet Support**: Accommodates various dietary preferences:
  - Vegetarian
  - Vegan
  - Gluten-Free
  - Keto
  - Paleo

## 📋 Prerequisites
- Python 3.8 or higher
- Django 4.0 or higher
- OpenAI API key
- Node.js and npm (for Tailwind CSS)

## 🚀 Quick Start

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/loki1001/MealMate.git
cd MealMate

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file in the project root:
```env
DJANGO_SECRET_KEY=your_secret_key
OPENAI_API_KEY=your_openai_api_key
DEBUG=True
```

### 3. Database Setup
```bash
# Apply migrations
python manage.py migrate
```

### 4. Run the Application
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000` in your browser.

## 📱 Usage Guide

### 1. Account Setup
1. Create an account or log in
2. Add ingredients to your inventory

### 2. Generate Recipes
1. Select ingredients for your recipe
2. Choose diet type and servings
3. Review generated recipe
4. Accept or reject the recipe
5. Save to your recipe library

### 3. Recipe Assistant
- Ask questions about cooking techniques
- Get ingredient substitution suggestions
- Request modifications to recipes
- Learn cooking tips and tricks