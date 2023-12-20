# Contributing to Plejd plejd-mqtt-ha

Thanks for considering contributing to the project!

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Getting Started](#getting-started)
  - [Setting up the environment](#setting-up-the-environment)
- [Coding Standards](#coding-standards)
- [Pull Requests](#pull-requests)
  - [Code linting](#code-linting)
- [Pre-commit Hooks](#pre-commit-hooks)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Getting Started

Before you start contributing, please review these guidelines:

1. Check out the project's [issue tracker](https://github.com/ha-enthus1ast/plejd-mqtt-ha/issues) and [pull requests](https://github.com/ha-enthus1ast/plejd-mqtt-ha/pulls) to see if someone else has already reported and/or fixed the issue you're facing.

2. If not, open a new issue. Please provide as much information as possible to help the maintainers understand and solve the problem.

3. If you think you can fix or implement it yourself, fork the project and submit a pull request. Please make sure to follow the coding standards and test your changes.

### Setting up the environment

This project uses [Poetry](https://python-poetry.org/) for dependency management. If you don't have Poetry installed, you can install it with:

```bash
curl -sSL https://install.python-poetry.org | python -
```

Once Poetry is installed, you can set up your environment with:

```bash
poetry install
```
This will create a virtual environment and install all the necessary dependencies so you can start contributing to the project.
To spawn a shell within the environment:

```bash
poetry shell
```

## Coding Standards

Please ensure your code adheres to the following standards:

- Follow the style used in the existing codebase.
- Include comments in your code where necessary.
- Write tests for your changes.

## Pull Requests

When submitting a pull request:

- Include a description of what your change intends to do.
- Be sure to link to the issue that your change is related to, if applicable.
- Make sure your pull request includes tests.

### Code linting
This project uses [Mega-Linter](https://nvuillam.github.io/mega-linter/), an open-source linter that analyzes consistency and quality of your code.

Before submitting a pull request, please ensure your changes do not introduce any new linting errors. You can run Mega-Linter locally to check your code before committing:

```bash
npx mega-linter-runner --flavor python
```
This command will run Mega-Linter against your local codebase and report any issues it finds.

## Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to ensure that code committed to the repository meets certain standards and passes linting tests. Before you can commit changes to the repository, your changes will be automatically checked by pre-commit hooks.

To install the pre-commit hooks, you need to have pre-commit installed on your local machine. You can install it using pip:

```bash
pip install pre-commit
```

Once pre-commit is installed, you can install the pre-commit hooks with:

```bash
pre-commit install
```

Now, the hooks will automatically run every time you commit changes to the repository. If the hooks find issues, your commit will be blocked until you fix the issues.

Looking to your contributions. Thank you!
