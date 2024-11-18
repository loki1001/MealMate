# MealMate 🍳

## 📑 Table of Contents
1. [📖 Overview](#overview)
2. [🌟 Key Features](#-key-features)
   - [Recipe Generator](#recipe-generator)
   - [Ingredient Management](#ingredient-management)
   - [AI Recipe Assistant](#ai-recipe-assistant)
   - [Recipe Management](#recipe-management)
3. [🛠 Technical Stack](#-technical-stack)
   - [Backend](#backend)
   - [Frontend](#frontend)
4. [📋 Prerequisites](#-prerequisites)
5. [🚀 Installation](#-installation)
6. [💡 Usage Guide](#-usage-guide)
   - [Account Management](#account-management)
   - [Recipe Generation](#recipe-generation)
   - [Recipe Interaction](#recipe-interaction)
   - [Recipe Assistant Features](#recipe-assistant-features)
   
## 📖 Overview
MealMate is a Django-powered recipe generation platform that transforms your available ingredients into personalized recipes. Leveraging OpenAI's GPT-4, it creates custom recipes tailored to your dietary preferences and serving needs, complete with an AI chatbot for cooking guidance.

## 🌟 Key Features

### Recipe Generator
- **Strict Recipe Mode**: Creates recipes using only your available ingredients plus basic seasonings
- **Flexible Recipe Mode**: Uses your ingredients as a base while adding complementary ingredients
- **Diet Customization**: Supports various dietary preferences:
  - Vegetarian
  - Vegan
  - Gluten-Free
  - Keto
  - Paleo
- **Serving Size Adjustment**: Customize recipes for your needed portion size

### Ingredient Management
- **Pantry Tracking**: Maintain a digital inventory of your available ingredients
- **Custom Units**: Support for various measurement units including:
  - Standard measurements (cups, tablespoons, teaspoons)
  - Metric measurements (grams, kilograms, milliliters)
  - Imperial measurements (ounces, pounds)
  - Custom units for specific items

### AI Recipe Assistant
- **Interactive Chat**: Get real-time cooking guidance for each recipe
- **Cooking Tips**: Ask questions about techniques and methods
- **Ingredient Substitutions**: Get suggestions for ingredient alternatives
- **Recipe Modifications**: Request adjustments to existing recipes
- **Persistent Chat History**: Conversations are saved per recipe for future reference

### Recipe Management
- **Recipe Library**: Save and organize your favorite recipes
- **Accept/Reject System**: Choose to save or regenerate recipes
- **Recipe Details**: View comprehensive recipe information including:
  - Ingredients with precise measurements
  - Step-by-step instructions
  - Cooking time
  - Serving size
  - Dietary category

## 🛠 Technical Stack

### Backend
- **Framework**: Django 4.2.16
- **Database**: SQLite3
- **AI Integration**: OpenAI GPT-4
- **Authentication**: Django built-in auth system

### Frontend
- **Styling**: Tailwind CSS
- **Templating**: Django Templates
- **UI Components**: Custom components with Tailwind classes
- **Responsive Design**: Mobile-friendly interface

## 📋 Prerequisites
- Python 3.8+
- Django 4.2.16+
- OpenAI API key
- Node.js and npm (for Tailwind CSS)

## 🚀 Installation

1. **Clone the Repository**
```bash
git clone https://github.com/loki1001/MealMate
cd MealMate
```

2. **Set Up Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Configuration**
Create a `.env` file in the project root:
```env
DJANGO_SECRET_KEY=your_secret_key
OPENAI_API_KEY=your_openai_api_key
DEBUG=True
```

5. **Database Setup**
```bash
python manage.py migrate
```

6. **Run the Development Server**
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000` in your browser.

## 💡 Usage Guide

### Account Management
1. Create a new account or log in
2. Add ingredients to your pantry inventory
3. Customize your dietary preferences

### Recipe Generation
1. Select ingredients from your inventory or add temporary ingredients
2. Choose between strict or flexible recipe generation
3. Select your dietary preferences
4. Specify the number of servings
5. Review and generate the recipe

### Recipe Interaction
1. Review the generated recipe
2. Accept to save to your library or reject to generate a new one
3. Use the AI assistant for cooking guidance
4. Save favorite recipes to your library

### Recipe Assistant Features
- Ask questions about cooking techniques
- Request ingredient substitutions
- Get clarification on instructions
- Receive cooking tips and tricks