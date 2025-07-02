import csv
import os
import sys
import requests
from collections import defaultdict


"""
Scripts to track new violations found in a new run of the tracking projetcs.

The script will:
1. Read the CSV file and group data by project (only changed projects)
2. For each project, get the two most recent runs
3. Find new violations
4. Create GitHub issues for new violations
"""


def get_run_data(csv_file, changed_projects):
    """
    Read the CSV file and group data by project (only changed projects).
    
    Args:
        csv_file (str): Path to the CSV file
        changed_projects (list): List of changed projects
    
    Returns:
        dict: Dictionary with project as key and list of runs data as value
    """
    # Read the csv file and group data by project (only changed projects)
    runs = defaultdict(list)
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        # Because the results are appended by time, the last run is the most recent and so on
        for row in reader:
            project = row.get('project', '')
            if project in changed_projects:
                runs[project].append(row)
    
    # Return the changed projects runs results
    return runs


def parse_violations_by_location(violations_str):
    """
    Parse the violations_by_location string into a dictionary.
    
    Args:
        violations_str (str): String in format "spec:file:line=count;spec:file:line=count"
    
    Returns:
        list: List of spec:file:line strings
    """
    # If there are no violations, return an empty list
    if not violations_str or violations_str == 'x':
        return []
    
    # Parse the violations_by_location string into a list of spec:file:line strings
    violations = []
    for item in violations_str.split(';'):
        if '=' in item:
            spec_location_str, _ = item.rsplit('=', 1)
            violations.append(spec_location_str)
    return violations


def find_new_violations(previous_run, current_run):
    """
    Compare two runs to find new violations.
    
    Args:
        previous_run (list): List of project data from previous run
        current_run (list): List of project data from current run
    
    Returns:
        dict: Dictionary with project names as keys and new violations as values
    """
    # Create a list to store the new violations
    new_violations = []
    
    # Parse the previous run violations
    if previous_run:
        previous_violations = parse_violations_by_location(previous_run.get('violations_by_location', ''))
    else:
        previous_violations = []

    # Parse the current run violations
    current_violations = parse_violations_by_location(current_run.get('violations_by_location', ''))

    # Find new violations
    for violation in current_violations:
        if violation not in previous_violations:
            new_violations.append(violation)

    # Return the new violations
    return new_violations


def parse_timestamp(timestamp_str):
    """
    Parse timestamp from format YYYYMMDD_HHMM to readable format.
    
    Args:
        timestamp_str (str): Timestamp in format YYYYMMDD_HHMM
    
    Returns:
        str: Readable timestamp format
    """
    try:
        # Parse the timestamp: YYYYMMDD_HHMM
        date_part = timestamp_str.split('_')[0]
        time_part = timestamp_str.split('_')[1]
        
        # Extract components
        year = date_part[:4]
        month = date_part[4:6]
        day = date_part[6:8]
        hour = time_part[:2]
        minute = time_part[2:4]
        
        # Create readable format
        readable_timestamp = f"{year}-{month}-{day} {hour}:{minute}"
        return readable_timestamp
    except (AttributeError, IndexError, ValueError):
        # Return original if parsing fails
        return timestamp_str


def print_new_violations(project, new_violations, current_timestamp):
    """
    Print the new violations in a formatted way showing spec, file, and line.
    (Only used for debugging purposes)
    
    Args:
        new_violations (dict): New violations by location
    """
    if not new_violations:
        print("No new violations found.")
        return
    
    print("=" * 80)
    print("NEW VIOLATIONS REPORT")
    print("=" * 80)
    print(f"Generated at: {current_timestamp}")
    print()

    print(f"Project: {project}")
    print("-" * 40)
    print(f"Total new violations: {len(new_violations)}")
    print()
    
    for violation in new_violations:
        spec, file, line = violation.split(':', 2)
        print(f"  {spec}: {file}:{line}")
    print()


def create_github_issue(project, new_violations, current_timestamp, repo_address, github_token):
    """
    Create a GitHub issue for new violations of a project.
    
    Args:
        project (str): Project name
        new_violations (list): List of new violations in format "spec:file:line"
        current_timestamp (str): Timestamp of the run
        repo_address (str): GitHub repository address
        github_token (str): GitHub personal access token
    """
    try:
        # Parse violation components
        parsed_violations = []
        for violation in new_violations:
            spec, file_path, line_num = violation.split(':', 2)
            parsed_violations.append({
                'spec': spec,
                'file_path': file_path,
                'line_num': line_num
            })

        # Create issue title
        title = f"New PyMOP violations detected for {project} on {current_timestamp}"
        
        # Create a header for the issue
        body_header = f"""## New PyMOP Violations Detected for {project} on {current_timestamp}

**Project:** {project}
**Timestamp:** {current_timestamp}

**Total number of new violations:** {len(new_violations)}

### Summary
These violations were detected in the latest PyMOP run and were not present in the previous run.

### Required Action
Please review the code at the specified locations and address each violation according to the corresponding PyMOP specification. You can find detailed specifications at: https://github.com/allrob23/pymop-artifacts-rv/tree/main/pymop/specs-new

---

"""
        
        # Build the violations section
        body_violations = ""
        for i, violation in enumerate(parsed_violations, start=1):
            body_violations += f"""**Violation {i} of {len(parsed_violations)}:**
**Specification:** {violation['spec']}
**File:** `{violation['file_path']}`
**Line:** {violation['line_num']}

---

"""
        # Add a footer to the issue
        body_end = "*This issue was automatically generated by the PyMOP violation tracker.*"
        
        # Combine all body parts
        body = body_header + body_violations + body_end

        # GitHub API configuration
        url = f"https://api.github.com/repos/{repo_address}/issues"
        
        # Headers for GitHub API
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
        
        # Issue data
        issue_data = {
            'title': title,
            'body': body
        }
        
        # Create the issue
        response = requests.post(url, headers=headers, json=issue_data)
        
        # If the issue is created successfully, print the issue url
        if response.status_code == 201:
            issue_url = response.json()['html_url']
            print(f"Created issue: {issue_url} for {project} - {current_timestamp}")
        else:
            print(f"Failed to create issue: {issue_url} for {project} - {current_timestamp}")
            print(f"Details: {response.status_code} - {response.text}")

    # If there is an error, print the error
    except Exception as e:
        print(f"Error creating issue: {str(e)}")


def create_issues_for_new_violations(project, new_violations, current_timestamp, repo_address, github_token):
    """
    Create GitHub issues for all new violations in a project.
    
    Args:
        project (str): Project name
        new_violations (list): List of new violations
        current_timestamp (str): Timestamp of the run
        repo_address (str): GitHub repository address
        github_token (str): GitHub personal access token
    """
    # If there are no new violations, return
    if not new_violations:
        return
    
    # Create a GitHub issue for the new violations
    print(f"Creating GitHub issue for {len(new_violations)} new violations...")
    create_github_issue(project, new_violations, current_timestamp, repo_address, github_token)
    print(f"Created GitHub issue for {len(new_violations)} new violations.")


def main():
    """Main function to track new violations."""

    # Get the csv and changed_projects_file files
    csv_file = 'pymop_over_time_results.csv'
    changed_projects_file = 'changed_projects.txt'

    # Check if the csv and changed_projects_file files exist
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found")
        sys.exit(1)
    
    if not os.path.exists(changed_projects_file):
        print(f"Error: {changed_projects_file} not found")
        sys.exit(1)

    # GitHub configuration
    github_token = "x"
    repo_address = "Stephen0512/pymop-shadow-observer"

    # Read the changed projects from the changed_projects_file and store in a list
    with open(changed_projects_file, 'r') as f:
        changed_projects = f.read().splitlines()
    
    # Get run data
    runs = get_run_data(csv_file, changed_projects)
    
    # Check if there is data in the csv file
    if not runs:
        print(f"No data found in {csv_file}")
        sys.exit(1)

    # For each project, get the two most recent runs
    for project, runs in runs.items():
        # Get the two most recent runs
        current_run = runs[-1]
        if len(runs) > 1:
            previous_run = runs[-2]
        else:
            previous_run = None

        # Get the timestamp of the current run
        current_timestamp = current_run.get('timestamp', '')
        current_timestamp = parse_timestamp(current_timestamp)

        # Find new violations
        new_violations = find_new_violations(previous_run, current_run)

        # Print the new violations
        # print_new_violations(project, new_violations, current_timestamp)
        
        # Create GitHub issues if token is available and violations found
        if github_token and new_violations:
            create_issues_for_new_violations(project, new_violations, current_timestamp, repo_address, github_token)

if __name__ == "__main__":
    main()
