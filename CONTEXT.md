# Semora Project Context & Coding Standards

This document establishes the project standards, architectural conventions, and coding rules for **Semora**—an autonomous local CI/quality-gate tool. All Antigravity agents working on this repository must adhere to these standards.

---

## 1. Project Overview & Architecture
Semora is a local, autonomous CI/quality-gate system that runs when a developer attempts a git commit (or invokes it manually).

### Core Components:
*   **Git Hook Interceptor**: Catches commits and triggers the gate.
*   **BDD Spec Generator**: Analyzes changes and creates Behavior-Driven Development (BDD) test specifications.
*   **Sandbox Executor**: Runs generated BDD specs in a secure sandbox.
*   **Security Modeler**: Performs STRIDE threat modeling on codebase changes.
*   **Reporting & Sync**: Outputs to the terminal and syncs with a Firebase-hosted dashboard.
*   **Frontend**: Firebase-hosted web dashboard displaying CI runs, threat models, and test statuses.

---

## 2. Python Coding Standards

*   **Type Hinting**: All Python functions and methods must have complete type signatures (argument and return types).
*   **Secrets & API Keys**:
    *   **NEVER** hardcode secrets, API keys, credentials, or configuration values.
    *   Always load configuration from environment variables.
    *   Use `python-dotenv` to load local `.env` files.
*   **Exception Handling**:
    *   Do **NOT** use bare `except:` clauses.
    *   Prefer explicit, narrow exception types (e.g., `except ValueError:`, `except FileNotFoundError:`).
*   **Module Documentation**: Every Python module (`.py` file) must begin with a docstring explaining its exact role and position in the Semora architecture.
*   **Style Guide**: Follow PEP 8 guidelines strictly.

---

## 3. Frontend (React) Standards

*   **Component Architecture**: Use functional React components with hooks.
*   **No Class Components**: Do **NOT** use class-based React components.
*   **Styling**: Use Vanilla CSS for styling (or TailwindCSS if explicitly configured/requested). Keep styling modular.

---

## 4. Testing Standards

*   **Test Coverage**: All new features, utilities, and components must ship with at least one corresponding unit or integration test.
*   **Test Framework**: Use `pytest` for Python and standard testing frameworks (e.g., Jest/React Testing Library) for Frontend.
*   **Sandbox Independence**: Tests must run without modifying the host system.

---

## 5. Development Conventions

*   **Skeleton Code**: When scaffolding structures or templates, write clean skeleton code with explicit `# TODO` or `// TODO` comments. Do not guess or stub business logic.
*   **File Naming**: Use `snake_case` for Python files and directories, and `PascalCase` for React component files.
