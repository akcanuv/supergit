# supergit.py

import os
import sys
import git
import yaml
import json
import base64
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import anthropic

# Set your Anthropic API key
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY:
    print("Please set your Anthropic API key in the ANTHROPIC_API_KEY environment variable.")
    sys.exit(1)

# Function to get a response from the Anthropic API using the anthropic package
def get_anthropic_response(system_prompt: str, messages: list):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response = client.beta.messages.create(
            model="claude-3-5-sonnet-20241022",
            betas=["pdfs-2024-09-25"],
            max_tokens=8000,
            system=system_prompt,
            messages=messages
        )
        # Extract the assistant's reply
        assistant_reply = ''
        for item in response.content:
            if item.type == 'text':
                assistant_reply += item.text
        return assistant_reply
    except Exception as e:
        print(f'Error in get_anthropic_response: {e}')
        return None

def read_supergit_context(directory: str) -> Dict[str, Any]:
    """
    Reads the .supergit.yaml file in the given directory to get context.
    """
    context_file = os.path.join(directory, '.supergit.yaml')
    if os.path.exists(context_file):
        with open(context_file, 'r') as f:
            data = yaml.safe_load(f)
            return data
    else:
        return {}

def get_combined_supergit_contexts(root_dir: str) -> Dict[str, Any]:
    """
    Recursively collects context data from all .supergit.yaml files starting from the root directory.
    """
    combined_context = {}
    for root, dirs, files in os.walk(root_dir):
        if '.supergit.yaml' in files:
            context = read_supergit_context(root)
            combined_context[root] = context
    return combined_context

def analyze_file(file_path: str, root_dir: str, user_message: str = None) -> Dict[str, Any]:
    """
    Analyzes the file content or user-provided message to determine the correct directory and filename.
    """
    combined_context = get_combined_supergit_contexts(root_dir)
    if not combined_context:
        print("No .supergit.yaml files found. Please set up your project structure first.")
        sys.exit(1)

    file_content = ""
    file_name = os.path.basename(file_path)
    file_extension = os.path.splitext(file_name)[1].lower()

    if user_message:
        file_content = user_message
    else:
        if file_extension == '.pdf':
            with open(file_path, 'rb') as f:
                file_content = base64.b64encode(f.read()).decode('utf-8')
        else:
            with open(file_path, 'r', errors='ignore') as f:
                file_content = f.read()

    # Prepare the prompt
    prompt_data = {
        "file_name": file_name,
        "file_content": file_content[:1000],  # Limit to first 1000 characters or base64 string
        "supergit_context": combined_context
    }

    system_prompt = "You are an AI assistant that helps organize files in a supergit repository."
    messages = [
        {
            "role": "user",
            "content": f"""
Given the combined .supergit.yaml contexts and the file content, determine the most appropriate directory within the supergit repository to place the file, and suggest a systematic filename according to the directory's naming conventions. The response should be in YAML format with 'directory', 'filename', 'justification' and 'updated .supergit.yaml' contents for that directory with no additional explanation.

{yaml.dump(prompt_data)}
"""
        }
    ]

    assistant_reply = get_anthropic_response(system_prompt, messages)

    # Parse the YAML response
    print(assistant_reply)
    try:
        result = yaml.safe_load(assistant_reply.strip())
        return result
    except yaml.YAMLError:
        print("Failed to parse the response from the AI assistant.")
        sys.exit(1)

def update_supergit_yaml(directory: str):
    """
    Updates the .supergit.yaml file in the given directory to reflect current files and directories.
    """
    entries = []
    with os.scandir(directory) as it:
        for entry in it:
            if entry.name == '.supergit.yaml' or entry.name.startswith('.'):
                continue
            entries.append(entry.name)

    context_file = os.path.join(directory, '.supergit.yaml')
    context = read_supergit_context(directory)
    context['entries'] = entries

    with open(context_file, 'w') as f:
        yaml.dump(context, f)

def place_file(file_path: str, root_dir: str, target_directory: str, target_filename: str):
    """
    Moves the file to the target directory with the target filename and commits the change.
    """
    # Ensure target_directory is relative to root_dir
    target_directory_rel = os.path.relpath(target_directory, root_dir)
    full_target_directory = os.path.join(root_dir, target_directory_rel)
    if not os.path.exists(full_target_directory):
        os.makedirs(full_target_directory)

    new_path = os.path.join(full_target_directory, target_filename)
    os.rename(file_path, new_path)

    # Update .supergit.yaml files
    update_supergit_yaml(full_target_directory)

    # Initialize Git repository at the root directory if not already initialized
    try:
        repo = git.Repo(root_dir)
    except git.InvalidGitRepositoryError:
        repo = git.Repo.init(root_dir)

    # Compute paths relative to the repo root directory
    relative_new_path = os.path.relpath(new_path, root_dir)
    relative_yaml_path = os.path.relpath(os.path.join(full_target_directory, '.supergit.yaml'), root_dir)

    # Stage and commit changes using relative paths
    repo.git.add(relative_new_path)
    repo.git.add(relative_yaml_path)
    repo.index.commit(f"Added {target_filename} to {target_directory_rel}")

def reindex_supergit(root_dir: str):
    """
    Verifies and updates the file indexes in each .supergit.yaml file recursively.
    """
    for root, dirs, files in os.walk(root_dir):
        if '.supergit.yaml' in files:
            update_supergit_yaml(root)

def find_files_by_query(root_dir: str, directory: str, query: str):
    """
    Finds files based on a natural language query within a directory.
    """
    # Collect files and contexts
    combined_context = get_combined_supergit_contexts(root_dir)
    file_descriptions = ""
    for dir_path, context in combined_context.items():
        if not dir_path.startswith(os.path.join(root_dir, directory)):
            continue
        entries = context.get('entries', [])
        for entry in entries:
            entry_path = os.path.join(dir_path, entry)
            if os.path.isfile(entry_path):
                file_info = f"File: {entry_path}\n"
                try:
                    with open(entry_path, 'r', errors='ignore') as f:
                        content = f.read(500)  # Read first 500 characters
                    file_info += f"Content Preview:\n{content}\n\n"
                except Exception:
                    continue
                file_descriptions += file_info

    if not file_descriptions:
        return "No files found matching the query."

    system_prompt = "You are an AI assistant that helps find files in a supergit repository."
    messages = [
        {
            "role": "user",
            "content": f"""
Given the user's query and the available files, provide the paths of files that best match the query. If the query asks for general information, provide a concise and accurate natural language response without any additional explanations.

User Query: {query}

Available Files:
{file_descriptions}
"""
        }
    ]

    assistant_reply = get_anthropic_response(system_prompt, messages)
    result = assistant_reply.strip()
    return result


def initialize_supergit(root_dir: str):
    """
    Initializes the supergit directories by creating or updating .supergit.yaml files
    with directory information and updates from the LLM.
    """
    # First, traverse the directory tree and collect initial data
    directory_data = {}  # key: directory path, value: data dict

    for dirpath, dirnames, filenames in os.walk(root_dir):
        entries = [name for name in dirnames + filenames if not name.startswith('.') and name != '.supergit.yaml']
        directory_name = os.path.basename(dirpath)
        data = {
            'directory_name': directory_name,
            'entries': entries,
            'description': '',  # Will be updated by LLM
            'remarks': ''       # Will be updated by LLM
        }

        # Save the data
        directory_data[dirpath] = data

    # Now, prepare the data for the LLM
    all_directories = []

    for dirpath, data in directory_data.items():
        relative_dirpath = os.path.relpath(dirpath, root_dir)
        data_with_relpath = data.copy()
        data_with_relpath['path'] = relative_dirpath
        all_directories.append(data_with_relpath)

    # Prepare the prompt for the LLM
    prompt_data = {
        "directories": all_directories
    }

    system_prompt = "You are an AI assistant that helps organize a supergit repository."
    user_prompt = f"""
Given the following directory information, update the 'description' and 'remarks' for each directory.

For each directory:
- Update the 'description' key to provide a short description of the directory based on existing files and directory name.
- If applicable, update the 'remarks' key with any specific naming conventions being followed in the directory or other information.

Provide the updated '.supergit.yaml' contents for each directory as a JSON array, where each item has 'path' and 'supergit_yaml' keys.
Only provide the JSON array without markdown formatting as response without any additional explanation.

Example:

[
  {{
    "path": "path/to/directory",
    "supergit_yaml": {{
      "directory_name": "directory",
      "description": "A short description.",
      "entries": [...],
      "remarks": "Any specific naming conventions."
    }}
  }},
  ...
]

Directories:

{json.dumps(prompt_data)}
"""

    messages = [
        {
            "role": "user",
            "content": user_prompt
        }
    ]

    assistant_reply = get_anthropic_response(system_prompt, messages)
    print(assistant_reply)
    # Now, parse the assistant's reply
    try:
        updated_directories = json.loads(assistant_reply)
    except json.JSONDecodeError:
        print("Failed to parse the response from the AI assistant.")
        sys.exit(1)

    # Now, update the .supergit.yaml files
    for item in updated_directories:
        path = item.get('path')
        supergit_yaml_content = item.get('supergit_yaml')
        if not path or not supergit_yaml_content:
            continue
        full_dir_path = os.path.join(root_dir, path)
        supergit_yaml_path = os.path.join(full_dir_path, '.supergit.yaml')
        with open(supergit_yaml_path, 'w') as f:
            yaml.dump(supergit_yaml_content, f)

def main():
    """
    Main function to handle command-line arguments.
    """
    parser = argparse.ArgumentParser(description='Supergit: An intelligent file organizer.')
    parser.add_argument('--add', '-a', help='Path to the file to add.')
    parser.add_argument('--instruct', '-i', help='Additional instruction for the file.', default=None)
    parser.add_argument('--init', action='store_true', help='Initialize the supergit directories.')
    parser.add_argument('--reindex', action='store_true', help='Reindex the supergit directories.')
    parser.add_argument('--dir', help='Directory to use as root or to query.')
    parser.add_argument('query', nargs='?', help='Natural language query.')

    args = parser.parse_args()

    # Determine the root directory
    root_dir = args.dir if args.dir else '.'

    if args.add:
        file_path = args.add
        if not os.path.exists(file_path):
            print("File does not exist.")
            sys.exit(1)
        result = analyze_file(file_path, root_dir, args.instruct)
        target_directory = result.get('directory')
        target_filename = result.get('filename')
        if not target_directory or not target_filename:
            print("Could not determine the target directory or filename.")
            sys.exit(1)
        place_file(file_path, root_dir, target_directory, target_filename)
        print(f"File placed in {os.path.join(root_dir, target_directory)} as {target_filename} and committed.")


    elif args.init:
        initialize_supergit(root_dir)
        print("Initialized supergit directories.")

    elif args.reindex:
        reindex_supergit(root_dir)
        print("Reindexed supergit directories.")

    elif args.query:
        if not args.dir:
            print("Please specify the directory to query using --dir.")
            sys.exit(1)
        result = find_files_by_query(root_dir, args.dir, args.query)
        print(f"\n{result}")

    else:
        parser.print_help()

if __name__ == '__main__':
    main()