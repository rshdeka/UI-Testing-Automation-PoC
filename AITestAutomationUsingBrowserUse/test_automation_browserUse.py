import os  
import asyncio  
import subprocess  
import requests  
import time  
import json  
from langchain_openai import AzureChatOpenAI  
from browser_use import Agent, Controller
from browser_use.browser.browser import Browser, BrowserConfig
from pydantic import BaseModel
from typing import List  
from dotenv import load_dotenv  
  

# Accessing environment variables from a .env file
load_dotenv()
azure_openai_api_key = os.environ["AZURE_OPENAI_KEY"]  
azure_openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]  
azure_openai_api_version = os.environ["AZURE_OPENAI_API_VERSION"]  
azure_openai_model = os.environ["AZURE_OPENAI_MODEL"]
app_url = os.environ["APP_URL"]
login_account = os.environ["LOGIN_ACCOUNT"]
chrome_path = os.environ["CHROME_EXECUTABLE_PATH"]
user_data_dir = os.environ["CHROME_USER_DATA_DIRECTORY"]

 
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


# Function to initialize BrowserUse Agent for browser automation and execute defined test cases
async def executeTestCases():
    # Define the prompt/task for the AI agent  
    task = f"""  
    **AI Agent Task: UI Testing Automation**  
    **Objective: Execute defined test cases on the application and summarize the results.**
 
    ---

    1. Automate browser interactions for each test case.
        - Ensure tests validate the UI functionalities as described.
    
    2. Execute each test case EXACTLY ONCE. No retries or reattempts at all.
        - Execute **each step in sequence** as defined in the test cases only.
        - Do not skip or infer steps. 
        - **Do not mark a test case as failed or passed** until all steps in that test case has been completed in proper sequence.
        
    3. After executing a test case ONCE, whether it fails or passes:
        - **ALWAYS navigate back to the original dashboard or Home page** before executing the next test case.
    
    4. If a test case fails at any step:
        - **Immediately stop the current test case**, 
        - **Mark it as FAILED**, 
        - **Move on to the NEXT test case** immediately without retrying.

    5. Check if the actual outcomes match the expected results, indicating successful execution.

    ---

    6. Access the application using valid credentials.
        - Navigate to the login URL {app_url}.
        - Click 'Log in with SSO'.
        - Select the account {login_account}. 
        - Wait for Authenticator approval (if prompted).
            - If Authentication fails leading to Request being denied, **log an error and stop execution**.
        - Wait for **up to 10 seconds** for the dashboard to fully load before proceeding.

    7. After successfully logging in, execute each test case **only ONCE** in the following order:
        - Execute **each step in sequence** as defined in the test cases ONLY.

        **Test Case 1**
            {{
                "name": "Navigation Display Test",
                "description": "Verify that the site navigation at the top of the page displays all pages in the application.",  
                "steps": [
                    "- Observe the navigation bar at the top of the page."  
                ],  
                "expected_result": "All pages in the application are listed in the navigation bar."  
            }}

        **Test Case 2**
            {{
                "name": "Single Row Owner Change Test",
                "description": "Verify that the user can change the owner of a single row by selecting a name in the owner column.",
                "steps": [
                    "- Locate a single row in the queue where the 'Plan' column value starts with 'CO000'.",
                    "- Within that row, find and click the checkbox element whose 'div id' starts with '#queue-checkbox'. Do not use element index-based selectors.",
                    "- Within that row, find and click the 'Owner' column element whose 'div id' starts with '#queue-table-cell-owner'. Do not use element index-based selectors.",
                    "- Wait for the dropdown options to appear.",
                    "- Locate all <li> elements whose 'li id' starts with '#queue-dropdown-item'.",
                    "- From the dropdown options, select and click one of the owner names from <li> elements by visible text. Do not use 'select_dropdown_option' as the dropdown is a custom element, not a <select>.",
                    "- Wait for up to 3 seconds for the dropdown to close and the new owner name to be visible in the owner column.",
                    "- Confirm the selected owner name is now visible in the owner column for the same row."
                ],
                "expected_result": "The owner of the selected row is updated in the dashboard."
            }}

        **Test Case 3**
            {{
                "name": "Bulk Modify Owner Status Test",  
                "description": "Verify that the user can bulk change the owner status using the 'Bulk modify' button.",  
                "steps": [
                    "- Locate multiple rows in the queue where the 'Plan' column values starts with 'CO000'.",
                    "- For each such row, find and click the checkbox elements whose 'div id' starts with '#queue-checkbox'. Do not use element index-based selectors.",
                    "- Click the 'Bulk modify owners' button.",  
                    "- Select a new owner from the dropdown.",
                    "- Click the 'Apply' button. Wait for up to 3 seconds for the dialog closure.",
                    "- If the dialog box does not close, **consider the test case failed**.",
                    "- If the dialog box closes, confirm that the updated owner name is visible in the dashboard rows."
                ],  
                "expected_result": "The owner status of the selected rows is updated in the dashboard."  
            }}

    ---
  
    **IMPORTANT RULES**

        - Ensure the dashboard actually loads before executing the test cases.

        - After executing a test case:
            - **ALWAYS navigate back to the main dashboard or Home page** before starting the next test case. This is mandatory - test execution will fail otherwise.
        
        - **DO NOT retry or reattempt** any test case or step under any circumstances.
        - **DO NOT loop or retry** actions under any circumstance - including page changes, DOM updates, element index changes, or scrolling.

        - DO NOT take any action unless explicitly instructed. Follow the instructions exactly as written.

        - If a page reloads or changes state briefly, wait and observe unless explicitly told to act.

    ---

    **IGNORE AND CONTINUE**

        - Ignore messages like "Something new appeared after action".
        - Ignore messages like "Element index changed after action".
        - Continue with next step without interruption when these messages appear.
        - Do not treat these messages as errors or warnings.
    
    """
 
    # Initialize the AzureChatOpenAI language model with the provided credentials
    llm = AzureChatOpenAI(
        model_name=azure_openai_model,
        openai_api_key=azure_openai_api_key,
        azure_endpoint=azure_openai_endpoint,
        deployment_name=azure_openai_model,
        api_version=azure_openai_api_version,
        temperature=0,
        max_retries=2
    )
    #print(llm.invoke(task))
  
    try:
        # Specify the path to our Chrome executable
        chrome_path = os.environ["CHROME_EXECUTABLE_PATH"]
        user_data_dir = os.environ["CHROME_USER_DATA_DIRECTORY"]
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

        # Connect to the browser
        browser = Browser(
            config=BrowserConfig(
                chrome_instance_path=chrome_path,
                remote_debugging_port=chrome_debug_port
            )
        )

        # Initialize the BrowserUse Agent with the defined task, language model, browser, and controller
        agent = Agent(
            task=task, 
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
        #history.save_to_file("agentResults.json")

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
            filename = "test_case_execution_results.txt"
            with open(f"{filename}", "w") as file:  
                file.write("\n".join(report_lines))  
            print(f"Results saved to {filename}")
 
        else:  
            print('No results to display. The agent did not produce any output.')

        # Close the browser instance
        await browser.close()
    
    except Exception as e:  
        print(f"Failed to connect to the browser or execute the task: {e}")
 
if __name__ == "__main__":  
    asyncio.run(executeTestCases())