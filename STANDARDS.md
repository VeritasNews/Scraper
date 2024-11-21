# Project Standards

## 1. Code Standards

### 1.1. General Coding Guidelines

- All code must be clean, readable, and maintainable.
- Write meaningful variable, function, and class names.
- Keep functions/methods small, ideally under 50 lines.
- Follow consistent indentation and spacing throughout the codebase.

### 1.2. Language-Specific Guidelines

- **JavaScript/React**: Follow the [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript). Use linters like `eslint` and formatters like `prettier`.
- **Python**: Follow [PEP 8](https://pep8.org/). Use `flake8` or `pylint` for linting and `black` for code formatting.
- **SQL**: Write clear and efficient queries, following proper indentation for readability.

---

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

- All new features or bug fixes must include corresponding unit tests.
- Use the following frameworks and tools:
  - **Python**: `unittest` or `pytest`
  - **JavaScript**: `Jest` or `React Testing Library`
- Write clear and concise test cases covering edge cases.
- Ensure test coverage does not decrease for the project.

---

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
