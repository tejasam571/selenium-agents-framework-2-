# """
# main.py
# ─────────────────────────────────────────────────────────────────
# Entry point for the Java Selenium ADK pipeline.

# Run modes
# ─────────
#   python main.py              → full pipeline (CSV → Java tests → Maven)
#   adk web                     → ADK Web UI (uses root_agent from agents/)

# Environment variables (.env)
# ────────────────────────────
#   GOOGLE_API_KEY   – Gemini API key  (for codegen + review agents)
#   GROQ_API_KEY     – Groq API key    (for RAG retrieval via Groq)
# """

# import asyncio
# import csv
# import json
# import os
# from pathlib import Path

# from dotenv import load_dotenv
# from google.adk.runners import Runner
# from google.adk.sessions import InMemorySessionService
# from google.adk.models.google_llm import _ResourceExhaustedError
# from google.genai.types import Content, Part

# from agents.root_agent import root_agent
# from tools.crawler import crawl_locators
# from tools.rag_csv import build_rag_index

# load_dotenv()

# # ── Config ────────────────────────────────────────────────────────────────────
# APP_URL           = "https://wealth.bmo.com/wealth/onboard/onlineinvesting/#/set-expectation?lang=en"
# CSV_PATH          = "data/test_cases.csv"
# APP_ID            = "java_selenium_app"
# USER_ID           = "runner"
# INTER_TEST_DELAY  = 15       # seconds between test cases
# LOCATORS_MAX      = 40       # max elements sent per agent call


# # ── Helpers ───────────────────────────────────────────────────────────────────

# def load_csv(path: str) -> list[dict]:
#     with open(path, newline="", encoding="utf-8") as f:
#         return list(csv.DictReader(f))


# def trim_locators(locators_json: str, max_elements: int = LOCATORS_MAX) -> str:
#     data = json.loads(locators_json)
#     data["elements"] = data["elements"][:max_elements]
#     return json.dumps(data)


# def setup_maven_project():
#     src = Path("java_tests/src/test/java/tests")
#     src.mkdir(parents=True, exist_ok=True)
#     pom = Path("java_tests/pom.xml")
#     if not pom.exists():
#         pom.write_text(POM_XML)
#         print("[Init] Maven pom.xml created.")


# def run_maven_tests():
#     import subprocess
#     print("\n[Run] Running Maven tests …")
#     result = subprocess.run(
#         ["mvn", "test", "-f", "java_tests/pom.xml"],
#         capture_output=False,
#     )
#     print(f"\n[Done] Maven exit code: {result.returncode}")
#     print("Report → java_tests/target/surefire-reports/")


# # ── Pipeline ──────────────────────────────────────────────────────────────────

# async def run_pipeline():
#     print("=" * 60)
#     print("  Java Selenium ADK Multi-Agent Pipeline")
#     print("=" * 60)

#     # 1. Build RAG index from CSV
#     print(f"\n[Init] Building RAG index from {CSV_PATH} …")
#     rag_status = build_rag_index(CSV_PATH)
#     print(f"[Init] RAG status: {rag_status}")

#     # 2. Auto-crawl (cached after first run; pass force_recrawl=True to refresh)
#     print(f"\n[Init] Auto-crawling {APP_URL} …")
#     locators_json = await crawl_locators(APP_URL)
#     locators_json = trim_locators(locators_json)
#     n_elems = len(json.loads(locators_json)["elements"])
#     print(f"[Init] Using {n_elems} locator elements.")

#     # 3. Load test cases
#     rows = load_csv(CSV_PATH)
#     session_service = InMemorySessionService()
#     runner = Runner(
#         agent=root_agent,
#         app_name=APP_ID,
#         session_service=session_service,
#     )
#     setup_maven_project()

#     # 4. Generate a test for each row
#     for idx, tc in enumerate(rows):
#         tc_id      = tc.get("Test Case ID", f"tc_{idx}")
#         session_id = f"session_{tc_id}"

#         await session_service.create_session(
#             app_name=APP_ID,
#             user_id=USER_ID,
#             session_id=session_id,
#             state={
#                 "app_url":  APP_URL,
#                 "locators": locators_json,
#             },
#         )

#         print(f"\n── Generating: {tc_id} ──")
#         message = Content(role="user", parts=[Part(text=json.dumps(tc))])

#         for attempt in range(5):
#             try:
#                 async for event in runner.run_async(
#                     user_id=USER_ID,
#                     session_id=session_id,
#                     new_message=message,
#                 ):
#                     if event.is_final_response() and event.content:
#                         print(f"  [Done] {tc_id}")
#                 break

#             except _ResourceExhaustedError:
#                 wait = 60 * (attempt + 1)
#                 print(f"  [429] Rate limited. Retry {attempt+1}/5 in {wait}s …")
#                 await asyncio.sleep(wait)
#         else:
#             print(f"  [SKIP] {tc_id} — failed after 5 retries.")

#         if idx < len(rows) - 1:
#             print(f"  [Pause] {INTER_TEST_DELAY}s before next test …")
#             await asyncio.sleep(INTER_TEST_DELAY)

#     # 5. Run Maven
#     run_maven_tests()


# # ── Maven POM ─────────────────────────────────────────────────────────────────
# POM_XML = """<?xml version="1.0" encoding="UTF-8"?>
# <project xmlns="http://maven.apache.org/POM/4.0.0"
#          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
#          xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
#                              http://maven.apache.org/xsd/maven-4.0.0.xsd">
#   <modelVersion>4.0.0</modelVersion>
#   <groupId>selenium.tests</groupId>
#   <artifactId>generated-tests</artifactId>
#   <version>1.0</version>
#   <properties>
#     <maven.compiler.source>11</maven.compiler.source>
#     <maven.compiler.target>11</maven.compiler.target>
#     <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
#   </properties>
#   <dependencies>
#     <dependency>
#       <groupId>org.seleniumhq.selenium</groupId>
#       <artifactId>selenium-java</artifactId>
#       <version>4.20.0</version>
#     </dependency>
#     <dependency>
#       <groupId>org.testng</groupId>
#       <artifactId>testng</artifactId>
#       <version>7.10.2</version>
#       <scope>test</scope>
#     </dependency>
#     <dependency>
#       <groupId>io.github.bonigarcia</groupId>
#       <artifactId>webdrivermanager</artifactId>
#       <version>5.8.0</version>
#       <scope>test</scope>
#     </dependency>
#   </dependencies>
#   <build>
#     <plugins>
#       <plugin>
#         <groupId>org.apache.maven.plugins</groupId>
#         <artifactId>maven-surefire-plugin</artifactId>
#         <version>3.2.5</version>
#         <configuration>
#           <reportFormat>html</reportFormat>
#         </configuration>
#       </plugin>
#     </plugins>
#   </build>
# </project>"""

# if __name__ == "__main__":
#     asyncio.run(run_pipeline())

# """
# main.py
# """

# import asyncio
# import csv
# import json
# from pathlib import Path

# from dotenv import load_dotenv
# from google.adk.runners import Runner
# from google.adk.sessions import InMemorySessionService
# from google.adk.models.google_llm import _ResourceExhaustedError
# from google.genai.types import Content, Part

# from agents.root_agent import root_agent
# from tools.crawler import crawl_locators
# from tools.rag_csv import build_rag_index

# load_dotenv()

# APP_URL          = "https://wealth.bmo.com/wealth/onboard/onlineinvesting/#/set-expectation?lang=en"
# CSV_PATH         = "data/test_cases.csv"
# APP_ID           = "java_selenium_app"
# USER_ID          = "runner"
# INTER_TEST_DELAY = 30
# LOCATORS_MAX     = 40


# def load_csv(path: str) -> list[dict]:
#     with open(path, newline="", encoding="utf-8") as f:
#         return list(csv.DictReader(f))


# def trim_locators(locators_json: str, max_elements: int = LOCATORS_MAX) -> str:
#     data = json.loads(locators_json)
#     data["elements"] = data["elements"][:max_elements]
#     return json.dumps(data)


# def setup_maven_project():
#     src = Path("java_tests/src/test/java/tests")
#     src.mkdir(parents=True, exist_ok=True)
#     pom = Path("java_tests/pom.xml")
#     if not pom.exists():
#         pom.write_text(POM_XML)
#         print("[Init] Maven pom.xml created.")


# def run_maven_tests():
#     import subprocess
#     print("\n[Run] Running Maven tests …")
#     result = subprocess.run(
#         ["mvn", "test", "-f", "java_tests/pom.xml"],
#         capture_output=False,
#         shell=True,
#     )
#     print(f"\n[Done] Maven exit code: {result.returncode}")
#     print("Report → java_tests/target/surefire-reports/")


# async def run_pipeline():
#     print("=" * 60)
#     print("  Java Selenium ADK Multi-Agent Pipeline")
#     print("=" * 60)

#     print(f"\n[Init] Building RAG index from {CSV_PATH} …")
#     rag_status = build_rag_index(CSV_PATH)
#     print(f"[Init] RAG status: {rag_status}")

#     print(f"\n[Init] Auto-crawling {APP_URL} …")
#     locators_json = await crawl_locators(APP_URL, force_recrawl=True)
#     locators_json = trim_locators(locators_json)
#     n_elems = len(json.loads(locators_json)["elements"])
#     print(f"[Init] Using {n_elems} locator elements.")

#     rows = load_csv(CSV_PATH)
#     session_service = InMemorySessionService()
#     runner = Runner(
#         agent=root_agent,
#         app_name=APP_ID,
#         session_service=session_service,
#     )
#     setup_maven_project()

#     for idx, tc in enumerate(rows):
#         tc_id      = tc.get("Test Case ID", f"tc_{idx}")
#         session_id = f"session_{tc_id}"

#         await session_service.create_session(
#             app_name=APP_ID,
#             user_id=USER_ID,
#             session_id=session_id,
#             state={
#                 "app_url":          APP_URL,
#                 "locators":         locators_json,
#                 "review_iteration": 1,
#                 "review_feedback":  None,
#             },
#         )

#         print(f"\n── Generating: {tc_id} ──")
#         message = Content(role="user", parts=[Part(text=json.dumps(tc))])

#         for attempt in range(5):
#             try:
#                 async for event in runner.run_async(
#                     user_id=USER_ID,
#                     session_id=session_id,
#                     new_message=message,
#                 ):
#                     if event.is_final_response() and event.content:
#                         print(f"  [Done] {tc_id}")
#                 break
#             except _ResourceExhaustedError:
#                 wait = 60 * (attempt + 1)
#                 print(f"  [429] Rate limited. Retry {attempt+1}/5 in {wait}s …")
#                 await asyncio.sleep(wait)
#         else:
#             print(f"  [SKIP] {tc_id} — failed after 5 retries.")

#         if idx < len(rows) - 1:
#             print(f"  [Pause] {INTER_TEST_DELAY}s before next test …")
#             try:
#                 await asyncio.sleep(INTER_TEST_DELAY)
#             except (asyncio.CancelledError, KeyboardInterrupt):
#                 print("\n[Interrupted] Stopping gracefully.")
#                 break

#     run_maven_tests()
#     print("\n[Done] Report → java_tests/target/surefire-reports/")


# POM_XML = """<?xml version="1.0" encoding="UTF-8"?>
# <project xmlns="http://maven.apache.org/POM/4.0.0"
#          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
#          xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
#                              http://maven.apache.org/xsd/maven-4.0.0.xsd">
#   <modelVersion>4.0.0</modelVersion>
#   <groupId>selenium.tests</groupId>
#   <artifactId>generated-tests</artifactId>
#   <version>1.0</version>
#   <properties>
#     <maven.compiler.source>17</maven.compiler.source>
#     <maven.compiler.target>17</maven.compiler.target>
#     <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
#   </properties>
#   <dependencies>
#     <dependency>
#       <groupId>org.seleniumhq.selenium</groupId>
#       <artifactId>selenium-java</artifactId>
#       <version>4.20.0</version>
#     </dependency>
#     <dependency>
#       <groupId>org.testng</groupId>
#       <artifactId>testng</artifactId>
#       <version>7.10.2</version>
#       <scope>test</scope>
#       <exclusions>
#         <exclusion>
#           <groupId>xml-apis</groupId>
#           <artifactId>xml-apis</artifactId>
#         </exclusion>
#       </exclusions>
#     </dependency>
#     <dependency>
#       <groupId>io.github.bonigarcia</groupId>
#       <artifactId>webdrivermanager</artifactId>
#       <version>5.8.0</version>
#       <scope>test</scope>
#     </dependency>
#   </dependencies>
#   <build>
#     <plugins>
#       <plugin>
#         <groupId>org.apache.maven.plugins</groupId>
#         <artifactId>maven-surefire-plugin</artifactId>
#         <version>3.2.5</version>
#         <configuration>
#           <includes>
#             <include>**/Test_*.java</include>
#           </includes>
#         </configuration>
#       </plugin>
#     </plugins>
#   </build>
# </project>"""


# if __name__ == "__main__":
#     try:
#         asyncio.run(run_pipeline())
#     except KeyboardInterrupt:
#         print("\n[Stopped] Pipeline interrupted by user.")

#the above code was in usage 
"""
main.py
"""
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.models.google_llm import _ResourceExhaustedError
from google.genai.types import Content, Part

from agents.codegen_agent import codegen_agent
from agents.review_agent  import review_agent
from tools.crawler        import crawl_locators
from tools.locator_tree   import reload_tree
from tools.storage        import save_java_test
from tools.tc_parser      import parse_test_cases, fetch_locators_for_tc, build_prompt
import tools.crawler as _crawler

load_dotenv()

APP_URL          = "https://www.saucedemo.com/"
CSV_PATH         = "data/test_cases_sause.csv"
APP_ID           = "java_selenium_app"
USER_ID          = "runner"
INTER_TEST_DELAY = 10
MAX_REVIEW_ITER  = 3

_crawler.LOGIN_URL      = APP_URL
_crawler.LOGIN_USERNAME = None
_crawler.LOGIN_PASSWORD = None


def setup_maven_project():
    src = Path("java_tests/src/test/java/tests")
    src.mkdir(parents=True, exist_ok=True)
    pom = Path("java_tests/pom.xml")
    if not pom.exists():
        pom.write_text(POM_XML)
        print("[Init] Maven pom.xml created.")


def run_maven_tests():
    import subprocess
    print("\n[Run] Running Maven tests ...")
    result = subprocess.run(
        ["mvn", "clean", "test"],
        cwd=Path("java_tests"),
        capture_output=False,
        shell=True,
    )
    print(f"\n[Done] Maven exit code: {result.returncode}")


async def run_agent(runner, session_id, message):
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=message,
    ):
        if event.is_final_response() and event.content:
            pass


# ── PHASE 1 ───────────────────────────────────────────────────────
async def codegen_all(rows, session_service):
    generated = {}
    runner = Runner(agent=codegen_agent, app_name=APP_ID, session_service=session_service)

    for idx, tc in enumerate(rows):
        tc_id = tc["test_id"]
        print(f"  [Codegen {idx+1}/{len(rows)}] {tc_id} ...")

        # ── fetch locators for THIS tc only ──────────────────────
        locators = fetch_locators_for_tc(tc, page_url=APP_URL)
        print(f"    [Tree] {len(locators)} locators matched for {tc_id}")

        # ── build final prompt: TC fields + matched locators ─────
        prompt = build_prompt(tc, locators)

        session_id = f"codegen_{tc_id}"
        await session_service.create_session(
            app_name=APP_ID, user_id=USER_ID, session_id=session_id,
            state={"app_url": APP_URL, "review_feedback": None},
        )

        for attempt in range(3):
            try:
                await run_agent(runner, session_id, Content(
                    role="user",
                    parts=[Part(text=prompt)]   # ← TC + locators only, nothing else
                ))
                break
            except _ResourceExhaustedError:
                wait = 60 * (attempt + 1)
                print(f"    [429] Retry in {wait}s ...")
                await asyncio.sleep(wait)

        sess = await session_service.get_session(
            app_name=APP_ID, user_id=USER_ID, session_id=session_id
        )
        java_code = sess.state.get("codegen_output", "")

        if java_code:
            generated[tc_id] = java_code
            print(f"    [OK] {tc_id} generated.")
        else:
            print(f"    [SKIP] {tc_id} — no output.")

        if idx < len(rows) - 1:
            await asyncio.sleep(INTER_TEST_DELAY)

    return generated


# ── PHASE 2 ───────────────────────────────────────────────────────
async def review_all(generated, session_service):
    approved = []
    failed   = {}
    review_runner  = Runner(agent=review_agent,  app_name=APP_ID, session_service=session_service)
    codegen_runner = Runner(agent=codegen_agent, app_name=APP_ID, session_service=session_service)

    for idx, (tc_id, java_code) in enumerate(generated.items()):
        print(f"\n  [Review] {tc_id} ...")
        passed = False

        for iteration in range(1, MAX_REVIEW_ITER + 1):
            rev_sid = f"review_{tc_id}_iter{iteration}"
            await session_service.create_session(
                app_name=APP_ID, user_id=USER_ID, session_id=rev_sid,
                state={
                    "app_url":          APP_URL,
                    "codegen_output":   java_code,
                    "review_iteration": iteration,
                    "test_id":          tc_id,
                },
            )

            print(f"    [Iter {iteration}/{MAX_REVIEW_ITER}] Reviewing ...")
            for attempt in range(3):
                try:
                    await run_agent(review_runner, rev_sid, Content(
                        role="user",
                        parts=[Part(text=f"Review Java test for test_id={tc_id}")]
                    ))
                    break
                except _ResourceExhaustedError:
                    await asyncio.sleep(60 * (attempt + 1))

            rev_sess   = await session_service.get_session(app_name=APP_ID, user_id=USER_ID, session_id=rev_sid)
            review_raw = rev_sess.state.get("review_output", "")

            if not review_raw:
                print(f"    [Iter {iteration}] No output.")
                break

            try:
                clean        = review_raw.strip().replace("```json","").replace("```","").strip()
                verdict_data = json.loads(clean)
            except Exception:
                print(f"    [Iter {iteration}] Bad JSON.")
                break

            verdict    = verdict_data.get("verdict", "FAIL")
            issues     = verdict_data.get("issues", [])
            fixed_code = verdict_data.get("fixed_code")

            if verdict == "PASS":
                print(f"    [Iter {iteration}] PASS ✓")
                approved.append(tc_id)
                passed = True
                break

            print(f"    [Iter {iteration}] FAIL — {issues}")

            if iteration >= MAX_REVIEW_ITER:
                print(f"    MAX iterations for {tc_id}.")
                break

            if fixed_code:
                java_code = fixed_code
                save_java_test(tc_id, java_code)
            else:
                patch_sid = f"patch_{tc_id}_iter{iteration}"
                await session_service.create_session(
                    app_name=APP_ID, user_id=USER_ID, session_id=patch_sid,
                    state={
                        "app_url":         APP_URL,
                        "codegen_output":  java_code,
                        "review_feedback": issues,
                        "test_id":         tc_id,
                    },
                )
                for attempt in range(3):
                    try:
                        await run_agent(codegen_runner, patch_sid, Content(
                            role="user",
                            parts=[Part(text=f"Fix issues in test_id={tc_id}: {json.dumps(issues)}")]
                        ))
                        break
                    except _ResourceExhaustedError:
                        await asyncio.sleep(60 * (attempt + 1))

                patch_sess = await session_service.get_session(app_name=APP_ID, user_id=USER_ID, session_id=patch_sid)
                java_code  = patch_sess.state.get("codegen_output", java_code)

            await asyncio.sleep(5)

        if not passed:
            failed[tc_id] = java_code

        if idx < len(generated) - 1:
            await asyncio.sleep(INTER_TEST_DELAY)

    return approved, failed


# ── PIPELINE ──────────────────────────────────────────────────────
async def run_pipeline():
    print("=" * 60)
    print("  Java Selenium ADK Pipeline")
    print("=" * 60)

    print(f"\n[Init] Crawling {APP_URL} ...")
    locators_json = await crawl_locators(APP_URL, force_recrawl=True)
    n = len(json.loads(locators_json)["elements"])
    print(f"[Init] {n} elements found.")

    reload_tree()
    print("[Init] Locator tree ready.")

    rows = parse_test_cases(CSV_PATH)
    print(f"[Init] {len(rows)} test cases parsed.")

    session_service = InMemorySessionService()
    setup_maven_project()

    print("\n" + "="*40)
    print("  PHASE 1 — Generating")
    print("="*40)
    generated = await codegen_all(rows, session_service)
    print(f"\n[Phase 1] {len(generated)}/{len(rows)} generated.")

    if not generated:
        print("[Abort] Nothing generated.")
        return

    print("\n" + "="*40)
    print("  PHASE 2 — Reviewing")
    print("="*40)
    approved, failed = await review_all(generated, session_service)

    print("\n" + "="*40)
    print("  RESULTS")
    print("="*40)
    print(f"  Approved : {len(approved)} — {approved}")
    print(f"  Failed   : {len(failed)}  — {list(failed.keys())}")

    if approved:
        run_maven_tests()
    else:
        print("\n[Skip Maven] No tests approved.")

    print("\n[Done]")


POM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>selenium.tests</groupId>
  <artifactId>generated-tests</artifactId>
  <version>1.0</version>
  <properties>
    <maven.compiler.source>17</maven.compiler.source>
    <maven.compiler.target>17</maven.compiler.target>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.seleniumhq.selenium</groupId>
      <artifactId>selenium-java</artifactId>
      <version>4.20.0</version>
    </dependency>
    <dependency>
      <groupId>org.testng</groupId>
      <artifactId>testng</artifactId>
      <version>7.10.2</version>
      <scope>test</scope>
      <exclusions>
        <exclusion>
          <groupId>xml-apis</groupId>
          <artifactId>xml-apis</artifactId>
        </exclusion>
      </exclusions>
    </dependency>
    <dependency>
      <groupId>io.github.bonigarcia</groupId>
      <artifactId>webdrivermanager</artifactId>
      <version>5.8.0</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <version>3.2.5</version>
        <configuration>
          <includes>
            <include>**/Test_*.java</include>
          </includes>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>"""


if __name__ == "__main__":
    try:
        asyncio.run(run_pipeline())
    except KeyboardInterrupt:
        print("\n[Stopped]")