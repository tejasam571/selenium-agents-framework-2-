project/
├── main.py                          ← pipeline entry point
├── .env                             ← GOOGLE_API_KEY
├── requirements.txt
├── data/
│   └── test_cases_sause.csv         ← input test cases
│
├── agents/
│   ├── __init__.py
│   ├── root_agent.py                ← chat assistant (adk web)
│   ├── codegen_agent.py             ← generates Java Selenium code
│   └── review_agent.py              ← reviews and fixes generated code
│
├── tools/
│   ├── __init__.py                  ← exports all tools
│   ├── crawler.py                   ← crawls website → locators.json
│   ├── locator_tree.py              ← builds tree, search by keyword
│   ├── tc_parser.py                 ← parses CSV, fetches locators, builds prompt
│   ├── storage.py                   ← saves .java files
│   └── runner.py                    ← runs maven tests
│
├── storage/                         ← auto-created
│   └── locators.json                ← crawler output → loaded into tree
│
└── java_tests/                      ← auto-created (Maven project)
    ├── pom.xml
    └── src/test/java/tests/
        ├── Test_TC_001.java
        ├── Test_TC_002.java
        ├── Test_TC_003.java
        ├── Test_TC_004.java
        └── Test_TC_005.java