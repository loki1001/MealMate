# views.py
import json

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Ingredient, Recipe, RecipeIngredient
import openai
import os
from django.contrib.auth import login, authenticate
from .forms import SignUpForm
from fractions import Fraction

def convert_to_decimal(quantity):
    try:
        # Convert the quantity to a decimal number
        return str(float(Fraction(quantity)))
    except ValueError:
        # Return the original value if conversion fails
        return quantity

def home(request):
    return render(request, 'recipes/home.html')

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in automatically after registration
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=user.username, password=raw_password)
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'recipes/signup.html', {'form': form})


@login_required(login_url='/login/')
def my_items(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        quantity = request.POST.get('quantity')
        unit = request.POST.get('unit')
        Ingredient.objects.create(
            user=request.user,
            name=name,
            quantity=quantity,
            unit=unit
        )
        return redirect('my_items')

    ingredients = Ingredient.objects.filter(user=request.user)
    return render(request, 'recipes/my_items.html', {'ingredients': ingredients})


@login_required(login_url='/login/')
def delete_ingredient(request, ingredient_id):
    try:
        ingredient = Ingredient.objects.get(id=ingredient_id, user=request.user)
        ingredient.delete()
        messages.success(request, 'Ingredient deleted successfully.')
    except Ingredient.DoesNotExist:
        messages.error(request, 'Ingredient not found.')
    return redirect('my_items')


@login_required(login_url='/login/')
def generate_recipe(request):
    ingredients = Ingredient.objects.filter(user=request.user)
    return render(request, 'recipes/generate_recipe.html', {'ingredients': ingredients})


@login_required(login_url='/login/')
def choose_diet(request):
    if request.method == 'POST':
        # Get database ingredients
        db_ingredients = request.POST.get('db_ingredients', '').split(',')
        db_ingredients = [id for id in db_ingredients if id]

        # Get temporary ingredients
        temp_ingredients_json = request.POST.get('temp_ingredients', '[]')
        try:
            temp_ingredients = json.loads(temp_ingredients_json)

            # Store both types of ingredients in session
            request.session['db_ingredients'] = db_ingredients
            request.session['temp_ingredients'] = temp_ingredients

            return render(request, 'recipes/choose_diet.html')
        except json.JSONDecodeError:
            messages.error(request, 'Error processing ingredients')
            return redirect('generate_recipe')
    return redirect('generate_recipe')


@login_required(login_url='/login/')
def choose_servings(request):
    if request.method == 'POST':
        diet_type = request.POST.get('diet_type')
        request.session['diet_type'] = diet_type
        return render(request, 'recipes/choose_servings.html')
    return redirect('choose_diet')


@login_required(login_url='/login/')
def review(request):
    if request.method == 'POST':
        servings = request.POST.get('servings')
        request.session['servings'] = servings

        # Get both types of ingredients from session
        db_ingredients = request.session.get('db_ingredients', [])
        temp_ingredients = request.session.get('temp_ingredients', [])
        diet_type = request.session.get('diet_type')

        # Get database ingredients
        db_ingredients_objects = Ingredient.objects.filter(id__in=db_ingredients)

        # Create temporary ingredient objects (without saving to database)
        temp_ingredients_objects = [
            {
                'name': ing['name'],
                'quantity': ing['quantity'],
                'unit': ing['unit']
            }
            for ing in temp_ingredients
        ]

        context = {
            'db_ingredients': db_ingredients_objects,
            'temp_ingredients': temp_ingredients_objects,
            'diet_type': diet_type,
            'servings': servings,
        }
        return render(request, 'recipes/review.html', context)
    return redirect('choose_servings')

client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
@login_required(login_url='/login/')
def generate(request):
    db_ingredients = request.session.get('db_ingredients', [])
    temp_ingredients = request.session.get('temp_ingredients', [])
    diet_type = request.session.get('diet_type')
    servings = request.session.get('servings')

    # Get database ingredients
    db_ingredients_list = Ingredient.objects.filter(id__in=db_ingredients)

    # Prepare ingredient texts for the prompt
    ingredients_text = ", ".join([
        f"{i.quantity} {i.unit} {i.name}" for i in db_ingredients_list
    ] + [
        f"{ing['quantity']} {ing['unit']} {ing['name']}" for ing in temp_ingredients
    ])

    prompt = f"""
        Create a {diet_type} recipe for {servings} people using these main ingredients: {ingredients_text}.
        
        IMPORTANT CONSTRAINTS:
        1. You MUST use ALL the provided ingredients in the recipe
        2. You can ONLY add salt, pepper, water, and oil as additional ingredients
        3. DO NOT add any other ingredients not listed (no vegetables, herbs, or other additions) unless absolutely essential for the recipe
        4. Please ensure all ingredient quantities are specified in decimal format with common kitchen units like cups, teaspoons, and tablespoons where appropriate and avoid using terms like "to taste" or "to preference."
        
        Return a JSON object with the following structure:
        {{
            "title": "Title of the dish",
            "ingredients": [
                {{"name": "ingredient_name", "quantity": "amount", "unit": "unit"}},
                ...
            ],
            "servings": "number of servings",
            "cook_time": "cooking time",
            "instructions": [
                "Step 1: instruction",
                ...
            ]
        }}
    """
    print(prompt)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful chef who creates recipes based on available ingredients."},
                {"role": "user", "content": prompt}
            ]
        )
        response_content = response.choices[0].message.content
        if response_content.startswith('```json'):
            response_content = response_content[7:].strip()  # Remove the leading ```json and any whitespace
        if response_content.endswith('```'):
            response_content = response_content[:-3].strip()  # Remove the trailing ```
        recipe_data = json.loads(response_content)
        print(recipe_data)

        # Create the recipe without adding ingredients to user's owned ingredients
        recipe = Recipe.objects.create(
            user=request.user,
            title=recipe_data["title"],
            cook_time=recipe_data["cook_time"],
            diet_type=diet_type,
            servings=recipe_data["servings"],
            instructions="\n".join(recipe_data.get("instructions", []))
        )

        # Process ingredients specifically for the recipe
        for ing in recipe_data["ingredients"]:
            RecipeIngredient.objects.create(
                recipe=recipe,
                name=ing["name"],
                quantity=convert_to_decimal(ing["quantity"]),
                unit=ing["unit"]
            )

        return render(request, 'recipes/recipe_result.html', {'recipe': recipe})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Failed to decode response'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='/login/')
def recipe_detail(request, recipe_id):
    # Get the recipe by its ID or return 404 if not found
    recipe = get_object_or_404(Recipe, id=recipe_id, user=request.user)

    conversation_key = f"conversation_{recipe_id}"
    conversation = request.session.get(conversation_key, [])

    if not conversation:
        recipe_context = f"Recipe Title: {recipe.title}\nIngredients:\n"
        for ingredient in recipe.recipe_ingredients.all():
            recipe_context += f"- {ingredient.quantity} {ingredient.unit} of {ingredient.name}\n"
        recipe_context += f"Instructions:\n{recipe.instructions}"

        # Add the recipe context as a "system" message
        conversation.append({"role": "system", "content": recipe_context})

    request.session[conversation_key] = conversation
    user_ai_conversation = [
        msg for msg in conversation if msg["role"] != "system"
    ]

    context = {
        'recipe': recipe,
        'conversation': user_ai_conversation,
    }

    return render(request, 'recipes/recipe_detail.html', context)

@login_required(login_url='/login/')
def accept_recipe(request, recipe_id):
    # Get the recipe by its ID or return 404 if not found
    recipe = get_object_or_404(Recipe, id=recipe_id, user=request.user)

    # Update the accepted field to True
    recipe.accepted = True
    recipe.save()

    # Add a success message
    messages.success(request, f"Recipe '{recipe.title}' has been accepted!")

    # Redirect to the recipe's detail page
    return redirect('recipe_detail', recipe_id=recipe.id)


@login_required(login_url='/login/')
def reject_recipe(request, recipe_id):
    # Get the rejected recipe by its ID or return 404 if not found
    recipe = get_object_or_404(Recipe, id=recipe_id, user=request.user)

    # Get ingredients from session
    db_ingredients = request.session.get('db_ingredients', [])
    temp_ingredients = request.session.get('temp_ingredients', [])
    diet_type = request.session.get('diet_type')
    servings = request.session.get('servings')

    # Get database ingredients
    db_ingredients_list = Ingredient.objects.filter(id__in=db_ingredients)

    # Prepare ingredient texts for the prompt
    ingredients_text = ", ".join([
                                     f"{i.quantity} {i.unit} {i.name}" for i in db_ingredients_list
                                 ] + [
                                     f"{ing['quantity']} {ing['unit']} {ing['name']}" for ing in temp_ingredients
                                 ])

    # Get the details of the rejected recipe
    rejected_recipe_title = recipe.title
    rejected_recipe_instructions = recipe.instructions
    rejected_recipe_ingredients = ", ".join([
        f"{ri.quantity} {ri.unit} {ri.name}" for ri in recipe.recipe_ingredients.all()
    ])

    # Create the prompt for GPT, including the rejected recipe context
    prompt = f"""
        You are a talented chef who can create unique recipes based on a set of ingredients. 
        The user has rejected the previous recipe, and they want a new one with the same ingredients.
        Please avoid repeating the same recipe or using similar instructions to the previous one.

        Here is the previously rejected recipe that the user did not like:
        - Title: {rejected_recipe_title}
        - Ingredients: {rejected_recipe_ingredients}
        - Instructions: {rejected_recipe_instructions}

        Now, please create a completely new and different {diet_type} recipe for {servings} people using these ingredients: {ingredients_text}.
        Ensure that the recipe is distinct from the rejected one, provides clear, detailed steps, while ensuring all ingredient quantities are specified in decimal format with common kitchen units like cups, teaspoons, and tablespoons where appropriate and avoid using terms like "to taste" or "to preference."
        The recipe should include:
        - A new title for the dish.
        - A new list of ingredients (use decimal format for quantities).
        - Clear cooking instructions.
        - The number of servings and cook time.

        Return the result in the following JSON format:
        {{
            "title": "New Dish Title",
            "ingredients": [
                {{"name": "ingredient_name", "quantity": "amount", "unit": "unit"}},
                ...
            ],
            "servings": "number of servings",
            "cook_time": "cooking time",
            "instructions": [
                "Step 1: Instruction",
                ...
            ]
        }}
    """
    print(prompt)
    try:
        # Call the GPT API to generate a new recipe
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Make sure to use the correct model
            messages=[
                {"role": "system", "content": "You are a skilled chef who can create unique and creative recipes."},
                {"role": "user", "content": prompt}
            ]
        )

        # Parse the response from GPT
        response_content = response.choices[0].message.content.strip()
        if response_content.startswith('```json'):
            response_content = response_content[7:].strip()  # Remove the leading ```json
        if response_content.endswith('```'):
            response_content = response_content[:-3].strip()  # Remove the trailing ```

        # Try parsing the response as JSON
        recipe_data = json.loads(response_content)

        recipe.delete()

        # Create the new recipe in the database
        new_recipe = Recipe.objects.create(
            user=request.user,
            title=recipe_data["title"],
            cook_time=recipe_data["cook_time"],
            diet_type=diet_type,
            servings=recipe_data["servings"],
            instructions="\n".join(recipe_data.get("instructions", [])),
            accepted=False  # Ensure this recipe is not accepted yet
        )

        # Process ingredients specifically for the new recipe
        for ing in recipe_data["ingredients"]:
            RecipeIngredient.objects.create(
                recipe=new_recipe,
                name=ing["name"],
                quantity=convert_to_decimal(ing["quantity"]),
                unit=ing["unit"]
            )

        # Redirect to the newly created recipe's details page
        messages.success(request, "Recipe rejected. A new recipe has been generated!")
        return render(request, 'recipes/recipe_result.html', {'recipe': new_recipe})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Failed to decode response'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='/login/')
def my_recipes(request):
    # Get all recipes saved by the current user
    recipes = Recipe.objects.filter(user=request.user)
    return render(request, 'recipes/my_recipes.html', {'recipes': recipes})


@login_required(login_url='/login/')
def delete_recipe(request, id):
    if request.method == "POST":
        recipe = get_object_or_404(Recipe, id=id)
        recipe.delete()
        messages.success(request, "Recipe deleted successfully.")
    return redirect('my_recipes')


@login_required(login_url='/login/')
def chatbot(request, recipe_id):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "")

        # Retrieve conversation history for the specific recipe
        conversation_key = f"conversation_{recipe_id}"
        conversation = request.session.get(conversation_key, [])

        # Append the user's message to the conversation history for the specific recipe
        conversation.append({"role": "user", "content": user_message})
        print(conversation)  # Debugging - Optional

        # Send the conversation history to the OpenAI API
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=conversation
            )

            # Get the bot's reply
            bot_reply = response.choices[0].message.content.strip()

            # Append the bot's response to the conversation history
            conversation.append({"role": "assistant", "content": bot_reply})

            # Save the updated conversation history for the recipe back to the session
            request.session[conversation_key] = conversation

            return JsonResponse({"response": bot_reply})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    else:
        return JsonResponse({"error": "Only POST requests are allowed"}, status=400)


@login_required
def clear_conversation(request, recipe_id):
    conversation_key = f"conversation_{recipe_id}"
    if conversation_key in request.session:
        del request.session[conversation_key]

    return redirect('recipe_detail', recipe_id=recipe_id)