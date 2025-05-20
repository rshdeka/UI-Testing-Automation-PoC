import os  
import asyncio  
import subprocess  
import requests  
import time  
import json  
from langchain_openai import AzureChatOpenAI  
from browser_use import Agent, Controller
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext
from browser_use.agent.views import ActionResult
from pydantic import BaseModel
from playwright.async_api import async_playwright
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


# Define Playwright functions for individual test cases (as fallback mechanism)
#-----------------------------------Test Case 1-----------------------------------
@controller.action('Verify that the user can log in to the application using valid credentials.')
async def verify_user_login(browser: BrowserContext):
    title = "Login Functionality Test"  
    print(f"Executing {title}")
    
    page = await browser.get_current_page()
    actual_outcome_details = []
    
    # Open the login page  
    try:
        await page.goto(app_url)                         # Navigate to the specified URL  
        await page.wait_for_load_state('load')           # Wait for the page to load completely  
        print("Login page loaded successfully.")  
    except Exception as e:
        actual_outcome_status = "Failed"  
        actual_outcome_details.append(f"Failed to load the login page: {str(e)}")
        print(f"Failed to load the login page: {e}")
    
    # Enter valid credentials  
    try: 
        # Click 'Log in with Email ID'  
        await page.click('text="Log in with Email ID"')
        # Wait for the account selection to appear
        await page.wait_for_selector('text="Pick an account"')
        # Select the appropriate account  
        await page.click(f'text="{login_account}"')  
        print(f"Logged in with the account {login_account}.")  
    except Exception as e:
        actual_outcome_status = "Failed"  
        actual_outcome_details.append(f"Failed to log in with the account {login_account}: {str(e)}")
        print(f"Failed to log in with the account {login_account}: {e}")
    
    # Wait for the Authenticator approval (if prompted)
    try:
        authenticator_prompt_selector = 'text="Approve sign in request"'
        approval_required = await page.query_selector(authenticator_prompt_selector)
        
        if approval_required:  
            print("Authenticator prompt detected, waiting for approval...")
            approval_received = False
            start_time = time.time()  
            timeout_seconds = 300
    
            # Loop to wait for user approval, with a timeout of 300 seconds
            while time.time() - start_time < timeout_seconds:  
                try:  
                    # Check if the approval prompt is visible  
                    await page.wait_for_selector(authenticator_prompt_selector, timeout=5000)  
                    print("Waiting for user to approve the sign-in request...")  
                except Exception:
                    approval_received = True     # If the prompt is no longer visible, assume approval is complete
                    break

            if not approval_received:
                actual_outcome_status = "Failed"  
                actual_outcome_details.append("Failed to get Authenticator approval after account selection.")  
                print("Failed to get Authenticator approval after account selection.")  
            else:  
                print("Authenticator approval received, proceeding with login.")
        else:  
            print("No authenticator prompt detected, proceeding directly to the dashboard.")
    except Exception as e:
        actual_outcome_status = "Failed"  
        actual_outcome_details.append(f"Failed during Authenticator approval process: {str(e)}")
        print(f"Failed during Authenticator approval process: {e}")

    # Wait for the original login page to redirect to the dashboard
    login_page = await page.is_visible('text="Log in with Email ID"')
    if login_page:
        await page.wait_for_timeout(10000)        # Wait for 10 seconds  
        print("Waiting for the original page to redirect to the dashboard...")  
    
        # Verify that the dashboard loads successfully
        try:
            # Wait for the dashboard to fully load 
            await page.wait_for_selector('text="Benefit plan queue"', timeout=10000)
            print("UI dashboard loaded successfully.")  
            actual_outcome_status = "Passed"  
            actual_outcome_details.append("UI dashboard loaded successfully.")  
        except Exception as e:
            print(f"Failed to load the dashboard: {e}")
            actual_outcome_status = "Failed"  
            actual_outcome_details.append(f"UI dashboard did not load successfully: {str(e)}")
    else:
        print(f"Failed to re-direct to the dashboard: {e}")
        actual_outcome_status = "Failed"  
        actual_outcome_details.append(f"UI dashboard did not load successfully: {str(e)}")
    
    print(actual_outcome_status)  
    print(actual_outcome_details)
    return ActionResult(
        extracted_content=f"Title: {title} \nActual outcome status: {actual_outcome_status} \nActual outcome details: {actual_outcome_details}",
        include_in_memory=True
    )

#-----------------------------------Test Case 2-----------------------------------
@controller.action('Verify that the site navigation at the top of the page displays all pages in the application.')
async def verify_site_nav(browser: BrowserContext):
    title = "Navigation Display Test"
    print(f"Executing {title}")

    page = await browser.get_current_page()
    actual_outcome_details = []

    # Observe the navigation bar at the top of the page to check visibility of each navigation item  
    try:
        home_visible = await page.is_visible('#menu-item-home')  
    except Exception as e:  
        home_visible = False  
        actual_outcome_details.append(f"Failed to verify visibility of 'Home' page: {str(e)}")

    try:
        manage_plans_visible = await page.is_visible('#menu-item-manage-plans')
    except Exception as e:  
        manage_plans_visible = False  
        actual_outcome_details.append(f"Failed to verify visibility of 'Manage Plans' page: {str(e)}") 

    try:
        support_visible = await page.is_visible('#menu-item-support')
    except Exception as e:  
        support_visible = False  
        actual_outcome_details.append(f"Failed to verify visibility of 'Support' page: {str(e)}")

    try:
        sign_out_visible = await page.is_visible('#menu-item-sign-out')
    except Exception as e:  
        sign_out_visible = False  
        actual_outcome_details.append(f"Failed to verify visibility of 'Sign Out' page: {str(e)}")

    if home_visible and manage_plans_visible and support_visible and sign_out_visible:
        actual_outcome_status = "Passed"  
        actual_outcome_details.append("Navigation items are visible and accessible.")  
    else:
        actual_outcome_status = "Failed"  
        if not home_visible:  
            actual_outcome_details.append("Home item is not visible.")  
        if not manage_plans_visible:  
            actual_outcome_details.append("Manage plans item is not visible.")  
        if not support_visible:  
            actual_outcome_details.append("Support item is not visible.")  
        if not sign_out_visible:  
            actual_outcome_details.append("Sign out item is not visible.")  
    
    print(actual_outcome_status)
    print(actual_outcome_details)
    return ActionResult(
        extracted_content=f"Title: {title} \nActual outcome status: {actual_outcome_status} \nActual outcome details: {actual_outcome_details}", 
        include_in_memory=True
    )

#-----------------------------------Test Case 3-----------------------------------
@controller.action('Verify that the user can bulk change the owner status using the Bulk modify button.')
async def bulk_modify_owner_status(browser: BrowserContext):
    title = "Bulk Modify Owner Status Test"
    print(f"Executing {title}")

    page = await browser.get_current_page()
    actual_outcome_details = []
    
    # Select multiple rows in the queue using checkboxes
    try:
        await page.click('#queue-checkbox-0')
        await page.click('#queue-checkbox-1')
        await page.click('#queue-checkbox-4')
        await page.click('#queue-checkbox-5')
        print("Rows selected successfully.")  
    except Exception as e:
        actual_outcome_status = "Failed"  
        actual_outcome_details.append(f"Failed to select multiple rows: {str(e)}")
        print("Failed to select multiple rows.")

    # Click the 'Bulk modify' button  
    try:
        await page.click('text="Bulk modify owners"')
        print("Clicked 'Bulk modify owners' button.")  
    except Exception as e:
        actual_outcome_status = "Failed"  
        actual_outcome_details.append(f"Failed to click 'Bulk modify owners' button: {str(e)}")  
        print("Failed to click 'Bulk modify owners' button.")

    # Change the owner status
    try:
        await page.click('text="Select owner"')             # Wait for the dropdown to appear and select a new owner
        await page.click('text="Second Name"')              # Select the new owner by visible text
        await page.is_visible('text="Second Name"', timeout=5000)      
        await page.click('text="Apply"')                    # Apply the changes   
        print("Owner status changed successfully.") 
    except Exception as e:  
        actual_outcome_status = "Failed"  
        actual_outcome_details.append(f"Failed to change owner status: {str(e)}")  
        print("Failed to change owner status.") 

    # Wait for the dialog box to close and navigate back to the original page
    try:
        await page.wait_for_timeout(2000)
        if not await page.is_visible('text="Apply"'):       # If dialog box closes, the owner change passed
            actual_outcome_status = "Passed"
            actual_outcome_details.append("The owner status of the selected rows is updated.") 
        else:
            await page.click('text="Cancel"')               # If the owner change fails, click "Cancel" and log the failure
            actual_outcome_status = "Failed"
            actual_outcome_details.append("The 'Apply' button is not clickable. Failed to verify owner status change.") 
    except Exception as e:  
        actual_outcome_status = "Failed"  
        actual_outcome_details.append(f"Failed to verify bulk owner status change: {str(e)}")  

    print(actual_outcome_status)  
    print(actual_outcome_details)  
    return ActionResult(
        extracted_content=f"Title: {title} \nActual outcome status: {actual_outcome_status} \nActual outcome details: {actual_outcome_details}",
        include_in_memory=True
    )  

#-----------------------------------Test Case 4-----------------------------------
@controller.action('Verify that the user can change the owner of a single row by selecting a name in the owner column.')
async def single_row_owner_change(browser: BrowserContext):
    title = "Single Row Owner Change Test"
    print(f"Executing {title}")

    page = await browser.get_current_page()
    actual_outcome_details = []

    # Unselect the selected rows in the queue
    try:
        await page.click('#queue-top-checkbox')
        print("Unselected all rows successfully.")  
    except Exception as e:  
        actual_outcome_status = "Failed"  
        actual_outcome_details.append(f"Failed to unselect selected rows: {str(e)}")  
        print("Failed to unselect selected rows.")
    
    # Select a row in the queue using checkbox
    try:
        await page.click('#queue-checkbox-0')
        print("Selected a single row successfully.")
    except Exception as e:  
        actual_outcome_status = "Failed"  
        actual_outcome_details.append(f"Failed to select a single row: {str(e)}")  
        print("Failed to select a single row.")
    
    # Click on the owner dropdown for the selected row  
    try:
        owner_dropdown_selector = '#queue-table-cell-owner-0'
        await page.click(owner_dropdown_selector)
        await page.click('text="Second Name"')              # Select the new owner by visible text
        print("Owner selected from dropdown successfully.")
    except Exception as e:  
        actual_outcome_status = "Failed"  
        actual_outcome_details.append(f"Failed to select owner from dropdown: {str(e)}")  
        print("Failed to select owner from dropdown.")

    # Verify that the owner change was successful  
    try:
        owner_changed = await page.is_visible('text="Second Name"', timeout=5000)
        if owner_changed:
            actual_outcome_status = "Passed"  
            actual_outcome_details.append("The owner of the selected row is updated.")  
        else:  
            actual_outcome_status = "Failed"  
            actual_outcome_details.append("Failed to verify owner change for the selected row.") 
    except Exception as e:  
        actual_outcome_status = "Failed"  
        actual_outcome_details.append(f"Failed to verify single owner status change: {str(e)}")   

    print(actual_outcome_status)  
    print(actual_outcome_details)  
    return ActionResult(
        extracted_content=f"Title: {title} \nActual outcome status: {actual_outcome_status} \nActual outcome details: {actual_outcome_details}",
        include_in_memory=True
    )


# Function to integrate BrowserUse and Playwright for browser automation and execute defined test cases
async def executeTestCases():
    # Define the prompt/task for the AI agent  
    task = f"""  
    **AI Agent Task: UI Testing Automation**  
    **Objective: Execute defined test cases on the application and summarize the results.**
 
    ---

    1. Execute each test case exactly once. No retries or reattempts at all.
        - Execute **each step in sequence** as defined in the test cases ONLY.

        - **Test Case 1**
            {{
                "name": "Login Functionality Test",  
                "description": "Verify that the user can log in to the application using valid credentials.",  
                "steps": [  
                    "- Navigate to the login URL {app_url}.",  
                    "- Click 'Log in with SSO'.",  
                    "- Select the account {login_account}.",  
                    "- Wait for Authenticator approval (if prompted).",
                    "- The login page may re-load briefly. This is expected - do not take any action or treat this as a failure.",
                    "- Wait for the page to automatically redirect to the UI dashboard.",
                    "- Verify that the dashboard has loaded by checking the presence of a 'Sign out' button."
                ],
                "expected_result": "Dashboard loads successfully and the 'Sign out' button is visible."
            }}

        - **Test Case 2**
            {{
                "name": "Navigation Display Test",
                "description": "Verify that the site navigation at the top of the page displays all pages in the application.",  
                "steps": [
                    "- Observe the navigation bar at the top of the page."  
                ],  
                "expected_result": "All pages in the application are listed in the navigation bar."  
            }}

        - **Test Case 3**
            {{
                "name": "Bulk Modify Owner Status Test",  
                "description": "Verify that the user can bulk change the owner status using the 'Bulk modify' button.",  
                "steps": [
                    "- Select multiple rows in the queue.",  
                    "- Click the 'Bulk modify' button.",  
                    "- Change the owner status."
                ],  
                "expected_result": "The owner status of the selected rows is updated."  
            }}

        - **Test Case 4**
            {{
                "name": "Single Row Owner Change Test",
                "description": "Verify that the user can change the owner of a single row by selecting a name in the owner column.",
                "steps": [
                    "- Select a single row in the queue.",
                    "- Click on the owner column.",
                    "- Select a new owner from the dropdown."
                ],
                "expected_result": "The owner of the selected row is updated."
            }}

    2. Check if the actual outcomes match the expected results, indicating successful execution.
        
    3. If any test case fails, **log an error and move on to the next test case** instead of retrying.
        - No retries or reattempts should be performed for any test case at all.
        - Continue testing with the next test case to ensure all scenarios are evaluated.
    
    ---  
  
    **IMPORTANT RULES**    
        
        - Ensure the dashboard actually loads before executing the test cases.  
        - No retries or reattempts should be performed for any test case at all.
        - Do not take any action unless explicitly instructed. Follow the instructions exactly as written.
        - If a page reloads or changes state briefly, wait and observe unless explicitly told to act.
    
    """
 
    # Initialize the AzureChatOpenAI language model with the provided credentials
    llm = AzureChatOpenAI(
        model_name=azure_openai_model,
        openai_api_key=azure_openai_api_key,
        azure_endpoint=azure_openai_endpoint,
        deployment_name=azure_openai_model,
        api_version=azure_openai_api_version,
        temperature=0
    )
    #print(llm.invoke(task))
  
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

        # Connect to the browser
        browser = Browser(
            config=BrowserConfig(
                chrome_instance_path=chrome_path,
                remote_debugging_port=chrome_debug_port
            )
        )

        # Initialize the BrowserUse Agent with the defined task, language model, browser, and controller
        agent = Agent(task=task, llm=llm, browser=browser, controller=controller, tool_calling_method="function_calling")

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
 
if __name__ == "__main__":  
    asyncio.run(executeTestCases())