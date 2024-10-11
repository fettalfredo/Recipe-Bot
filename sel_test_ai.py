import openai
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")  # Use an environment variable for security

# Get user inputs for search terms
print("Welcome to the Recipe Finder!")
userIngredients = input("Please input some basic ingredients you have for the dish>>> ")
userInput = input("What are we cooking today>>> ")

# Initialize the Chrome driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Pre-prompt for the AI
pre_prompt = (f"You are a chef bot that will be provided recipes from the internet. "
              f"You will first be given some ingredients that the user has on hand. "
              f"Then you will be given a list of ingredients from recipes that were scraped from the internet. "
              f"Your job will be to choose from the list of ingredients from the web the one that best suits the user's current ingredients. "
              f"If the user is missing some ingredients that the recipes required, you will have to provide substitutes to those ingredients. "
              f"Once you have chosen the ingredients you believe best suit the user's current ingredients, "
              f"you will respond with the URL and the substitutes for the missing ingredients all separated by commas. "
              f"You are a chef bot. Do your job properly. "
              f"Here are the ingredients the user has on hand: {userIngredients}. ")

# Open Google
driver.get('https://google.com')

# Find the search input element and enter the search term
inputElement = driver.find_element(By.CLASS_NAME, "gLFyf")
inputElement.clear()
inputElement.send_keys(userInput + Keys.ENTER)

# Wait for the search results to load
time.sleep(2)

# Find all search result elements
webElements = driver.find_elements(By.CSS_SELECTOR, 'h3')

# Initialize a list to store URLs and recipe data
urlList = []
recipeData = {}

def get_openai_response(prompt):
    client = openai.OpenAI()  # Initialize the OpenAI client

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Specify the model
        messages=[
            {"role": "system", "content": pre_prompt},  # Format the system message
            {"role": "user", "content": prompt}  # Format the input message
        ],
        max_tokens=150  # Set maximum tokens for the response
    )
    
    return response.choices[0].message['content']  # Access content using correct format

# Filter search results based on the second user input
for element in webElements:
    if userInput.upper() in element.text.upper():
        parent_link = element.find_element(By.XPATH, './..')
        url = parent_link.get_attribute('href')
        if url and "reddit.com" not in url and "youtube.com" not in url:
            urlList.append(url)

# Visit each URL and collect recipe data
for url in urlList:
    driver.get(url)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    try:
        ingredients = soup.find_all('li', class_='wprm-recipe-ingredient')
        ingredient_text = '\n '.join([ing.get_text() for ing in ingredients])
        
        instructions = soup.find_all('div', class_='wprm-recipe-instruction-text')
        instruction_text = '\n'.join([inst.get_text(strip=True) for inst in instructions])

        if ingredient_text and instruction_text:
            recipeData[url] = {
                'ingredients': ingredient_text,
                'instructions': instruction_text
            }
            
    except Exception as e:  # Catch all exceptions for better error handling
        print(f"Error processing URL {url}: {e}")

# Combine all ingredients from recipes
all_ingredients = [item for sublist in [data["ingredients"].split('\n') for data in recipeData.values()] for item in sublist]
response_text = get_openai_response(f"Here are the ingredients available from different recipes: {', '.join(all_ingredients)}. "
                                     "Which ingredients would you recommend to the user?").strip().split(',')

# Ensure the response is valid
if response_text and response_text[0]:
    best_recipe_url = response_text[0].strip()
    if best_recipe_url in recipeData:  # Check if the URL is in recipeData
        print(f"The best recipe for the ingredients that you currently have is from {best_recipe_url}.\n"
              f"Ingredients: \n  {recipeData[best_recipe_url]['ingredients']}\n"
              f"Instructions: \n  {recipeData[best_recipe_url]['instructions']}")
    else:
        print("The recommended recipe URL is not found in the collected data.")
else:
    print("No suitable recipe found.")

# Wait for user input to close the browser
input("Press Enter To Close The Tab")

# Quit the driver
driver.quit()
