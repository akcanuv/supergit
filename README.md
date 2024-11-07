supergit
The database of the future.

## Overview

Supergit is an intelligent file organizer that helps manage and organize files within a repository using advanced AI capabilities. It leverages the Anthropic API to provide contextual file organization and management.

## Features

- **Anthropic API Integration**: Utilizes the Anthropic API for intelligent file organization and context management.
- **Contextual File Analysis**: Analyzes file content and user instructions to determine the best directory and filename.
- **Recursive Context Collection**: Collects context data from `.supergit.yaml` files across directories.
- **File Placement and Commit**: Moves files to appropriate directories and commits changes to the Git repository.
- **Supergit Initialization**: Initializes directories with `.supergit.yaml` files and sets up a Git repository.
- **Reindexing**: Updates file indexes in `.supergit.yaml` files.
- **Natural Language Query**: Finds files based on natural language queries.

## Requirements

- Python 3.6+
- Git
- Anthropic API Key (set in the `ANTHROPIC_API_KEY` environment variable)

## Installation

1. Clone the repository.
2. Set your Anthropic API key:
   ```
   export ANTHROPIC_API_KEY='your_api_key_here'
   ```

## Usage

### Initialize Supergit

To initialize a supergit repository:

```
python supergit.py init --dir /path/to/root
```

### Add a File

To add a file to the supergit repository:

```
python supergit.py add --file /path/to/file --dir /path/to/root
```

### Reindex Directories

To reindex the supergit directories:

```
python supergit.py reindex --dir /path/to/root
```

### Query Files

To query files in the supergit repository:

```
python supergit.py query --dir /path/to/root "your query here"
```

## License

This project is licensed under the MIT License.