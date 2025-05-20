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

test_automation_blueprint=func.Blueprint()


# Classes to define the output format of the Agent as a Pydantic model
class TestCase(BaseModel):  
    title: str  
    steps: List[str]  
    expected_result: str  
    actual_outcome_status: str
    actual_outcome_details: List[str]
  
class TestCasesSummary(BaseModel):  
    test_cases: List[TestCase]  
  
controller = Controller(output_model=TestCasesSummary)


test_case_string = """
    ### TEST CASES:

    #### Positive Test Cases:

    1. **Test Case Name:** Verify Navigation Bar Functionality
    **Description:** Ensure the navigation bar displays all pages and allows users to navigate to them.
    **Steps:**
    - Open the application URL.
    - Verify the navigation bar is visible at the top of the page.
    - Click on each navigation link.
    - Verify the user is redirected to the correct page.
    **Expected Result:** Navigation bar displays all pages, and clicking on each link redirects the user to the correct page.

    2. **Test Case Name:** Verify Bulk Modify Button Functionality
    **Description:** Ensure the 'Bulk Modify' button allows users to change the owner status for multiple rows.
    **Steps:**
    - Open the application URL.
    - Select multiple rows in the table.
    - Click the 'Bulk Modify' button.
    - Change the owner status for the selected rows.
    - Verify the owner status is updated for all selected rows.
    **Expected Result:** The owner status is successfully updated for all selected rows.

    3. **Test Case Name:** Verify Single Row Owner Change
    **Description:** Ensure users can change the owner of a single row by selecting a name in the owner column.
    **Steps:**
    - Open the application URL.
    - Select a single row in the table.
    - Click on the owner column dropdown.
    - Select a new owner name.
    - Verify the owner is updated for the selected row.
    **Expected Result:** The owner is successfully updated for the selected row.

    4. **Test Case Name:** Verify Analyst Assignment
    **Description:** Ensure users can assign an analyst to the work.
    **Steps:**
    - Open the application URL.
    - Select a row in the table.
    - Click on the 'Assign Analyst' button.
    - Select an analyst from the dropdown.
    - Verify the analyst is assigned to the selected work.
    **Expected Result:** The analyst is successfully assigned to the selected work.

    #### Negative Test Cases:

    5. **Test Case Name:** Verify Navigation Bar with Invalid URL
    **Description:** Ensure the navigation bar handles invalid URLs gracefully.
    **Steps:**
    - Open the application URL.
    - Click on a navigation link.
    - Manually modify the URL to an invalid page.
    - Verify the application displays an error message or redirects to a default page.
    **Expected Result:** The application displays an error message or redirects to a default page.

    6. **Test Case Name:** Verify Bulk Modify with No Rows Selected
    **Description:** Ensure the 'Bulk Modify' button does not allow changes when no rows are selected.
    **Steps:**
    - Open the application URL.
    - Click the 'Bulk Modify' button without selecting any rows.
    - Attempt to change the owner status.
    **Expected Result:** The application prevents changes and displays an appropriate error message.

    7. **Test Case Name:** Verify Single Row Owner Change with Invalid Name
    **Description:** Ensure the application handles invalid owner names gracefully.
    **Steps:**
    - Open the application URL.
    - Select a single row in the table.
    - Click on the owner column dropdown.
    - Enter an invalid owner name.
    - Attempt to save the changes.
    **Expected Result:** The application prevents changes and displays an appropriate error message.

    8. **Test Case Name:** Verify Analyst Assignment with No Analyst Selected
    **Description:** Ensure the application prevents assigning work when no analyst is selected.
    **Steps:**
    - Open the application URL.
    - Select a row in the table.
    - Click on the 'Assign Analyst' button.
    - Leave the analyst dropdown empty.
    - Attempt to save the changes.
    **Expected Result:** The application prevents changes and displays an appropriate error message.
"""

  
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


# Function to use GPT and extract relevant sections of test cases from the input string
def parse_test_cases_with_prompt(input_text):
    prompt = f"""
    You are given a set of test cases described in a structured format. Extract each test case's name, description, steps, and expected result.
    Organize them into two categories: Positive Test Cases and Negative Test Cases.
    Format the output in a JSON-like structure for clarity.
    
    Input: {input_text}
    
    Output:
    {{
        "Positive Test Cases": [  
            {{
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


# Function to initialize browser and handle setup
async def initialize_browser():
    try:
        # Specify the path to our Chrome executable
        chrome_path = r'C:\Program Files\Google\Chrome Beta\Application\chrome.exe'
        user_data_dir = r'C:\Users\ak\Downloads\ChromeUserData'
        chrome_debug_port = 9222

        # Connect to our existing Chrome installation and start Chrome in debugging mode  
        subprocess.Popen([chrome_path, f'--remote-debugging-port={chrome_debug_port}', f'--user-data-dir={user_data_dir}'])  
        time.sleep(5)  # Wait for Chrome to start

        try:  
            response = requests.get(f'http://localhost:{chrome_debug_port}/json/version')  
            if response.status_code == 200:  
                print("Chrome is running and accessible.")  
            else:  
                print(f"Unexpected status code: {response.status_code}")  
        except Exception as e:  
            print(f"Failed to connect to Chrome: {e}")
  
    except Exception as e:  
        print(f"Failed to initialize the browser: {e}")

    return chrome_path, chrome_debug_port


# Function for GPT prompt to generate BrowserUse task
async def generate_browseruse_agent_prompt(app_url, login_account, positive_test_cases, negative_test_cases):
    # Define the task for the AI agent for accessing the application
    common_task = f"""  
    1. Access the application using valid credentials.
        - Navigate to the login URL {app_url}.
        - Click 'Log in with SSO'.
        - Select the account {login_account}. 
        - Wait for Authenticator approval (if prompted).
            - If Authentication fails leading to Request being denied, **log an error and stop execution**.
        - Wait for up to 5 seconds for the dashboard to fully load.
    """

    # Define the prompt for the AI agent to generate test cases
    test_case_prompt = f"""
    2. Execute each test case exactly once. No retries or reattempts at all.      
        - Execute **each step in sequence** as defined in the test cases ONLY.  
        
        - Positive Test Cases: {positive_test_cases}  
        - Negative Test Cases: {negative_test_cases}  
    
    3. Check if the actual outcomes match the expected results, indicating successful execution.  
    
    4. If any step of a test case fails, **log an error and mark the test case as failed**.
        - **Move on to the next test case immediately without retrying**.
        - No retries or reattempts should be performed for any test case or step.
    """

    # Combine the login task with the dynamically generated test case prompt
    task = f"""  
    **AI Agent Task: UI Testing Automation**  
    **Objective: Execute defined test cases on the application and summarize the results.**  
    
    ---  

    {common_task}
    {test_case_prompt}
    
    ---  

    5. Strictly adhere to these instructions mentioned below -
  
    **IMPORTANT RULES**    
        
        - Ensure the dashboard actually loads before executing the test cases.  
        - No retries or reattempts should be performed for any test case or step at all.
        - After executing a test case, wait for up to 5 seconds before executing the next test case.
        - Do not take any action unless explicitly instructed. Follow the instructions exactly as written.
        - If a page reloads or changes state briefly, wait and observe unless explicitly told to act.
    
    ---

    **FAIL AND CONTINUE**

        - **DO NOT loop or retry** actions under any circumstance - including page changes, DOM updates, element index changes, or scrolling happens.
        - If messages like "Something new appeared after action", "Element index changed after action", "Scrolled up the page", or "Scrolled down the page" appear:
            - **Immediately stop the current test case**, 
            - **Mark it as FAILED**, 
            - **Move on to the NEXT test case**.
        - Treat any of the above messages as **terminal failures** - do not attempt to recover or proceed within that test case.
        - DO NOT reattempt any step or part of the test case once failed.
    
    ---

    **Handle Unresponsive or Repetitive UI Actions**

        - If a button is clicked, but nothing visibly changes (dialog or modal remains open, no navigation or update occurs):
            - DO NOT retry the click.
            - If a **Cancel, Close, or Exit** button is visible within the dialog or modal, click it once to exit cleanly.
            - After attempting to exit, **mark the test case as FAILED** and **move on to the NEXT test case**.
        - DO NOT perform any additional recovery actions unless explicitly instructed.

    """
    return common_task, task


# Function for GPT prompt to generate Playwright script code for individual test cases (as fallback mechanism)
async def generate_playwright_script(app_url, login_account, login_task, positive_test_cases, negative_test_cases):
    # Example Playwright test case script  
    example_script = """
    @controller.action('Test Case Description.')
    async def example_func(browser: BrowserContext):
        title = "Test Case Title"
        print(f"Executing {title}")

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
    
    Before executing the test cases, perform the following login steps:  
    {login_task}
    
    After successfully logging in, execute the following test cases:
        - Positive Test Cases: {positive_test_cases}  
        - Negative Test Cases: {negative_test_cases}

    Use the following template as a guide for structuring the scripts:  
    {example_script}

    For each test case, generate the corresponding Playwright code snippet.
    Ensure each snippet includes -
    - Actions such as clicking buttons, waiting for elements, and verifying expected outcomes.  
    - Use selectors relevant to the application pages.  
    - Handle exceptions gracefully.
      
    Output the code in a Python format suitable for execution in Playwright's async API.
    Replace placeholders like 'your_actual_selector' with real CSS or XPath selectors.
    """
    
    return generate_gpt_response(prompt)


# Function to integrate BrowserUse and Playwright for browser automation and execute defined test cases
async def execute_test_cases():
    logging.info('Executing test cases.')

    # Accessing environment variables from a .env file
    load_dotenv()
    azure_openai_api_key = os.environ["AZURE_OPENAI_KEY"]  
    azure_openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]  
    azure_openai_api_version = os.environ["AZURE_OPENAI_API_VERSION"]  
    azure_openai_model = os.environ["AZURE_OPENAI_MODEL"]
    app_url = os.environ["APP_URL"]
    login_account = os.environ["LOGIN_ACCOUNT"]

    try:
        # Parse the test cases from the input string  
        test_cases = parse_test_cases_with_prompt(test_case_string)
        positive_test_cases, negative_test_cases = format_test_cases(test_cases)

        # Filter the steps for positive and negative test cases
        filtered_positive_test_cases = filter_test_case_steps(positive_test_cases)  
        filtered_negative_test_cases = filter_test_case_steps(negative_test_cases)
        print(f"Filtered Positive Test Cases: \n{filtered_positive_test_cases}")
        print(f"Filtered Negative Test Cases: \n{filtered_negative_test_cases}")

        # Save the test cases to a text file
        filename = "extraction_results.txt"
        with open(filename, "w") as file:
            file.write("----------------TEST CASES-----------------\n\n")
            file.write(filtered_positive_test_cases + "\n" + filtered_negative_test_cases)
        print(f"Parsed Test Cases saved to {filename}")

        # Generate the BrowserUse task using the parsed test cases
        common_task, browseruse_task = await generate_browseruse_agent_prompt(app_url, login_account, filtered_positive_test_cases, filtered_negative_test_cases)
        
        # Save the BrowserUse task to a text file
        with open(filename, "a") as file:
            file.write("\n\n----------------BROWSERUSE PROMPT-----------------\n")
            file.write(browseruse_task) 
        print(f"BrowserUse task appended to {filename}")  
        
        # Generate Playwright script code using the parsed test cases (as fallback mechanism)
        playwright_scripts = await generate_playwright_script(app_url, login_account, common_task, filtered_positive_test_cases, filtered_negative_test_cases)

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
        
        # Initialize the AzureChatOpenAI language model with the provided credentials
        llm = AzureChatOpenAI(
            model_name=azure_openai_model,
            openai_api_key=azure_openai_api_key,
            azure_endpoint=azure_openai_endpoint,
            deployment_name=azure_openai_model,
            api_version=azure_openai_api_version,
            temperature=0
        )

        try:
            # Initialize browser and handle setup
            chrome_path, chrome_debug_port = await initialize_browser()

            # Connect to the browser
            browser = Browser(
                config=BrowserConfig(
                    chrome_instance_path=chrome_path,
                    remote_debugging_port=chrome_debug_port,
                    headless=False
                )
            )

            # Initialize the BrowserUse Agent with the defined task, language model, browser, and controller
            agent = Agent(
                task=browseruse_task, 
                llm=llm, 
                browser=browser, 
                controller=controller, 
                tool_calling_method="function_calling"
            )

            # Run the agent asynchronously and capture the run  
            print("Starting BrowserUse agent run...")
            history = await agent.run()
            print("BrowserUse agent run completed.") 

            # Save entire history to a file
            history.save_to_file("agentResults.json")

            # Extract and print the final result from the agent's run history
            result = history.final_result()
            if result:  
                # Convert to JSON string if not already  
                if not isinstance(result, str):  
                    result = json.dumps(result)
                    print(f"Result: {result}")

                # Validate and parse the JSON result using Pydantic
                parsed_result: TestCasesSummary = TestCasesSummary.model_validate_json(result)  
                
                report_lines = ["## Test Case Results Summary"]
                # Iterate over each test-case to format and print
                for test_case in parsed_result.test_cases:
                    report_lines.append(f"\n### Test Case Title: {test_case.title}") 
                    report_lines.append("- **Steps Executed:**")  
                    for step in test_case.steps:  
                        report_lines.append(f"  - {step}")  
                    report_lines.append(f"- **Expected Result:** \n  - {test_case.expected_result}")  
                    report_lines.append(f"- **Actual Outcome Status:** \n  - {test_case.actual_outcome_status}")  
                    report_lines.append("- **Actual Outcome Details:**")
                    for detail in test_case.actual_outcome_details:  
                        report_lines.append(f"  - {detail}")
        
                # Print the formatted report  
                print("\n".join(report_lines))
    
                # Save the formatted report to a text file
                filename = "test_case_results.txt"
                with open(f"{filename}", "w") as file:  
                    file.write("\n".join(report_lines))  
                print(f"Results saved to {filename}")
    
            else:  
                print('No results to display. The agent did not produce any output.')

            # Close the browser instance
            await browser.close()
        
        except Exception as e:  
            print(f"Failed to connect to the browser or execute the task: {e}")

        finally:
            if browser:  
                await browser.close()
                logging.info("Browser closed successfully.")
        
    except Exception as e:  
        logging.error(f"An error occurred during test case execution: {e}")
        return func.HttpResponse(  
                "An error occurred during test case execution.",  
                status_code=500  
            )
    
if __name__ == "__main__":
    asyncio.run(execute_test_cases())