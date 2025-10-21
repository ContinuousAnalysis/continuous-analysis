import sys
from git import Repo
import pandas as pd
from collections import OrderedDict
import csv
import os
from track_commit_changes import track_changes


# Get the project path and sha of the current commit from the command line
# Usage: python track_commit_changes.py <repo_path> <current_commit_sha>
repo_path = sys.argv[1]
current_sha = sys.argv[2]

# Get the parent sha of the current commit
# This allows us to compare the current commit with its immediate predecessor
repo = Repo(repo_path)
commit = repo.commit(current_sha)
parent_sha = commit.parents[0].hexsha if commit.parents else None

# Print the project info for debugging
print(f"Project path: {repo_path}")
print(f"Current SHA: {current_sha}")
print(f"Parent SHA: {parent_sha}")

# Declare variables for whether first time running the script
first_time_running = False

# Read the over_time csv file
df = pd.read_csv("continuous_analysis_over_time_results.csv")

# Filter the rows where the commit_sha is the current commit
df_current_commit = df[df['commit_sha'] == current_sha]

# Get the timestamp of the current commit
timestamp = df[df['commit_sha'] == current_sha]['timestamp'].iloc[0]

# Get the coverage of the current commit
coverage = df[df['commit_sha'] == current_sha]['coverage'].iloc[0]

# Combine the violations from the current commit for both PyMOP and DyLin
pymop_value = df_current_commit[df_current_commit['algorithm'] == 'pymop']['violations_by_location'].iloc[0] if not df_current_commit[df_current_commit['algorithm'] == 'pymop'].empty else None
dylin_value = df_current_commit[df_current_commit['algorithm'] == 'dylin']['violations_by_location'].iloc[0] if not df_current_commit[df_current_commit['algorithm'] == 'dylin'].empty else None

violations_current_commit_pymop = pymop_value.split(';') if pymop_value is not None and pd.notna(pymop_value) else []
violations_current_commit_dylin = dylin_value.split(';') if dylin_value is not None and pd.notna(dylin_value) else []
violations_current_commit = violations_current_commit_pymop + violations_current_commit_dylin

# Parse each violations to a list of tuples (spec, filepath, line_num)
violations_current_commit_tuples = []
for violation in violations_current_commit:
    spec, filepath, line_num = violation.split('=')[0].split(':')
    violations_current_commit_tuples.append((spec, filepath, line_num))

# Filter the rows where the commit_sha is the parent commit
df_parent_commit = df[df['commit_sha'] == parent_sha]

# Check if there is any row in the parent commit dataframe
if df_parent_commit.empty:
    print("No parent commit found")
    first_time_running = True
else:
    # Get the violations from the parent commit
    pymop_parent_value = df_parent_commit[df_parent_commit['algorithm'] == 'pymop']['violations_by_location'].iloc[0] if not df_parent_commit[df_parent_commit['algorithm'] == 'pymop'].empty else None
    dylin_parent_value = df_parent_commit[df_parent_commit['algorithm'] == 'dylin']['violations_by_location'].iloc[0] if not df_parent_commit[df_parent_commit['algorithm'] == 'dylin'].empty else None
    
    violations_parent_commit_pymop = pymop_parent_value.split(';') if pymop_parent_value is not None and pd.notna(pymop_parent_value) else []
    violations_parent_commit_dylin = dylin_parent_value.split(';') if dylin_parent_value is not None and pd.notna(dylin_parent_value) else []
    violations_parent_commit = violations_parent_commit_pymop + violations_parent_commit_dylin

    # Parse each violations to a list of tuples (spec, filepath, line_num)
    violations_parent_commit_tuples = []
    for violation in violations_parent_commit:
        spec, filepath, line_num = violation.split('=')[0].split(':')
        violations_parent_commit_tuples.append((spec, filepath, line_num))

# Get the changes between the current and parent commit
if not first_time_running and parent_sha:
    # Get the changes between the current and parent commit
    changes = track_changes(repo_path, parent_sha, current_sha)
    print(changes)

    # Filter the violations_current_commit_tuples to only include new violations that are not in the parent commit
    violations_current_commit_tuples_filtered = []
    for violation in violations_current_commit_tuples:
        spec = violation[0]
        filepath = violation[1]
        line_num = int(violation[2])
        # If the violation is from python or site-packages, we cannot match changes, direct compare with parent commit
        if 'python3' in filepath or 'site-packages' in filepath:
            if violation not in violations_parent_commit_tuples:
                violations_current_commit_tuples_filtered.append(violation)
        else:  # If the violation is from the testing repository
            if '-pymop/' in filepath:
                filepath = filepath.split('-pymop/')[1]
            elif '-dylin/' in filepath:
                filepath = filepath.split('-dylin/')[1]
                # Remove the last 5 characters of the filepath (.orig)
                filepath = filepath[:-5]

            # Check if the filepath has been changed
            if filepath in changes['new_file_changes'].keys():
                checked_status = False
                # If the file has been changed, check if the line number is in the changed range
                for start, end in changes['new_file_changes'][filepath]:
                    if line_num >= start and line_num <= end:
                        violations_current_commit_tuples_filtered.append(violation)
                        checked_status = True
                        break
                # If the line number is not in the changed range, check if the violation is in the parent commit
                if not checked_status:

                    # Declare a variable to check if the violation is in the parent commit
                    violation_in_parent_commit = False

                    # Get the old filepath
                    if changes['renames'].get(filepath, None) is not None:
                        old_filepath = changes['renames'][filepath]
                    else:
                        old_filepath = filepath

                    # Iterate through all the violations in the parent commit
                    for violation_parent in violations_parent_commit_tuples:
                        # If the filepath matched
                        if old_filepath in violation_parent[1]:

                            # Get the offseted line number
                            offseted_line_num = int(violation_parent[2])
                            sorted_start_lines = sorted(changes['offsets'][filepath].keys())
                            for i in range(len(sorted_start_lines)):
                                if int(violation_parent[2]) < sorted_start_lines[i]:
                                    if i != 0:
                                        offseted_line_num = offseted_line_num + changes['offsets'][filepath][sorted_start_lines[i-1]]
                                    break
                                if int(violation_parent[2]) >= sorted_start_lines[i] and i == len(sorted_start_lines) - 1:
                                    offseted_line_num = offseted_line_num + changes['offsets'][filepath][sorted_start_lines[i]]

                            # Check if the offseted line number matched the line number of the current commit
                            if offseted_line_num == line_num and spec == violation_parent[0]:
                                violation_in_parent_commit = True
                                break
                    
                    # If the violation is not in the parent commit, add it to the filtered list
                    if not violation_in_parent_commit:
                        violations_current_commit_tuples_filtered.append(violation)

            # If the file has not been changed, check if the violation is in the parent commit directly
            else:
                if violation not in violations_parent_commit_tuples:
                    violations_current_commit_tuples_filtered.append(violation)

    # Convert the filtered violations to a string
    violations_current_commit_filtered = []
    for violation in violations_current_commit_tuples_filtered:
        violations_current_commit_filtered.append(f"{violation[0]}:{violation[1]}:{violation[2]}")

# If the parent commit is not found, set the parent commit to an empty string and the filtered violations to an empty list
else:
    parent_sha = ''
    violations_parent_commit = []
    violations_current_commit_filtered = []
    for violation in violations_current_commit_tuples:
        violations_current_commit_filtered.append(f"{violation[0]}:{violation[1]}:{violation[2]}")
    print("No parent commit found or first time running. No filtering done.")

# Store the filtered violations in a new csv file
line = OrderedDict({
    'timestamp': timestamp,
    'coverage': coverage,
    'current_commit_sha': current_sha,
    'parent_commit_sha': parent_sha,
    'num_new_violations': len(violations_current_commit_filtered),
    'new_violations': ';'.join(violations_current_commit_filtered),
    'num_current_violations': len(violations_current_commit),
    'current_violations': ';'.join(violations_current_commit),
    'num_parent_violations': len(violations_parent_commit),
    'parent_violations': ';'.join(violations_parent_commit),
})

# Check if continuous_analysis_over_time_violations_filtered.csv exists
file_exists = os.path.isfile('continuous_analysis_over_time_violations_filtered.csv')

# Append the results to the continuous_analysis_over_time_violations_filtered.csv file
print("\n====== APPENDING TO RESULTS OVER TIME ======\n")
print(f'appending to continuous_analysis_over_time_violations_filtered.csv')

# Append the line to the csv file
with open('continuous_analysis_over_time_violations_filtered.csv', 'a') as f:
    writer = csv.DictWriter(f, line.keys())
    # Write header only if file doesn't exist
    if not file_exists:
        writer.writeheader()
    # Write the line
    try:
        writer.writerow(line)
    except Exception as e:
        print('could not write line:', line.keys(), str(e))

print('appended to continuous_analysis_over_time_violations_filtered.csv')