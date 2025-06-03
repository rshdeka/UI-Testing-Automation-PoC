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
from dotenv import load_dotenv
from test_scripts_generation import extract_test_cases, parse_test_cases_with_prompt, format_test_cases, filter_test_case_steps, generate_browseruse_agent_prompt


# Classes to define the output format of the Agent as a Pydantic model
class TestCase(BaseModel): 
    number: int 
    title: str  
    steps: List[str]  
    expected_result: str  
    actual_outcome_status: str
    actual_outcome_details: List[str]
  
class TestCasesSummary(BaseModel):  
    test_cases: List[TestCase]  
  
controller = Controller(output_model=TestCasesSummary)


# Define Playwright functions for individual test cases (as fallback mechanism)
#------------------------Copy and paste the functions from the generated text file------------------------
@controller.action('Login to the application.')
async def login(browser: BrowserContext):
    title = "Login Test Case"
    print(f"Fallback mechanism invoked for {title} task.")
    print(f"Executing {title} task.")

    page = await browser.new_page()
    actual_outcome_details = []

    try:
        await page.goto('https://<UI>/')
        await page.click('text=Log in with SSO')
        await page.click('text=ak@gmail.com')
        
        # Wait for Authenticator approval
        try:
            await page.wait_for_selector('your_dashboard_selector', timeout=10000)
            actual_outcome_status = "Passed"
        except Exception as e:
            actual_outcome_details.append(str(e))
            actual_outcome_status = "Failed"
            print("Authentication failed, stopping execution.")
            return ActionResult(
                extracted_content=f"Title: {title} \nActual outcome status: {actual_outcome_status} \nActual outcome details: {actual_outcome_details}",
                include_in_memory=True
            )
    except Exception as e:
        actual_outcome_details.append(str(e))
        actual_outcome_status = "Failed"

    return ActionResult(
        extracted_content=f"Title: {title} \nActual outcome status: {actual_outcome_status} \nActual outcome details: {actual_outcome_details}",
        include_in_memory=True
    )

@controller.action('Verify Navigation Bar Functionality.')
async def verify_navigation_bar(browser: BrowserContext):
    title = "Verify Navigation Bar Functionality"
    print(f"Fallback mechanism invoked for {title} task.")
    print(f"Executing {title} task.")

    page = await browser.get_current_page()
    actual_outcome_details = []

    try:
        is_visible = await page.is_visible('your_navigation_bar_selector')
        if is_visible:
            links = await page.query_selector_all('your_navigation_links_selector')
            for link in links:
                await link.click()
                # Verify redirection
                is_correct_page = await page.is_visible('your_correct_page_selector')
                if not is_correct_page:
                    actual_outcome_details.append("Redirection failed for one of the links.")
                    actual_outcome_status = "Failed"
                    break
            else:
                actual_outcome_status = "Passed"
        else:
            actual_outcome_details.append("Navigation bar is not visible.")
            actual_outcome_status = "Failed"
    except Exception as e:
        actual_outcome_details.append(str(e))
        actual_outcome_status = "Failed"

    return ActionResult(
        extracted_content=f"Title: {title} \nActual outcome status: {actual_outcome_status} \nActual outcome details: {actual_outcome_details}",
        include_in_memory=True
    )

@controller.action('Verify Bulk Modify Button Functionality.')
async def verify_bulk_modify(browser: BrowserContext):
    title = "Verify Bulk Modify Button Functionality"
    print(f"Fallback mechanism invoked for {title} task.")
    print(f"Executing {title} task.")

    page = await browser.get_current_page()
    actual_outcome_details = []

    try:
        await page.click('your_table_row_selector')  # Select multiple rows
        await page.click('your_bulk_modify_button_selector')
        await page.select_option('your_owner_status_dropdown_selector', 'new_owner_status')
        
        # Verify owner status update
        is_updated = await page.is_visible('your_updated_owner_status_selector')
        actual_outcome_status = "Passed" if is_updated else "Failed"
        if not is_updated:
            actual_outcome_details.append("Owner status update failed.")
    except Exception as e:
        actual_outcome_details.append(str(e))
        actual_outcome_status = "Failed"

    return ActionResult(
        extracted_content=f"Title: {title} \nActual outcome status: {actual_outcome_status} \nActual outcome details: {actual_outcome_details}",
        include_in_memory=True
    )

@controller.action('Verify Single Row Owner Change.')
async def verify_single_row_owner_change(browser: BrowserContext):
    title = "Verify Single Row Owner Change"
    print(f"Fallback mechanism invoked for {title} task.")
    print(f"Executing {title} task.")

    page = await browser.get_current_page()
    actual_outcome_details = []

    try:
        await page.click('your_single_row_selector')
        await page.click('your_owner_column_dropdown_selector')
        await page.select_option('your_owner_name_selector', 'new_owner_name')
        
        # Verify owner update
        is_updated = await page.is_visible('your_updated_owner_selector')
        actual_outcome_status = "Passed" if is_updated else "Failed"
        if not is_updated:
            actual_outcome_details.append("Owner update failed.")
    except Exception as e:
        actual_outcome_details.append(str(e))
        actual_outcome_status = "Failed"

    return ActionResult(
        extracted_content=f"Title: {title} \nActual outcome status: {actual_outcome_status} \nActual outcome details: {actual_outcome_details}",
        include_in_memory=True
    )

@controller.action('Verify Analyst Assignment.')
async def verify_analyst_assignment(browser: BrowserContext):
    title = "Verify Analyst Assignment"
    print(f"Fallback mechanism invoked for {title} task.")
    print(f"Executing {title} task.")

    page = await browser.get_current_page()
    actual_outcome_details = []

    try:
        await page.click('your_row_selector')
        await page.click('your_assign_analyst_button_selector')
        await page.select_option('your_analyst_dropdown_selector', 'analyst_name')
        
        # Verify analyst assignment
        is_assigned = await page.is_visible('your_assigned_analyst_selector')
        actual_outcome_status = "Passed" if is_assigned else "Failed"
        if not is_assigned:
            actual_outcome_details.append("Analyst assignment failed.")
    except Exception as e:
        actual_outcome_details.append(str(e))
        actual_outcome_status = "Failed"

    return ActionResult(
        extracted_content=f"Title: {title} \nActual outcome status: {actual_outcome_status} \nActual outcome details: {actual_outcome_details}",
        include_in_memory=True
    )

@controller.action('Verify Navigation Bar with Invalid URL.')
async def verify_navigation_bar_invalid_url(browser: BrowserContext):
    title = "Verify Navigation Bar with Invalid URL"
    print(f"Fallback mechanism invoked for {title} task.")
    print(f"Executing {title} task.")

    page = await browser.get_current_page()
    actual_outcome_details = []

    try:
        await page.click('your_navigation_link_selector')
        await page.goto('https://<UI>/invalid-url')
        
        # Verify error message or redirection
        is_error_displayed = await page.is_visible('your_error_message_selector')
        actual_outcome_status = "Passed" if is_error_displayed else "Failed"
        if not is_error_displayed:
            actual_outcome_details.append("Error message or redirection failed.")
    except Exception as e:
        actual_outcome_details.append(str(e))
        actual_outcome_status = "Failed"

    return ActionResult(
        extracted_content=f"Title: {title} \nActual outcome status: {actual_outcome_status} \nActual outcome details: {actual_outcome_details}",
        include_in_memory=True
    )

@controller.action('Verify Bulk Modify with No Rows Selected.')
async def verify_bulk_modify_no_rows(browser: BrowserContext):
    title = "Verify Bulk Modify with No Rows Selected"
    print(f"Fallback mechanism invoked for {title} task.")
    print(f"Executing {title} task.")

    page = await browser.get_current_page()
    actual_outcome_details = []

    try:
        await page.click('your_bulk_modify_button_selector')
        
        # Attempt to change owner status
        is_error_displayed = await page.is_visible('your_error_message_selector')
        actual_outcome_status = "Passed" if is_error_displayed else "Failed"
        if not is_error_displayed:
            actual_outcome_details.append("Error message not displayed when no rows are selected.")
    except Exception as e:
        actual_outcome_details.append(str(e))
        actual_outcome_status = "Failed"

    return ActionResult(
        extracted_content=f"Title: {title} \nActual outcome status: {actual_outcome_status} \nActual outcome details: {actual_outcome_details}",
        include_in_memory=True
    )

@controller.action('Verify Single Row Owner Change with Invalid Name.')
async def verify_single_row_owner_change_invalid_name(browser: BrowserContext):
    title = "Verify Single Row Owner Change with Invalid Name"
    print(f"Fallback mechanism invoked for {title} task.")
    print(f"Executing {title} task.")

    page = await browser.get_current_page()
    actual_outcome_details = []

    try:
        await page.click('your_single_row_selector')
        await page.click('your_owner_column_dropdown_selector')
        
        # Attempt to select invalid name
        is_error_displayed = await page.is_visible('your_error_message_selector')
        actual_outcome_status = "Passed" if is_error_displayed else "Failed"
        if not is_error_displayed:
            actual_outcome_details.append("Error message not displayed for invalid owner name selection.")
    except Exception as e:
        actual_outcome_details.append(str(e))
        actual_outcome_status = "Failed"

    return ActionResult(
        extracted_content=f"Title: {title} \nActual outcome status: {actual_outcome_status} \nActual outcome details: {actual_outcome_details}",
        include_in_memory=True
    )

@controller.action('Verify Analyst Assignment with No Analyst Selected.')
async def verify_analyst_assignment_no_analyst(browser: BrowserContext):
    title = "Verify Analyst Assignment with No Analyst Selected"
    print(f"Fallback mechanism invoked for {title} task.")
    print(f"Executing {title} task.")

    page = await browser.get_current_page()
    actual_outcome_details = []

    try:
        await page.click('your_row_selector')
        await page.click('your_assign_analyst_button_selector')
        
        # Attempt to save without selecting an analyst
        is_error_displayed = await page.is_visible('your_error_message_selector')
        actual_outcome_status = "Passed" if is_error_displayed else "Failed"
        if not is_error_displayed:
            actual_outcome_details.append("Error message not displayed for no analyst selection.")
    except Exception as e:
        actual_outcome_details.append(str(e))
        actual_outcome_status = "Failed"

    return ActionResult(
        extracted_content=f"Title: {title} \nActual outcome status: {actual_outcome_status} \nActual outcome details: {actual_outcome_details}",
        include_in_memory=True
    )


# Function to initialize browser and handle setup
async def initialize_browser():
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
    
    except Exception as e:  
        print(f"Failed to initialize the browser: {e}")

    return chrome_path, chrome_debug_port


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
        # Parse the test cases first
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
        login_task, test_case_task, browseruse_task = generate_browseruse_agent_prompt(app_url, login_account, filtered_positive_test_cases, filtered_negative_test_cases)
        
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
                    headless=False,
                    disable_security=True
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
        return {
            "An error occurred during test case execution."   
        }
    
if __name__ == "__main__":
    asyncio.run(execute_test_cases())