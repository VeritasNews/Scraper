# Project Standards

## 1. Code Standards

### 1.1 General Guidelines
- Write clear and simple code. If someone else reads it, they should easily understand it.
- Use descriptive names for variables, functions, and classes. Avoid abbreviations.
- Keep functions small (try to limit them to 20-30 lines).
- Use consistent indentation (2 or 4 spaces, based on the language).
- Avoid duplicating code; reuse functions where possible.
- Comment only when necessary. Write code that is self-explanatory, but use comments to clarify complex logic.

### 1.2 Consistency
- Be consistent with style and conventions, even if they are not your personal preference.
- Use linters and formatters to ensure consistent style across the codebase (e.g., ESLint for JavaScript, flake8 for Python).

### 1.3 Language-Specific Guidelines
- **JavaScript/React**: 
  - Follow simple conventions like using `const` for constants, and `let` for variables that will change.
  - Use arrow functions for anonymous functions.
- **Python**:
  - Follow basic PEP 8 guidelines, but focus on readability over strict adherence to every rule.
- **SQL**: Write queries in a readable, consistent format. Each clause (e.g., `SELECT`, `WHERE`) should be on its own line.

### 1.4 Error Handling
- Always handle potential errors. Use `try/catch` in JavaScript and `try/except` in Python for critical operations.
- Display user-friendly error messages, but don't expose sensitive information (e.g., stack traces).

### 1.5 Keep it Simple
- Don't overcomplicate solutions. Always aim for the simplest solution that works.
- Avoid using unnecessary libraries or tools; only use what’s essential for the project.


## 2. Commit and Versioning Standards

### 2.1. Commit Message Guidelines

- Use the following format for commit messages:
  - **Type**: A short description of the change. Use one of the following:
    - `feat`: New feature
    - `fix`: Bug fix
    - `docs`: Documentation changes
    - `style`: Code style changes (e.g., formatting, indentation)
    - `refactor`: Code refactoring
    - `test`: Adding or modifying tests
    - `chore`: Routine tasks or maintenance

    Example:
    ```
    feat: add search functionality to articles
    ```

## 3. Pull Request (PR) Standards

- All pull requests must be reviewed by at least one team member before merging.
- PR descriptions should clearly explain the changes made, the problem they solve, and any important context.
- Ensure that the PR title and description align with the issue or task being addressed.
- Use GitHub labels to categorize the PR (e.g., `bug`, `feature`, `documentation`).

---

## 4. Testing Standards

### 4.1 General Guidelines
- **Test early, test often**: Start writing tests as soon as possible and run them regularly.
- **Keep tests simple**: Write tests that check only one thing at a time.
- **Test for expected and unexpected behavior**: Make sure your tests cover both normal and edge cases.

### 4.2 Types of Tests
- **Unit Tests**: Write unit tests for individual functions or components to ensure they work as expected.
- **Integration Tests**: Check that different parts of the system work together correctly (e.g., database, API, UI).
- **End-to-End (E2E) Tests**: Simulate real user scenarios to ensure everything works from start to finish.

### 4.3 Naming Conventions
- Name your test functions clearly so they describe what the test does. For example:
  - `shouldAddUserSuccessfully`
  - `shouldShowErrorWhenInvalidInput`
  - `shouldReturn404ForNonexistentPage`

### 4.4 Test Automation
- (Optional) Use automated tests where possible to save time and avoid human error. 
- (Optional) Use CI/CD tools to run tests automatically on every pull request (e.g., GitHub Actions, CircleCI).

### 4.5 Test Coverage
- Aim for **high coverage**, but don’t obsess over 100%. Focus on the critical parts of the application.
- Ensure that your tests cover important user interactions and edge cases.

### 4.6 Fixing Failing Tests
- If a test fails, fix the code **or** the test, but never ignore it.
- After fixing, run all tests again to ensure nothing else is broken.

## 5. Documentation Standards

- Maintain clear and up-to-date documentation:
  - Use `README.md` for general project information.
- Inline code comments should explain the "why" rather than the "what."

---

## 6. Workflow and Task Management

- **Task Tracking**: All tasks and progress are managed via Notion.
- **Weekly Meetings**: Team members meet weekly to discuss progress, blockers, and next steps.
- **Version Control**: Use Git and GitHub for code tracking.

---

## 7. Tools and Integrations

- **Version Control**: Git (hosted on GitHub).
- **Task Tracking**: Notion for task and progress management.
- **(Optional) CI/CD**: GitHub Actions for automated testing and deployment.
- **(Optional) Code Reviews**: Use GitHub’s review and approval system.

---

## 8. Licensing and Attribution

- This project adheres to the [MIT License](LICENSE).  
- Ensure all third-party tools and libraries used comply with their respective licenses.

---

## 9. Security Best Practices

- Avoid hardcoding sensitive information like API keys or passwords.
- Use environment variables for configuration.
- Regularly update dependencies to fix vulnerabilities.

---

By adhering to these standards, we aim to foster a productive, efficient, and collaborative development environment.
