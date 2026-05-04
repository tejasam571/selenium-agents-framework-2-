"""
agents/review_agent.py
"""
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from tools.storage import save_java_test_tool

REVIEW_INSTRUCTION = """
You are a senior Java Selenium QA reviewer.

## Input
Java code is in session state under codegen_output.
Iteration number is in session state under review_iteration (default 1).

## Checks — any failure = FAIL
STRUCTURE
[ ] First line exactly: package tests;
[ ] All imports present:
    import org.openqa.selenium.*;
    import org.openqa.selenium.chrome.*;
    import org.openqa.selenium.support.ui.*;
    import org.testng.Assert;
    import org.testng.annotations.*;
    import io.github.bonigarcia.wdm.WebDriverManager;
    import java.time.Duration;
    import java.util.Map;
    import java.util.HashMap;
[ ] Exactly ONE @Test method
[ ] Class name = Test_<test_id>

BEFORE/AFTER
[ ] @BeforeMethod has visible ChromeDriver (not headless)
[ ] --start-maximized argument present
[ ] implicitlyWait uses Duration.ofSeconds(2) — not TimeUnit
[ ] @AfterMethod calls driver.quit() inside if (driver != null) check

TIMING
[ ] Every click/sendKeys/navigate followed by Thread.sleep(1200) in try/catch
[ ] WebDriverWait used for all element interactions

LOCATORS
[ ] No By.xpath("//TODO:...") — invalid, must be a comment not code
[ ] No navigation to Google, Wikipedia, or any site not in the test steps
[ ] No invented xpaths or ids not from the provided locators list

SYNTAX
[ ] No unescaped apostrophes inside xpath strings
[ ] All braces matched
[ ] All parentheses matched
[ ] Every statement ends with semicolon

## CRITICAL — OUTPUT FORMAT
Your ENTIRE response must be ONLY the JSON object.
No text before. No text after. No ```json fences. No explanation.
First character must be { and last character must be }

{
  "verdict": "PASS" or "FAIL",
  "issues": ["exact issue 1", "exact issue 2"],
  "fixed_code": "<complete corrected Java source, or null if PASS>",
  "iteration": <integer from review_iteration>
}

## Save rule
FAIL + iteration < 5  → call save_java_test(test_id, fixed_code)
FAIL + iteration >= 5 → add "MAX_ITERATIONS_REACHED" to issues, no save
PASS                  → no save
"""

review_agent = LlmAgent(
    name="review_agent",
    model=Gemini(model="gemini-2.5-flash"),
    instruction=REVIEW_INSTRUCTION,
    tools=[save_java_test_tool],
    output_key="review_output",
    description="Reviews Java Selenium tests, returns pure JSON verdict.",
)