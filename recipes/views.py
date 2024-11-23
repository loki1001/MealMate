# views.py
import json
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from openai import OpenAIError
from .models import Ingredient, Recipe, RecipeIngredient
import openai
from django.contrib.auth import login, authenticate
from .forms import SignUpForm
from fractions import Fraction

# Function to convert a quantity to decimal format
def convert_to_decimal(quantity):
    try:
        # Convert the quantity to a decimal number
        return str(float(Fraction(quantity)))
    except ValueError:
        # Return the original value if conversion fails
        return quantity

# Home view that renders the homepage
def home(request):
    return render(request, 'recipes/home.html')

# Signup view to handle user registration
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

# View for displaying and managing the user's ingredients
@login_required(login_url='/login/')
def my_items(request):
    if request.method == 'POST':
        # Retrieve ingredient data from the form submission
        name = request.POST.get('name')
        quantity = request.POST.get('quantity')
        unit = request.POST.get('unit')
        # Create a new ingredient for the logged-in user
        Ingredient.objects.create(
            user=request.user,
            name=name,
            quantity=quantity,
            unit=unit
        )
        return redirect('my_items')

    # Retrieve the ingredients for the logged-in user
    ingredients = Ingredient.objects.filter(user=request.user)
    return render(request, 'recipes/my_items.html', {'ingredients': ingredients})

# View to delete an ingredient from the user's list
@login_required(login_url='/login/')
def delete_ingredient(request, ingredient_id):
    try:
        # Attempt to retrieve the ingredient to delete
        ingredient = Ingredient.objects.get(id=ingredient_id, user=request.user)
        ingredient.delete()
        messages.success(request, 'Ingredient deleted successfully.')
    except Ingredient.DoesNotExist:
        messages.error(request, 'Ingredient not found.')
    return redirect('my_items')

# View to render the page where the user generates a recipe
@login_required(login_url='/login/')
def generate_recipe(request):
    # Retrieve the user's ingredients for recipe generation
    ingredients = Ingredient.objects.filter(user=request.user)
    return render(request, 'recipes/generate_recipe.html', {'ingredients': ingredients})

# View to handle diet selection and store ingredients in the session
@login_required(login_url='/login/')
def choose_diet(request):
    if request.method == 'POST':
        # Get database ingredients (IDs) from the form submission
        db_ingredients = request.POST.get('db_ingredients', '').split(',')
        db_ingredients = [id for id in db_ingredients if id]

        # Get temporary ingredients from the form submission
        temp_ingredients_json = request.POST.get('temp_ingredients', '[]')
        try:
            # Try to parse the temporary ingredients JSON data
            temp_ingredients = json.loads(temp_ingredients_json)

            # Store both database and temporary ingredients in the session
            request.session['db_ingredients'] = db_ingredients
            request.session['temp_ingredients'] = temp_ingredients

            return render(request, 'recipes/choose_diet.html')
        except json.JSONDecodeError:
            messages.error(request, 'Error processing ingredients')
            return redirect('generate_recipe')
    return redirect('generate_recipe')

# View to handle serving size selection
@login_required(login_url='/login/')
def choose_servings(request):
    if request.method == 'POST':
        # Get the diet type and store it in the session
        diet_type = request.POST.get('diet_type')
        request.session['diet_type'] = diet_type
        return render(request, 'recipes/choose_servings.html')
    return redirect('choose_diet')

# View to review the recipe before finalizing
@login_required(login_url='/login/')
def review(request):
    if request.method == 'POST':
        servings = request.POST.get('servings')
        request.session['servings'] = servings

        # Retrieve both types of ingredients from the session
        db_ingredients = request.session.get('db_ingredients', [])
        temp_ingredients = request.session.get('temp_ingredients', [])
        diet_type = request.session.get('diet_type')

        # Retrieve database ingredients based on their IDs
        db_ingredients_objects = Ingredient.objects.filter(id__in=db_ingredients)

        # Create temporary ingredient objects (without saving them to the database)
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


# Initialize OpenAI client using API key from settings
client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)


# Ensure the user is logged in before accessing this view
@login_required(login_url='/login/')
def generate(request):
    # Fetch ingredients stored in session variables
    db_ingredients = request.session.get('db_ingredients', [])
    temp_ingredients = request.session.get('temp_ingredients', [])
    diet_type = request.session.get('diet_type')
    servings = request.session.get('servings')

    # Retrieve ingredients from the database using the IDs stored in session
    db_ingredients_list = Ingredient.objects.filter(id__in=db_ingredients)

    # Prepare the list of ingredients to be used in the prompt by combining
    # both database ingredients and temporary ingredients
    ingredients_text = ", ".join([
                                     f"{i.quantity} {i.unit} {i.name}" for i in db_ingredients_list
                                 ] + [
                                     f"{ing['quantity']} {ing['unit']} {ing['name']}" for ing in temp_ingredients
                                 ])

    # Construct the prompt that will be sent to OpenAI to generate a recipe
    prompt = f"""
        Create a {diet_type} recipe for {servings} people using these main ingredients: {ingredients_text}.

        IMPORTANT CONSTRAINTS:
        1. You MUST use ONLY the provided ingredients in the recipe
        2. You can omit some of the ingredients if they are not crucial to the recipe
        3. You can ONLY add salt, pepper, water, and oil as additional ingredients
        4. DO NOT add any other ingredients not listed (no vegetables, herbs, or other additions) unless absolutely essential for the recipe
        5. Please ensure all ingredient quantities are specified in decimal format with common kitchen units like cups, teaspoons, and tablespoons where appropriate and avoid using terms like "to taste" or "to preference."

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

    # Print the generated prompt for debugging purposes
    print(prompt)

    try:
        # Send the prompt to OpenAI to generate a recipe
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use GPT model for generating the recipe
            messages=[
                {"role": "system",
                 "content": "You are a helpful chef who creates recipes based on available ingredients."},
                {"role": "user", "content": prompt}
            ]
        )

        # Extract and clean up the response content from OpenAI
        response_content = response.choices[0].message.content
        if response_content.startswith('```json'):
            response_content = response_content[7:].strip()  # Remove the leading ```json and any whitespace
        if response_content.endswith('```'):
            response_content = response_content[:-3].strip()  # Remove the trailing ```

        # Parse the response content as a JSON object
        recipe_data = json.loads(response_content)
        print(recipe_data)

        # Create a new Recipe object in the database using the generated data
        recipe = Recipe.objects.create(
            user=request.user,
            title=recipe_data["title"],
            cook_time=recipe_data["cook_time"],
            diet_type=diet_type,
            servings=recipe_data["servings"],
            instructions="\n".join(recipe_data.get("instructions", []))
        )

        # Process the ingredients for the new recipe and store them in the database
        for ing in recipe_data["ingredients"]:
            RecipeIngredient.objects.create(
                recipe=recipe,
                name=ing["name"],
                quantity=convert_to_decimal(ing["quantity"]),  # Convert quantity to decimal format
                unit=ing["unit"]
            )

        # Render the recipe result page with the newly created recipe
        return render(request, 'recipes/recipe_result.html', {'recipe': recipe})

    # Handle errors related to invalid JSON format in the response
    except json.JSONDecodeError:
        error_context = {
            'error_title': 'Invalid Recipe Format',
            'error_message': 'We had trouble formatting your recipe. Please try again.',
            'suggestions': [
                'Try using fewer ingredients',
                'Make sure all ingredients have proper measurements',
                'Check if your dietary preferences work with these ingredients'
            ]
        }
        return render(request, 'recipes/error.html', error_context)

    # Handle errors when the OpenAI service is unavailable
    except OpenAIError as e:
        error_context = {
            'error_title': 'Service Temporarily Unavailable',
            'error_message': 'We\'re having trouble connecting to our recipe service.',
            'suggestions': [
                'Please wait a few moments and try again',
                'Check your internet connection',
                'If the problem persists, try starting over'
            ]
        }
        return render(request, 'recipes/error.html', error_context)

    # Handle other unexpected errors
    except Exception as e:
        error_context = {
            'error_title': 'Unexpected Error',
            'error_message': 'Something went wrong while generating your recipe.',
            'suggestions': [
                'Try again with different ingredients',
                'Make sure all inputs are valid',
                'If the problem continues, please contact support'
            ]
        }
        return render(request, 'recipes/error.html', error_context)


# Ensure the user is logged in before accessing this view
@login_required(login_url='/login/')
def recipe_detail(request, recipe_id):
    # Fetch the recipe by its ID or return a 404 error if not found
    recipe = get_object_or_404(Recipe, id=recipe_id, user=request.user)

    # Define a unique key for the conversation associated with the recipe
    conversation_key = f"conversation_{recipe_id}"
    # Retrieve any existing conversation stored in the session, or initialize an empty list
    conversation = request.session.get(conversation_key, [])

    # If no conversation exists, create a new one
    if not conversation:
        # Start by constructing the recipe context as a string
        recipe_context = f"Recipe Title: {recipe.title}\nIngredients:\n"
        for ingredient in recipe.recipe_ingredients.all():
            # Add each ingredient to the recipe context
            recipe_context += f"- {ingredient.quantity} {ingredient.unit} of {ingredient.name}\n"
        recipe_context += f"Instructions:\n{recipe.instructions}"

        # Add the recipe context as a "system" message to the conversation
        conversation.append({"role": "system", "content": recipe_context})

    # Store the updated conversation in the session
    request.session[conversation_key] = conversation
    # Extract only the user messages from the conversation, excluding the system message
    user_ai_conversation = [
        msg for msg in conversation if msg["role"] != "system"
    ]

    # Pass the recipe and the user's AI conversation to the template context
    context = {
        'recipe': recipe,
        'conversation': user_ai_conversation,
    }

    # Render the recipe detail page with the recipe and conversation data
    return render(request, 'recipes/recipe_detail.html', context)


# Ensure the user is logged in before accessing this view
@login_required(login_url='/login/')
def accept_recipe(request, recipe_id):
    # Fetch the recipe by its ID or return a 404 error if not found
    recipe = get_object_or_404(Recipe, id=recipe_id, user=request.user)

    # Update the 'accepted' field of the recipe to True
    recipe.accepted = True
    recipe.save()

    # Add a success message indicating the recipe has been accepted
    messages.success(request, f"Recipe '{recipe.title}' has been accepted!")

    # Redirect the user to the recipe's detail page
    return redirect('recipe_detail', recipe_id=recipe.id)


# Ensure the user is logged in before accessing this view
@login_required(login_url='/login/')
def reject_recipe(request, recipe_id):
    # Fetch the rejected recipe by its ID or return a 404 error if not found
    recipe = get_object_or_404(Recipe, id=recipe_id, user=request.user)

    # Retrieve the ingredients and other session data
    db_ingredients = request.session.get('db_ingredients', [])  # List of database ingredient IDs
    temp_ingredients = request.session.get('temp_ingredients', [])  # List of temporary ingredients
    diet_type = request.session.get('diet_type')  # Diet type selected by the user (e.g., vegan, gluten-free)
    servings = request.session.get('servings')  # Number of servings requested by the user

    # Retrieve the actual database ingredients using the IDs stored in the session
    db_ingredients_list = Ingredient.objects.filter(id__in=db_ingredients)

    # Prepare a string with ingredient details for the prompt, combining database and temporary ingredients
    ingredients_text = ", ".join([
                                     f"{i.quantity} {i.unit} {i.name}" for i in db_ingredients_list
                                 ] + [
                                     f"{ing['quantity']} {ing['unit']} {ing['name']}" for ing in temp_ingredients
                                 ])

    # Get the details of the recipe being rejected
    rejected_recipe_title = recipe.title
    rejected_recipe_instructions = recipe.instructions
    rejected_recipe_ingredients = ", ".join([
        f"{ri.quantity} {ri.unit} {ri.name}" for ri in recipe.recipe_ingredients.all()
    ])

    # Construct the prompt for GPT to generate a new recipe using the same ingredients but different instructions
    prompt = f"""
        The user has rejected the previous recipe, and they want a new one with the same ingredients.
        Please avoid repeating the same recipe or using similar instructions to the previous one.

        Here is the previously rejected recipe that the user did not like:
        - Title: {rejected_recipe_title}
        - Ingredients: {rejected_recipe_ingredients}
        - Instructions: {rejected_recipe_instructions}

        Now, please create a completely new and different {diet_type} recipe for {servings} people using these ingredients: {ingredients_text}.

        IMPORTANT CONSTRAINTS:
        1. You MUST use ONLY the provided ingredients in the recipe
        2. You can omit some of the ingredients if they are not crucial to the recipe
        3. You can ONLY add salt, pepper, water, and oil as additional ingredients
        4. DO NOT add any other ingredients not listed (no vegetables, herbs, or other additions) unless absolutely essential for the recipe
        5. Please ensure all ingredient quantities are specified in decimal format with common kitchen units like cups, teaspoons, and tablespoons where appropriate and avoid using terms like "to taste" or "to preference."
        6. The new recipe must be significantly different from the rejected recipe in terms of preparation method and final dish.

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
        # Call the GPT API to generate a new recipe based on the provided prompt
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a skilled chef who can create unique and creative recipes."},
                {"role": "user", "content": prompt}
            ]
        )

        # Process the response from GPT
        response_content = response.choices[0].message.content.strip()

        # Clean up the response content by removing any code block markers (if any)
        if response_content.startswith('```json'):
            response_content = response_content[7:].strip()  # Remove the leading ```json
        if response_content.endswith('```'):
            response_content = response_content[:-3].strip()  # Remove the trailing ```

        # Attempt to parse the cleaned response as JSON
        recipe_data = json.loads(response_content)

        # Delete the rejected recipe from the database
        recipe.delete()

        # Create the new recipe in the database with the generated data
        new_recipe = Recipe.objects.create(
            user=request.user,
            title=recipe_data["title"],
            cook_time=recipe_data["cook_time"],
            diet_type=diet_type,
            servings=recipe_data["servings"],
            instructions="\n".join(recipe_data.get("instructions", [])),
            accepted=False  # Ensure this recipe is not accepted yet
        )

        # Process the ingredients for the new recipe and save them to the database
        for ing in recipe_data["ingredients"]:
            RecipeIngredient.objects.create(
                recipe=new_recipe,
                name=ing["name"],
                quantity=convert_to_decimal(ing["quantity"]),
                unit=ing["unit"]
            )

        # Redirect to the newly created recipe's detail page and display a success message
        messages.success(request, "Recipe rejected. A new recipe has been generated!")
        return render(request, 'recipes/recipe_result.html', {'recipe': new_recipe})
    except json.JSONDecodeError:
        # Handle the case where the response could not be parsed as valid JSON
        error_context = {
            'error_title': 'Invalid Recipe Format',
            'error_message': 'We had trouble formatting your recipe. Please try again.',
            'suggestions': [
                'Try using fewer ingredients',
                'Make sure all ingredients have proper measurements',
                'Check if your dietary preferences work with these ingredients'
            ]
        }
        return render(request, 'recipes/error.html', error_context)
    except OpenAIError as e:
        # Handle errors from the GPT API (e.g., service unavailable)
        error_context = {
            'error_title': 'Service Temporarily Unavailable',
            'error_message': 'We\'re having trouble connecting to our recipe service.',
            'suggestions': [
                'Please wait a few moments and try again',
                'Check your internet connection',
                'If the problem persists, try starting over'
            ]
        }
        return render(request, 'recipes/error.html', error_context)
    except Exception as e:
        # Handle unexpected errors
        error_context = {
            'error_title': 'Unexpected Error',
            'error_message': 'Something went wrong while generating your recipe.',
            'suggestions': [
                'Try again with different ingredients',
                'Make sure all inputs are valid',
                'If the problem continues, please contact support'
            ]
        }
        return render(request, 'recipes/error.html', error_context)


@login_required(login_url='/login/')
def my_recipes(request):
    # Fetch all recipes saved by the current user from the Recipe model
    recipes = Recipe.objects.filter(user=request.user)

    # Render the 'my_recipes.html' template and pass the retrieved recipes as context
    return render(request, 'recipes/my_recipes.html', {'recipes': recipes})


@login_required(login_url='/login/')
def delete_recipe(request, id):
    # Handle the POST request to delete a recipe
    if request.method == "POST":
        # Retrieve the recipe by its ID or return a 404 if not found
        recipe = get_object_or_404(Recipe, id=id)

        # Delete the recipe
        recipe.delete()

        # Display a success message after deletion
        messages.success(request, "Recipe deleted successfully.")

    # Redirect back to the user's recipe list page
    return redirect('my_recipes')


@login_required(login_url='/login/')
def chatbot(request, recipe_id):
    # Handle the POST request for the chatbot interaction
    if request.method == "POST":
        # Parse the incoming JSON data and retrieve the user's message
        data = json.loads(request.body)
        user_message = data.get("message", "")

        # Define a unique conversation key for this recipe
        conversation_key = f"conversation_{recipe_id}"

        # Retrieve the conversation history for the specific recipe from the session
        conversation = request.session.get(conversation_key, [])

        # Append the user's message to the conversation history
        conversation.append({"role": "user", "content": user_message})
        print(conversation)  # Debugging - Optional

        # Send the conversation history to the OpenAI API for a response
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Use the specified model
                messages=conversation  # Send the conversation as context
            )

            # Extract the bot's reply from the response
            bot_reply = response.choices[0].message.content.strip()

            # Append the bot's response to the conversation history
            conversation.append({"role": "assistant", "content": bot_reply})

            # Save the updated conversation history back to the session
            request.session[conversation_key] = conversation

            # Return the bot's response as a JSON response
            return JsonResponse({"response": bot_reply})

        # Handle exceptions during the API call
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    # Return an error response for non-POST requests
    else:
        return JsonResponse({"error": "Only POST requests are allowed"}, status=400)


@login_required
def clear_conversation(request, recipe_id):
    # Generate a unique session key for the conversation related to the recipe
    conversation_key = f"conversation_{recipe_id}"

    # Check if the conversation exists in the session and delete it if found
    if conversation_key in request.session:
        del request.session[conversation_key]

    # Redirect to the recipe details page for the given recipe_id
    return redirect('recipe_detail', recipe_id=recipe_id)


@login_required(login_url='/login/')
def generate_flexible(request):
    # Retrieve the ingredients, diet type, and servings from the session
    db_ingredients = request.session.get('db_ingredients', [])
    temp_ingredients = request.session.get('temp_ingredients', [])
    diet_type = request.session.get('diet_type')
    servings = request.session.get('servings')

    # Get the ingredient objects from the database based on the selected ids
    db_ingredients_list = Ingredient.objects.filter(id__in=db_ingredients)

    # Prepare a string representation of all ingredients to use in the recipe prompt
    ingredients_text = ", ".join([
                                     f"{i.quantity} {i.unit} {i.name}" for i in db_ingredients_list
                                 ] + [
                                     f"{ing['quantity']} {ing['unit']} {ing['name']}" for ing in temp_ingredients
                                 ])

    # Construct the prompt for the AI to generate a recipe based on the provided ingredients and guidelines
    prompt = f"""
        Create a {diet_type} recipe for {servings} people incorporating these ingredients: {ingredients_text}.

        Guidelines:
        1. Try to use as many of the provided ingredients as possible
        2. You can add common ingredients and seasonings to create a complete recipe
        3. Please ensure all ingredient quantities are specified in decimal format with common kitchen units like cups, teaspoons, and tablespoons where appropriate and avoid using terms like "to taste" or "to preference."
        4. Any additional ingredients should enhance the recipe while keeping the provided ingredients as the main components

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
    print(prompt)  # Debugging - Optional

    try:
        # Call the OpenAI API to generate a recipe based on the prompt and ingredients
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Specify the model to use
            messages=[
                {"role": "system",
                 "content": "You are a creative chef who creates delicious recipes incorporating available ingredients while adding complementary ingredients when needed."},
                {"role": "user", "content": prompt}  # User's recipe prompt
            ]
        )

        # Extract the content of the response
        response_content = response.choices[0].message.content
        # Clean up the response to remove any markdown formatting (if present)
        if response_content.startswith('```json'):
            response_content = response_content[7:].strip()
        if response_content.endswith('```'):
            response_content = response_content[:-3].strip()

        # Parse the response content as JSON to extract the recipe data
        recipe_data = json.loads(response_content)

        # Create a new recipe object in the database using the data from the AI response
        recipe = Recipe.objects.create(
            user=request.user,
            title=recipe_data["title"],
            cook_time=recipe_data["cook_time"],
            diet_type=diet_type,
            servings=recipe_data["servings"],
            instructions="\n".join(recipe_data.get("instructions", [])),
        )

        # Add each ingredient from the AI-generated recipe to the database
        for ing in recipe_data["ingredients"]:
            RecipeIngredient.objects.create(
                recipe=recipe,
                name=ing["name"],
                quantity=convert_to_decimal(ing["quantity"]),  # Convert quantity to decimal format
                unit=ing["unit"]
            )

        # Render the 'recipe_result.html' template with the newly created recipe
        return render(request, 'recipes/recipe_result.html', {'recipe': recipe})

    # Handle specific exceptions for JSON formatting issues
    except json.JSONDecodeError:
        error_context = {
            'error_title': 'Invalid Recipe Format',
            'error_message': 'We had trouble formatting your recipe. Please try again.',
            'suggestions': [
                'Try using fewer ingredients',
                'Make sure all ingredients have proper measurements',
                'Check if your dietary preferences work with these ingredients'
            ]
        }
        # Render an error page with the appropriate error message and suggestions
        return render(request, 'recipes/error.html', error_context)

    # Handle OpenAI API connection errors
    except OpenAIError as e:
        error_context = {
            'error_title': 'Service Temporarily Unavailable',
            'error_message': 'We\'re having trouble connecting to our recipe service.',
            'suggestions': [
                'Please wait a few moments and try again',
                'Check your internet connection',
                'If the problem persists, try starting over'
            ]
        }
        # Render an error page with the appropriate error message and suggestions
        return render(request, 'recipes/error.html', error_context)

    # Handle any other unexpected errors
    except Exception as e:
        error_context = {
            'error_title': 'Unexpected Error',
            'error_message': 'Something went wrong while generating your recipe.',
            'suggestions': [
                'Try again with different ingredients',
                'Make sure all inputs are valid',
                'If the problem continues, please contact support'
            ]
        }
        # Render an error page with the appropriate error message and suggestions
        return render(request, 'recipes/error.html', error_context)
