import logging  

import os

import json

import asyncio  

import subprocess  

import requests  

import time

from langchain_openai import AzureChatOpenAI  

from browser_use import Agent, Controller

from browser_use.browser.browser import Browser, BrowserConfig

from browser_use.browser.context import BrowserContext

from browser_use.agent.views import ActionResult

from pydantic import BaseModel

from playwright.async_api import async_playwright

from typing import List

import azure.functions as func

import requests.exceptions

from OpenAI import callGptEndpoint

from dotenv import load_dotenv

 

 

# Function to call GPT for the given prompt  

def generate_gpt_response(prompt):  

    user_message = {  

        "role": "user",  

        "content": prompt  

    }  

 

    messages = [user_message]  

    gpt_options = {

        "engine": os.environ["AZURE_OPENAI_MODEL"],

        "messages": messages,  

        "temperature": 0,  

        "max_tokens": 4096

    }

 

    gpt_response = callGptEndpoint(gpt_options)

 

    if str(gpt_response).startswith("Unexpected"):  

        logging.error("Error occurred while calling GPT endpoint.")  

   

    # Extract the generated content and token usage

    response = gpt_response.choices[0].message.content

    prompt_tokens = gpt_response.usage.prompt_tokens

    completion_tokens = gpt_response.usage.completion_tokens

    total_tokens = gpt_response.usage.total_tokens

    logging.info("GPT response processed successfully.")

 

    return (response, prompt_tokens, completion_tokens, total_tokens)

 

# Function to extract test cases

def extract_test_cases():  

    try:

        filename = "test_cases.txt"

        with open(filename, 'r') as file:  

            content = file.read()  

 

        # Find the start of the test cases section  

        start_index = content.find("### TEST CASES:")  

        end_index = content.find("---", start_index)  

 

        # Extract the test cases section  

        if start_index != -1 and end_index != -1:  

            test_cases_section = content[start_index:end_index].strip()  

            return test_cases_section  

        else:  

            raise ValueError("Test cases section markers not found in the file.")  

     

    except Exception as e:  

        print(f"An error occurred: {e}")  

        return None

 

# Function to use GPT and extract relevant sections of test cases from the input string

def parse_test_cases_with_prompt(input_text):

    prompt = f"""

    You are given a set of test cases described in a structured format. Extract each test case's name, description, steps, and expected result.

    Organize them into two categories: Positive Test Cases and Negative Test Cases.

    Number each test case sequentially across both categories, starting from 1 for Positive Test Cases and continuing for Negative Test Cases.

    Format the output in a JSON-like structure for clarity.

   

    Input: {input_text}

   

    Output:

    {{

        "Positive Test Cases": [  

            {{

                "test": 1,

                "name": "Test Case Name",  

                "description": "Description",  

                "steps": [  

                    "Step 1",  

                    "Step 2",  

                    ...  

                ],  

                "expected_result": "Expected Result"  

            }},  

            ...  

        ],  

        "Negative Test Cases": [  

            {{

                "test": 2,

                "name": "Test Case Name",  

                "description": "Description",  

                "steps": [  

                    "Step 1",  

                    "Step 2",  

                    ...  

                ],  

                "expected_result": "Expected Result"  

            }},  

            ...  

        ]  

    }}

    """

    return generate_gpt_response(prompt)

 

# Function to clean up and extract valid JSON from test cases

def format_test_cases(response_data):

    # Ensure response_data is a string  

    if isinstance(response_data, tuple):

        response_string = response_data[0]  

    else:  

        response_string = response_data

 

    try:

        # Extract the JSON string by finding the first and last braces

        start_index = response_string.find("{")  

        end_index = response_string.rfind("}") + 1

        test_case_string = response_string[start_index:end_index]

       

        # Parse the JSON string into a dictionary

        test_cases_dict = json.loads(test_case_string)

 

        # Separate positive and negative test cases  

        positive_test_cases = test_cases_dict.get("Positive Test Cases", [])  

        negative_test_cases = test_cases_dict.get("Negative Test Cases", [])  

 

        # Convert to pretty-printed JSON strings

        formatted_positive = json.dumps(positive_test_cases, indent=4)  

        formatted_negative = json.dumps(negative_test_cases, indent=4)

       

        return formatted_positive, formatted_negative

    except Exception as e:  

        return f"An error occurred: {e}"

   

 

# Function to filter out unnecessary steps from test cases  

def filter_test_case_steps(test_cases):

    filtered_test_cases = []

 

    # Convert JSON strings to Python lists  

    test_cases_list = json.loads(test_cases)

   

    # Loop through individual test cases to filter out the step "Open the application URL."

    for test_case in test_cases_list:

        # Ensure test_case is treated as a dictionary  

        if isinstance(test_case, dict):  

            # Get the 'steps' list and filter it

            original_steps = test_case.get("steps", [])

            filtered_steps = [step for step in original_steps if step != "Open the application URL."]

            test_case["steps"] = filtered_steps  

            filtered_test_cases.append(test_case)

 

    # Convert to pretty-printed JSON strings

    filtered_test_cases = json.dumps(filtered_test_cases, indent=4)

    return filtered_test_cases

 

# Function to extract and format code blocks from GPT response  

def extract_and_format_code_blocks(response):

    lines = response.split('\n')     # Split the response into lines

    code_blocks = []                 # Empty list to hold code blocks

    in_code_block = False            # Flag to track if we're inside a code block  

    current_code_block = []          # Empty list to hold lines of a current code block  

 

    for line in lines:

        # Skip the markdown code block indicator

        if line.startswith("```python"):  

            in_code_block = True  

            continue

        # Append the current code block to the list

        elif line.startswith("```"):  

            in_code_block = False

            formatted_code_block = '\n'.join(current_code_block)

            code_blocks.append(formatted_code_block)  

            current_code_block = []      # Reset for the next code block

            continue  

 

        if in_code_block:  

            current_code_block.append(line)

   

    # Join individual code blocks with newlines to keep each block distinct

    formatted_code_blocks = '\n\n'.join(code_blocks)

    return formatted_code_blocks

 

# Function for GPT prompt to generate BrowserUse task

async def generate_browseruse_agent_prompt(app_url, login_account, positive_test_cases, negative_test_cases):

    # Define the task for the AI agent for accessing the application

    login_prompt = f"""

    1. Execute the **Login Test Case** to access the application:

        - Open a new tab and Access the application using valid credentials.

        - Navigate to the login URL {app_url}.

        - Click 'Log in with SSO'.

        - Select the account {login_account}.

        - Wait for Authenticator approval (if prompted).

            - If Authentication fails leading to Request being denied, **log an error and stop execution**.

        - Wait for **up to 10 seconds** for the dashboard to fully load before proceeding.

    """

 

    # Define the prompt for the AI agent to generate test cases

    test_case_prompt = f"""

    2. After successfully logging in, execute each test case **only ONCE** in the following order:

 

        - First, execute all the **Positive Test Cases** in sequence:

        {positive_test_cases}

 

        - Then, execute all the **Negative Test Cases** in sequence:

        {negative_test_cases}

   

    3. After executing a test case ONCE, whether it fails or passes:

        - **ALWAYS navigate back to the original dashboard or Home page** before executing the next test case.

   

    4. Execute each test case **exactly once**. Do not retry or reattempt any test case or step under any circumstances.

   

    5. If a test case fails at any step:

        - **Immediately stop the current test case**,

        - **Mark it as FAILED**,

        - **Move on to the NEXT test case** immediately without retrying.

   

    6. Check if the actual outcomes match the expected results, indicating successful execution.

 

    7. After executing all Positive and Negative test cases ONCE:

        - **Stop execution completely**.

        - Summarize the results of all test cases, including their status (Passed/Failed) and details of any failures.

    """

 

    # Combine the login task with the dynamically generated test case prompt

    common_task = f"""  

    **AI Agent Task: UI Testing Automation**  

    **Objective: Execute defined test cases on the application and summarize the results.**

   

    ---  

 

    {login_prompt}

    {test_case_prompt}

   

    ---

 

    **IMPORTANT RULES**    

       

        - Ensure the dashboard actually loads before executing the test cases.

 

        - After executing a test case:

            - **ALWAYS navigate back to the main dashboard or Home page** before starting the next test case. This is mandatory - test execution will fail otherwise.

       

        - **DO NOT retry or reattempt** any test case or step under any circumstances.

        - **DO NOT loop or retry** actions under any circumstance - including page changes, DOM updates, element index changes, or scrolling.

 

        - DO NOT take any action unless explicitly instructed. Follow the instructions exactly as written.

 

    ---

 

    **FAIL AND CONTINUE**

 

        - If messages like "Something new appeared after action", "Element index changed after action", "Scrolled up the page", or "Scrolled down the page" appear:

            - **Immediately stop the current test case**,

            - **Mark it as FAILED**,

            - **Move on to the NEXT test case**.

        - Treat any of the above messages as **terminal failures** - do not attempt to recover or proceed within that test case.

       

        - If a button is clicked, but nothing visibly changes (dialog or modal remains open, no navigation or update occurs):

            - **Click a Cancel, Close, or Exit button** once if visible within the dialog or modal to exit cleanly.

            - **Immediately mark the test case as FAILED** and **move on to the NEXT test case**.

            - **DO NOT retry the original button**, even if it remains on screen.

        - Treat the persistent presence of the same dialog or modal after the button click as **terminal failure**.

 

        - DO NOT reattempt any step or part of the test case once failed.

    ---

    """

    return login_prompt, test_case_prompt, common_task

 

# Function for GPT prompt to generate Playwright script code for individual test cases (as fallback mechanism)

async def generate_playwright_scripts(login_test_case, positive_test_cases, negative_test_cases):

    # Example Playwright test case script  

    example_script = """

    @controller.action('Test Case Description.')

    async def example_func(browser: BrowserContext):

        title = "Test Case Title"

        print(f"Fallback mechanism invoked for {title} task.")   # Ensure this line is part of the script  

        print(f"Executing {title} task.")                        # Ensure this line is part of the script

 

        page = await browser.get_current_page()

        actual_outcome_details = []

 

        # Insert actions and logic here in proper try-except blocks

        # Example: await page.click('selector')  

        # Example: is_visible = await page.is_visible('selector')  

 

        # Determine the actual outcome status based on actions and validations  

        actual_outcome_status = "Passed" if <condition> else "Failed"

 

        return ActionResult(

            extracted_content=f"Title: {title} \nActual outcome status: {actual_outcome_status} \nActual outcome details: {actual_outcome_details}",

            include_in_memory=True

        )

    """

 

    # Define the prompt for the AI agent to generate Playwright script

    prompt = f"""

    Based on the following structured test cases, generate Playwright automation scripts.

   

    First, execute the login test case to access the application:  

    {login_test_case}

   

    After successfully logging in, execute the following test cases:

        - Positive Test Cases: {positive_test_cases}  

        - Negative Test Cases: {negative_test_cases}

 

    After executing a test case, always navigate back to the Home page before executing the next test case.

   

    Use the following template as a guide for structuring the scripts:  

    {example_script}

 

    For each test case (login + positive + negative), generate the corresponding Playwright code snippet.

    Ensure each snippet includes -

    - Actions such as clicking buttons, waiting for elements, and verifying expected outcomes.  

    - Use selectors relevant to the application pages.  

    - Handle exceptions gracefully.

     

    Output the code in a Python format suitable for execution in Playwright's async API.

    Replace placeholders like 'your_actual_selector' with real CSS or XPath selectors.

    """

   

    return generate_gpt_response(prompt)

 

# Main function

async def automation_scripts_generation():

    logging.info('Generating test scripts.')

 

    # Accessing environment variables from a .env file

    load_dotenv()

    azure_openai_api_key = os.environ["AZURE_OPENAI_KEY"]  

    azure_openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]  

    azure_openai_api_version = os.environ["AZURE_OPENAI_API_VERSION"]  

    azure_openai_model = os.environ["AZURE_OPENAI_MODEL"]

    app_url = os.environ["APP_URL"]

    login_account = os.environ["LOGIN_ACCOUNT"]

 

    try:

        # Read the test cases from the file

        test_case_string = extract_test_cases()

 

        # Parse the test cases from the input string  

        test_cases = parse_test_cases_with_prompt(test_case_string)

        positive_test_cases, negative_test_cases = format_test_cases(test_cases)

 

        # Filter the steps for positive and negative test cases

        filtered_positive_test_cases = filter_test_case_steps(positive_test_cases)  

        filtered_negative_test_cases = filter_test_case_steps(negative_test_cases)

        print(f"Filtered Positive Test Cases: \n{filtered_positive_test_cases}")

        print(f"Filtered Negative Test Cases: \n{filtered_negative_test_cases}")

 

        # Generate the BrowserUse task using the parsed test cases

        login_task, test_case_task, browseruse_task = await generate_browseruse_agent_prompt(app_url, login_account, filtered_positive_test_cases, filtered_negative_test_cases)

       

        # Save the BrowserUse task to a text file

        filename = "extraction_results.txt"

        with open(filename, "w") as file:

            file.write("----------------BROWSERUSE PROMPT-----------------\n")

            file.write(browseruse_task)

        print(f"BrowserUse task appended to {filename}")  

       

        # Generate Playwright script code using the parsed test cases (as fallback mechanism)

        playwright_scripts = await generate_playwright_scripts(login_task, filtered_positive_test_cases, filtered_negative_test_cases)

 

        # Extract and format Playwright automation script code blocks from GPT response

        if isinstance(playwright_scripts, tuple):  

            playwright_scripts = playwright_scripts[0]

        playwright_script_code_blocks = extract_and_format_code_blocks(playwright_scripts)

        print(f"Playwright Automation scripts: \n\n{playwright_script_code_blocks}")

       

        # Save the playwright scripts to a text file

        with open(filename, "a") as file:

            file.write("\n\n----------------PLAYWRIGHT AUTOMATION SCRIPTS-----------------\n\n")

            file.write(playwright_script_code_blocks)

        print(f"Playwright Automation scripts appended to {filename}")

 

    except Exception as e:  

        logging.error(f"An error occurred during test scripts generation: {e}")

        return func.HttpResponse(  

                "An error occurred during test scripts generation.",  

                status_code=500  

            )

 

if __name__ == "__main__":  

    asyncio.run(automation_scripts_generation())