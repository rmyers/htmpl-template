# htmpl-template

Starter project for htmpl, this is based off of copier but includes a UI to manage the installed options. The available options include:

- Auth (login and registration pages)
- Themes
- Database services

The components you copy in are yours to change, we have based the desgin of this component library on `shadcn` where you 'install' the components you want and they are copied into your project. That way if you want to change anything, you simply modify the code to your liking.

If and when the base template changes you will be able to upgrade to the new one. Copier handles applying changes to the templated files and gives options to overwrite or produce a diff and allow you to apply the changes via git conflict resolution.

## Getting Started

First you will need to install `uv` go get it now if you don't have it: https://docs.astral.sh/uv/

> [!NOTE]
> Make sure you are not in an existing project folder before running this command.

Find a good location to install your project:

```bash
$ uvx htmpl init .
Installed 24 packages in 11ms

🎤 What is your project name?
   frank
🎤 What is your Python module name?
   frank
🎤 What theme to use?
   dark

Copying from template version 0.1.0
```

The above command will create the project in a folder called `frank` that includes a Makefile to initialize and run the application.

```bash
# display the available commands:
$ make

# Runs uv sync and generates .env file for storing secrets for local dev
$ make setup

# Run the application locally
$ make dev
```

Open your browser and go to http://localhost:8000/admin/ this will allow you to view documentation on the available components and install them. Some of the components have dependencies that will need to be installed for python deps we run `uv add <package>` otherwise we'll run copier `copier upgrade --data <options.selected>`
