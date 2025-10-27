# Import necessary libraries
import os
import json
from collections import OrderedDict
from collections import Counter
import csv
from datetime import datetime
import sys
import xml.etree.ElementTree as ET
from git import Repo


dylin_spec_dict = {
             "PC-01": "InvalidComparisonAnalysis",
             "PC-02": "InvalidComparisonAnalysis",
             "PC-03": "WrongTypeAddedAnalysis",
             "PC-04": "ChangeListWhileIterating",
             "PC-05": "ItemInListAnalysis",
             "SL-01": "InPlaceSortAnalysis",
             "SL-02": "BuiltinAllAnalysis",
             "SL-03": "StringStripAnalysis",
             "SL-04": "StringConcatAnalysis",
             "SL-05": "InvalidComparisonAnalysis",
             "SL-06": "NondeterministicOrder",
             "SL-07": "RandomParams_NoPositives",
             "SL-08": "RandomRandrange_MustNotUseKwargs",
             "SL-09": "Thread_OverrideRun",
             "CF-01": "ComparisonBehaviorAnalysis",
             "ML-01": "InconsistentPreprocessing",
             "ML-02": "DataLeakage",
             "ML-03": "NonFiniteValues",
             "ML-04": "GradientExplosion",
             "TP-01": "HostnamesTerminatesWithSlash",
             "TP-02": "NLTK_regexp_span_tokenize",
             "TP-03": "Requests_DataMustOpenInBinary",
             "TP-04": "Session_DataMustOpenInBinary"}


def get_time_from_json():
    """
    Extract time information from JSON file

    Returns:
        A tuple containing the instrumentation duration, create monitor duration, and test duration
    """
    # Define the time file name
    filename = f'D-time.json'

    # Check if the time file exists
    if not os.path.isfile(filename):
        return None
    
    # Check if the time file is empty
    if os.path.getsize(filename) == 0:
        return None
    
    # Load the time JSON file
    try:
        with open(filename, 'r') as f:
            json_data = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing JSON file {filename}: {e}")
        return None

    # Get the time information from the JSON file
    instrumentation_duration = json_data.get('instrumentation_duration', 0)
    create_monitor_duration = json_data.get('create_monitor_duration', 0)
    test_duration = json_data.get('test_duration', 0)

    # Return the time information in a tuple
    return instrumentation_duration, create_monitor_duration, test_duration

def get_monitors_and_events_from_json(algorithm):
    """
    Extract monitor and event information from JSON file

    Returns:
        A tuple containing the monitor and event information
    """
    # Define the monitor and event filename
    filename = f'{algorithm}-full.json'

    # Check if the monitor and event file exists
    if not os.path.isfile(filename):
        return None
    
    # Check if the monitor and event file is empty
    if os.path.getsize(filename) == 0:
        return None
    
    # Load the monitor and event JSON file
    try:
        with open(filename, 'r') as f:
            json_data = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing JSON file {filename}: {e}")
        return None

    # Initialize the variables for the monitor and event information
    total_monitors = 0
    total_events = 0
    return_str_monitors = ""
    return_str_events = ""

    # Iterate over the monitor and event information for each spec
    for spec in json_data.keys():

        # Get the number of monitors for the spec
        num_monitors = json_data[spec]["monitors"]
        # Get the total number of events for the spec
        total_events_spec = sum(json_data[spec]["events"].values())

        # Update the return string for the monitors of the spec
        return_str_monitors += f'{spec}={num_monitors}<>'
        # Update the return string for the events of the spec
        for event, count in json_data[spec]["events"].items():
            return_str_events += f'{spec}={event}={count}<>'

        # Update the total number of monitors and events
        total_monitors += num_monitors
        total_events += total_events_spec

    # Return the monitor and event information without the last '<>'
    return return_str_monitors[:-2], return_str_events[:-2], total_monitors, total_events

def get_num_violations_from_json():
    """
    Extract violation information from JSON file

    Returns:
        A tuple containing the number of violations, the unique violations count, and the violations by location
    """
    # Define the violation filename
    filename = f'D-violations.json'

    # Check if the violation file exists
    if not os.path.isfile(filename):
        return None
    
    # Check if the violation file is empty
    if os.path.getsize(filename) == 0:
        return None
    
    # Load the violation JSON file
    try:
        with open(filename, 'r') as f:
            json_data = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing JSON file {filename}: {e}")
        return None

    # Initialize the variables for the violation information
    total_violations_count = 0
    total_violations = ""
    unique_violations_count = 0
    unique_violations = ""
    unique_violations_by_location = {}
    unique_violations_by_test = {}

    # Iterate over the violation information for each spec
    for spec in json_data.keys():

        # Get the number of violations for the spec
        size = len(json_data[spec])
        # Update the return string for the spec (total number of violations for the spec)
        total_violations += f'{spec}={size};'

        # Initialize the set for the violations
        violations = set()

        # Iterate over the violations for the spec
        for item in json_data[spec]:
            # Add the violation to the list
            violations.add(item['violation'])
            
            # Extract the file name and line number and test id from the violation string
            violation_str = item['violation']
            test_id_str = item['test']

            # Add the violation to the unique violations by location
            if 'file_name:' in violation_str and 'line_num:' in violation_str:
                file_name = violation_str.split('file_name:')[1].split(',')[0].strip()
                if 'pymop-venv' in file_name:
                    file_name = file_name.split('pymop-venv')[-1]
                elif 'pymop' in file_name:
                    file_name = file_name.split('pymop')[-1]
                line_num = violation_str.split('line_num:')[1].split(',')[0].strip()
                location_key = f"{spec}:{file_name}:{line_num}"

                # Add the violation to the unique violations by location
                unique_violations_by_location[location_key] = unique_violations_by_location.get(location_key, 0) + 1

                # Add the test id to the unique violations by test
                if test_id_str is not None:
                    unique_violations_by_test[location_key] = unique_violations_by_test.get(location_key, set())
                    unique_violations_by_test[location_key].add(test_id_str)

        # Get the unique violations count for the spec
        unique_violations_spec_num = len(violations)
        unique_violations_count += unique_violations_spec_num
        unique_violations += f'{spec}={unique_violations_spec_num};'

        total_violations_count += size

    return (total_violations_count, total_violations[:-1], unique_violations_count, unique_violations[:-1], unique_violations_by_location, unique_violations_by_test)

def get_test_time(test_summary):
    """
    Extract test time from test summary

    Args:
        test_summary: A string containing the test summary

    Returns:
        A string containing the time
    """
    # Initialize the time variable
    time = None

    # If the test summary is not None, split the test summary into parts and extract the time
    if test_summary:
        parts = test_summary.split()
        for part in parts:
            if part.endswith('s') and parts[parts.index(part)-1] == "in":
                time = part[:-1]
    return time

def get_coverage_from_file(coverage_file):
    """
    Extract coverage information from XML coverage file
    
    Args:
        coverage_file: A string containing the path to the coverage XML file
        
    Returns:
        A float containing the line coverage percentage, or None if parsing fails
    """
    # Check if the coverage file exists
    if not coverage_file or not os.path.isfile(coverage_file):
        return None
    
    # Check if the coverage file is empty
    if os.path.getsize(coverage_file) == 0:
        return None
    
    try:
        # Parse the XML file
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        # Get the line-rate attribute from the coverage root element
        line_rate = root.get('line-rate')
        if line_rate is not None:
            # Convert to float and return as percentage
            return float(line_rate) * 100
        else:
            return None
            
    except (ET.ParseError, ValueError, AttributeError) as e:
        print(f"Error parsing coverage file {coverage_file}: {e}")
        return None

def get_commit_timestamp_and_message(commit_info_file):
    """
    Get the commit timestamp and commit message from the git log

    Args:
        commit_info_file: A string containing the path to the commit info file
    Returns:
        A tuple containing the commit timestamp and commit message, or (None, None) if unable to retrieve
    """
    # Check if the commit info file exists
    if not commit_info_file or not os.path.isfile(commit_info_file):
        return None, None
    
    # Check if the commit info file is empty
    if os.path.getsize(commit_info_file) == 0:
        return None, None
    
    # Open the commit info file and read the commit timestamp and commit message
    with open(commit_info_file, 'r') as file:
        for line in file:
            if 'Commit timestamp:=' in line:
                commit_timestamp = line.replace('Commit timestamp:= ', '').strip()
            if 'Commit message:=' in line:
                commit_message = line.replace('Commit message:= ', '').strip()
    return commit_timestamp, commit_message

def get_run_time_test_summary_from_files(result_file, output_file):
    """
    Extract run time information from result and output files

    Args:
        result_file: A string containing the result file
        output_file: A string containing the output file
    """
    # Initialize the end-to-end time
    end_to_end_time = "x"

    # If the result file is not None, open the result file and extract the test duration and end-to-end time
    if result_file is not None:
        with open(result_file, 'r') as file:
            for l in file:
                if 'Test Time:' in l:
                    test_time = l.split(' ')[-1].replace('s', '').strip()
                    if test_time != "Timeout":
                        end_to_end_time = float(test_time)

    # If the output file is not None, open the output file and extract the test summary
    test_summary = None
    if output_file:
        with open(output_file, 'r') as file:
            # Iterate over the lines in the output file in reverse order
            for line in reversed(file.readlines()):
                if "in" in line:
                    for part in ['passed', 'failed', 'skipped', 'xfailed', 'xpassed', 'errors']:
                        if part in line.lower():
                            test_summary = line.strip()
                            break

                # If the test summary is not None, break the loop
                if test_summary:
                    break

    # Return the end-to-end time and test summary
    return end_to_end_time, test_summary

def get_test_summary(test_summary, time, line):
    """
    Extract test summary from test summary and update the line dictionary (only test results, not time)

    Args:
        test_summary: A string containing the test summary
        time: A string containing the time
        line: A dictionary containing the line
    """
    # Check if the test summary and time are not None
    if test_summary and time:
        # Split the test summary into parts
        parts = test_summary.split()

        # Iterate over the parts
        for i in range(len(parts)):

            # Iterate over the keys in the line and update the line with the test summary
            for key in line.keys():
                if key in parts[i].lower():
                    try:
                        line[key] = int(parts[i-1])
                    except ValueError:
                        pass

    # If the test summary and time are None, set the columns to cross out to 'x'
    else:
        columns_to_cross_out = ['passed', 'failed', 'skipped', 'xfailed', 'xpassed', 'errors', 'time']
        for column in columns_to_cross_out:
            line[column] = 'x'

def create_base_data_structure(project, algorithm):
    """
    Create base OrderedDict for test results

    Args:
        project: A string containing the project
        algorithm: A string containing the algorithm
    """
    return OrderedDict({
        'project': project,
        'timestamp': 'x',
        'commit_sha': 'x',
        'commit_timestamp': 'x',
        'commit_message': 'x',
        'algorithm': algorithm,
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'xfailed': 0,
        'xpassed': 0,
        'errors': 0,
        'time': 0.0,
        'coverage': 'x',
        'type_project': algorithm,
        'time_instrumentation': 'x',
        'time_create_monitor': 'x',
        'test_duration': 'x',
        'post_run_time': 'x',
        'end_to_end_time': 'x',
        'total_violations_count': '',
        'total_violations': '',
        'unique_violations_count': '',
        'unique_violations': '',
        'violations_by_location': '',
        'violations_by_test': '',
        'total_monitors': '',
        'monitors': '',
        'total_events': '',
        'events': '',
    })

def results_csv_file(lines, commit_sha, timestamp):
    """
    Write results to a CSV file

    Args:
        lines: A list of dictionaries containing the results
        timestamp: A string containing the timestamp for the run
    """
    # Check if there is no data to write
    if not lines:
        print('No data to write.')
        return

    # Get the line with the most columns
    max_columns_line = max(lines, key=lambda line: len(line.keys()))

    # Open the CSV file for writing
    with open(f'continuous_analysis_results_{timestamp}.csv', 'w', newline='', encoding='utf-8') as f:
        # Create the writer object and write the header
        writer = csv.DictWriter(f, fieldnames=max_columns_line.keys())
        writer.writeheader()

        # Iterate over the lines
        for line in lines:
            # Remove the execution problems key if it exists (older version, not used anymore)
            if 'execution_problems' in line:
                del line['execution_problems']

            # Add the commit_sha to the line
            line['commit_sha'] = commit_sha

            # Add the timestamp to the line
            line['timestamp'] = timestamp

            # Convert violations_by_location dict to string if it exists and is a dict
            if isinstance(line.get('violations_by_location'), dict):
                converted_violations_loc = {}
                for loc, count in line['violations_by_location'].items():
                    try:  # For PyMOP version
                        spec, filepath, line_num = loc.rsplit(':', 2)
                        converted_loc = f"{spec}:{filepath}:{line_num}"
                        converted_violations_loc[converted_loc] = count
                    except ValueError:
                        filepath, line_num = loc.rsplit(':', 1)
                        converted_loc = f"{filepath}:{line_num}"
                        converted_violations_loc[converted_loc] = count
                line['violations_by_location'] = ';'.join(f"{loc}={count}" for loc, count in converted_violations_loc.items())

            # Convert violations_by_test dict to string if it exists and is a dict
            if isinstance(line.get('violations_by_test'), dict):
                converted_violations_test = {}
                for loc, test_ids in line['violations_by_test'].items():
                    converted_violations_test[loc] = str(test_ids)
                line['violations_by_test'] = ';'.join(f"{loc}={test_ids}" for loc, test_ids in converted_violations_test.items())

            # Write the line to the CSV file and handle any errors
            try:
                writer.writerow(line)
            except Exception as e:
                print('could not write line:', line.keys(), str(e))

def append_to_results_over_time(lines, commit_sha, timestamp):
    """
    Append results to a CSV file that tracks results over time

    Args:
        lines: A list of dictionaries containing the results
        commit_sha: A string containing the commit SHA
    """
    # Check if there is no data to append
    if not lines:
        print('No data to append.')
        return

    # Check if continuous_analysis_over_time_results.csv exists
    file_exists = os.path.isfile('continuous_analysis_over_time_results.csv')

    # Open the CSV file for appending
    with open('continuous_analysis_over_time_results.csv', 'a', newline='', encoding='utf-8') as f:
        # Get fieldnames from the first line
        max_columns_line = max(lines, key=lambda line: len(line.keys()))
        fieldnames = list(max_columns_line.keys())
        
        # Add commit_sha to fieldnames if it's not already there
        if 'commit_sha' not in fieldnames:
            fieldnames.append('commit_sha')

        # Add timestamp to fieldnames if it's not already there
        if 'timestamp' not in fieldnames:
            fieldnames.append('timestamp')
        
        # Create the writer object
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write header only if file doesn't exist
        if not file_exists:
            writer.writeheader()
        
        # Iterate over the lines to append each line into the CSV file
        for line in lines:
            # Remove the execution problems key if it exists (older version, not used anymore)
            if 'execution_problems' in line:
                del line['execution_problems']

            # Convert violations_by_location dict to string if it exists and is a dict
            if isinstance(line.get('violations_by_location'), dict):
                converted_violations_loc = {}
                for loc, count in line['violations_by_location'].items():
                    try:  # For PyMOP version
                        spec, filepath, line_num = loc.rsplit(':', 2)
                        converted_loc = f"{spec}:{filepath}:{line_num}"
                        converted_violations_loc[converted_loc] = count
                    except ValueError:
                        filepath, line_num = loc.rsplit(':', 1)
                        converted_loc = f"{filepath}:{line_num}"
                        converted_violations_loc[converted_loc] = count
                line['violations_by_location'] = ';'.join(f"{loc}={count}" for loc, count in converted_violations_loc.items())

            # Convert violations_by_test dict to string if it exists and is a dict
            if isinstance(line.get('violations_by_test'), dict):
                converted_violations_test = {}
                for loc, test_ids in line['violations_by_test'].items():
                    converted_violations_test[loc] = str(test_ids)
                line['violations_by_test'] = ';'.join(f"{loc}={test_ids}" for loc, test_ids in converted_violations_test.items())

            # Add commit_sha to the line
            line['commit_sha'] = commit_sha

            # Add timestamp to the line
            line['timestamp'] = timestamp

            # Write the line to the CSV file and handle any errors
            try:
                writer.writerow(line)
            except Exception as e:
                print('could not write line:', line.keys(), str(e))

def main(project: str, commit_sha: str):
    """Main function to process projects and generate results"""
    # Get the timestamp for the current run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Initialize the lines list
    lines = []

    # Parse the output for the project
    original_folder = f"./continuous-analysis-output/{project}_original_output"
    pymop_folder = f"./continuous-analysis-output/{project}_pymop_output"
    dylin_folder = f"./continuous-analysis-output/{project}_dylin_output"

    # ===============================================
    # Process Original files
    # ===============================================

    # Set the algorithm to original
    algorithm = 'original'

    # Change to the original folder
    os.chdir(original_folder)

    # Get all files in the original folder
    files = os.listdir()

    # Get the result and output files
    result_files = [f for f in files if f.endswith(f'results.txt')]
    output_files = [f for f in files if f.endswith('Output.txt')]
    coverage_files = [f for f in files if f.endswith('coverage.xml')]
    commit_info_files = [f for f in files if f.endswith('commit_info.txt')]

    # If no result or output files, print error and skip to next project
    if not result_files or not output_files:
        print(f'No original files found for {project}')
        result_file = None
        output_file = None
    else:
        # Get the first result, output, and coverage files
        result_file = result_files[0]
        output_file = output_files[0]

    if not coverage_files:
        coverage_file = None
    else:
        coverage_file = coverage_files[0]

    if not commit_info_files:
        commit_info_file = None
    else:
        commit_info_file = commit_info_files[0]

    # Get the end-to-end time and test summary
    end_to_end_time, test_summary = get_run_time_test_summary_from_files(result_file, output_file)

    # If no result file, print error and skip to next project
    if result_file is None:
        print(f"No test results found for {project} with algorithm {algorithm}")
        os.chdir('../..')
        return

    # Get the time from the test summary
    time = get_test_time(test_summary)

    # If no test summary, print error and skip to next project
    if not test_summary:
        print(f"No test summary found for {project} with algorithm {algorithm}")
        os.chdir('../..')
        return

    # Get the coverage from the coverage file
    coverage = get_coverage_from_file(coverage_file)

    # Get the commit timestamp and commit message from the git log
    commit_timestamp, commit_message = get_commit_timestamp_and_message(commit_info_file)

    # Create the base data structure
    line = create_base_data_structure(project, algorithm)

    # Process the test time results
    line['time'] = str(time)

    # Process the test summary results
    get_test_summary(test_summary, time, line)

    # Add the instrumentation time
    line['time_instrumentation'] = '0.0'

    # Add the time to create the monitor
    line['time_create_monitor'] = '0.0'

    # Add the test duration
    line['test_duration'] = str(end_to_end_time)

    # Add end-to-end time
    line['end_to_end_time'] = str(end_to_end_time)

    # Add the post-run time
    line['post_run_time'] = '0.0'
    
    # Add the coverage
    if coverage is not None:
        line['coverage'] = str(coverage)
    else:
        line['coverage'] = 'x'

    # Add the commit timestamp to the line
    line['commit_timestamp'] = commit_timestamp

    # Add the commit message to the line
    line['commit_message'] = commit_message

    # Add the line to the lines list
    lines.append(line)

    # Change to the original folder
    os.chdir('../..')

    # ===============================================
    # Process Pymop files with libraries
    # ===============================================

    # If no pymop folder, print error , append a empty line to the results file, and skip to next project
    if not os.path.exists(pymop_folder):
        print(f'No pymop folder found for {project}')
        line = OrderedDict({
            'project': project,
            'timestamp': 'x',
            'commit_sha': 'x',
            'commit_timestamp': 'x',
            'commit_message': 'x',
            'algorithm': 'pymop',
            'passed': 'x',
            'failed': 'x',
            'skipped': 'x',
            'xfailed': 'x',
            'xpassed': 'x',
            'errors': 'x',
            'time': 'x',
            'coverage': 'x',
            'type_project': 'pymop',
            'time_instrumentation': 'x',
            'time_create_monitor': 'x',
            'test_duration': 'x',
            'post_run_time': 'x',
            'end_to_end_time': 'x',
            'total_violations_count': '',
            'total_violations': '',
            'unique_violations_count': '',
            'unique_violations': '',
            'violations_by_location': '',
            'violations_by_test': '',
            'total_monitors': '',
            'monitors': '',
            'total_events': '',
            'events': '',
        })
        # Append the empty line to the results file
        lines.append(line)
    else:
        # Change to the pymop folder
        os.chdir(pymop_folder)

        # Process Algorithm D results (only one algorithm is used in this script)
        for algorithm in ["D"]:
            # Get all files in the pymop folder
            files = os.listdir()

            # the result and output files
            result_files = [f for f in files if f.endswith(f'results.txt')]
            output_files = [f for f in files if f.endswith('_Output.txt')]

            # If no result or output files, print error and skip to next project
            if not result_files or not output_files:
                print(f'No pymop files found for {project}')
                result_file = None
                output_file = None
            else:
                result_file = result_files[0]
                output_file = output_files[0]

            # Get the end-to-end time and test summary
            end_to_end_time, test_summary = get_run_time_test_summary_from_files(result_file, output_file)

            # Get the time from the test summary
            time = get_test_time(test_summary)

            # Create the base data structure
            line = create_base_data_structure(project, 'pymop')

            # Process the test time results
            line['time'] = str(time)

            # Process the test summary results
            get_test_summary(test_summary, time, line)

            # Get the instrumentation time, create monitor time, and test duration
            try:
                ret_time = get_time_from_json()
            except Exception as e:
                ret_time = None

            # If ret_time is not None, set the instrumentation time, create monitor time, and test duration
            if ret_time is not None and time is not None and isinstance(end_to_end_time, float) and isinstance(end_to_end_time, float):
                (instrumentation_duration, create_monitor_duration, _) = ret_time
                line['time_instrumentation'] = instrumentation_duration
                line['time_create_monitor'] = create_monitor_duration
                line['test_duration'] = end_to_end_time - instrumentation_duration - create_monitor_duration
                line['end_to_end_time'] = end_to_end_time
            else:
                line['time_instrumentation'] = 'x'
                line['time_create_monitor'] = 'x'
                line['test_duration'] = 'x'
                line['end_to_end_time'] = 'x'

            # If the algorithm is not original, get the number of violations
            if algorithm != "original":

                # Get the number of violations
                ret_violation = get_num_violations_from_json()

                # If ret_violation is not None, set the number of violations
                if ret_violation is not None:
                    (
                        total_violations_count,
                        total_violations,
                        unique_violations_count,
                        unique_violations,
                        unique_violations_by_location,
                        unique_violations_by_test
                    ) = ret_violation
                
                    line['total_violations_count'] = total_violations_count
                    line['total_violations'] = total_violations
                    line['unique_violations_count'] = unique_violations_count
                    line['unique_violations'] = unique_violations
                    line['violations_by_location'] = unique_violations_by_location
                    line['violations_by_test'] = unique_violations_by_test

                # Get the monitors and events
                ret_full = get_monitors_and_events_from_json(algorithm)

                # If ret_full is not None, set the monitors and events
                if ret_full is not None:
                    monitors_str, events_str, total_monitors, total_events = ret_full

                    line['monitors'] = monitors_str
                    line['total_monitors'] = total_monitors
                    line['events'] = events_str
                    line['total_events'] = total_events

                # Add the post-run time
                line['post_run_time'] = '0.0'

                # Add the commit timestamp to the line
                line['commit_timestamp'] = commit_timestamp

                # Add the commit message to the line
                line['commit_message'] = commit_message

            # Add the line to the lines list
            lines.append(line)

        # Change back to parent directory
        os.chdir('../..')

    # ===============================================
    # Process Dylin files without libraries
    # ===============================================

    # If no dylin folder, print error, append a empty line to the results file, and skip to next project
    if not os.path.exists(dylin_folder):
        print(f'No dylin folder found for {project}')
        line = OrderedDict({
            'project': project,
            'timestamp': 'x',
            'commit_sha': 'x',
            'commit_timestamp': 'x',
            'commit_message': 'x',
            'algorithm': 'dylin',
            'passed': 'x',
            'failed': 'x',
            'skipped': 'x',
            'xfailed': 'x',
            'xpassed': 'x',
            'errors': 'x',
            'time': 'x',
            'coverage': 'x',
            'type_project': 'dylin',
            'time_instrumentation': 'x',
            'time_create_monitor': 'x',
            'test_duration': 'x',
            'post_run_time': 'x',
            'end_to_end_time': 'x',
            'total_violations_count': '',
            'total_violations': '',
            'unique_violations_count': '',
            'unique_violations': '',
            'violations_by_location': '',
            'violations_by_test': '',
            'total_monitors': '',
            'monitors': '',
            'total_events': '',
            'events': '',
        })
        # Append the empty line to the results file
        lines.append(line)
    else:
        # Change to the dylin folder
        os.chdir(dylin_folder)

        # Set the algorithm to dylin
        algorithm = 'dylin'

        # Get all files in the dylin folder
        files = os.listdir()

        # Get the result and output files
        result_files = [f for f in files if f.endswith(f'results.txt')]
        output_files = [f for f in files if f.endswith('_Output.txt')]
        findings_csv = [f for f in files if f.endswith('_findings.csv')]
        findings_txt = [f for f in files if f.endswith('_findings.txt')]

        # If no result or output files, print error and skip to next project
        if not result_files or not output_files:
            print(f'No dylin files found for {project}')
            result_file = None
            output_file = None
        else:
            # Get the first result and output files (should only be one)
            result_file = result_files[0]
            output_file = output_files[0]

        # Get the instrumentation duration and test duration
        instrumentation_duration = "x"
        test_duration = "x"
        post_run_time = "x"
        if result_file is not None:
            with open(result_file, 'r') as file:
                for l in file:
                    if 'Instrumentation Time:' in l:
                        instrumentation_time = l.split(' ')[-1].replace('s', '').strip()
                        if instrumentation_time != "Timeout":
                            instrumentation_duration = float(instrumentation_time)
                    elif 'Test Time:' in l:
                        test_time = l.split(' ')[-1].replace('s', '').strip()
                        if test_time != "Timeout":
                            test_duration = float(test_time)
                    elif 'Post-Run Time:' in l:
                        post_run_time = l.split(' ')[-1].replace('s', '').strip()
                        if post_run_time != "Timeout":
                            post_run_time = float(post_run_time)
        
        # Get the total violations, violations, total events, and events
        total_violations_count = 0
        total_violations = []
        unique_violations_count = 0
        unique_violations = {}
        violations_by_location = {}
        violations_by_test = {}

        # If there are statistics files, parse them
        if findings_csv and findings_txt:

            # Parse the findings csv
            with open(findings_csv[0], 'r') as file:
                reader = csv.reader(file)
                for row in reader:
                    if int(row[1]) > 0:
                        spec_name = row[0]
                        total_violations.append(f"{spec_name}={row[1]}")
                        total_violations_count += int(row[1])

            # Parse the findings txt
            with open(findings_txt[0], 'r') as file:
                for l in file:
                    if l.strip() != "":
                        l_split = l.split(': ')
                        if len(l_split) < 3 or '-' not in l_split[0]:
                            continue
                        violation_number = l_split[0].strip()

                        # Convert the violation number to the spec name
                        if violation_number in dylin_spec_dict:
                            spec_name = dylin_spec_dict[violation_number]
                        else:
                            raise ValueError(f'Violation number {violation_number} not found in dylin_spec_dict')

                        # Form the violation location string
                        violation_file = l_split[1].strip()
                        if 'dylin' in violation_file:
                            violation_file = violation_file.split('dylin')[-1]
                        if '.orig' in violation_file:
                            violation_file = violation_file.replace('.orig', '')
                        violation_line = l_split[2].strip()

                        violation_str = f"{spec_name}:{violation_file}:{violation_line}"
                        if violation_str not in violations_by_location:
                            violations_by_location[violation_str] = 1
                            unique_violations[spec_name] = unique_violations.get(spec_name, 0) + 1
                        else:
                            violations_by_location[violation_str] += 1

        # Convert lists to strings
        total_violations = ';'.join(total_violations) if total_violations else ""
        unique_violations_str = []
        for key, value in unique_violations.items():
            unique_violations_count += value
            unique_violations_str.append(f"{key}={value}")
        unique_violations = ';'.join(unique_violations_str) if unique_violations_str else ""

        # Get the test summary from the output file
        test_summary = None
        if output_file:
            with open(output_file, 'r') as file:
                for line in reversed(file.readlines()):
                    if "passed" in line.lower() and "in" in line:
                        test_summary = line.strip()
                        break

        # Get the time from the test summary
        time = get_test_time(test_summary)

        # Create the base data structure
        line = create_base_data_structure(project, 'dylin')

        # Process the test time results
        line['time'] = str(time)

        # Process the test summary results
        get_test_summary(test_summary, time, line)

        # If no time, set the test duration to x
        if time is None and not isinstance(instrumentation_duration, float) and not isinstance(test_duration, float) and not isinstance(post_run_time, float):
            line['time_instrumentation'] = 'x'
            line['test_duration'] = 'x'
            line['post_run_time'] = 'x'
            line['end_to_end_time'] = 'x'
        else:
            line['time_instrumentation'] = instrumentation_duration
            line['test_duration'] = test_duration
            line['end_to_end_time'] = instrumentation_duration + test_duration + post_run_time
            line['post_run_time'] = post_run_time
            
            # Add the total violations, violations, total events, and events
            line['total_violations_count'] = total_violations_count
            line['total_violations'] = total_violations
            line['unique_violations_count'] = unique_violations_count
            line['unique_violations'] = unique_violations
            line['violations_by_location'] = violations_by_location
            line['violations_by_test'] = violations_by_test

        # Add the time to create the monitor
        line['time_create_monitor'] = 0.0  # DynaPyt doesn't track this

        # Add the coverage
        if coverage is not None:
            line['coverage'] = str(coverage)
        else:
            line['coverage'] = 'x'

        # Add the commit timestamp to the line
        line['commit_timestamp'] = commit_timestamp

        # Add the commit message to the line
        line['commit_message'] = commit_message

        # Add the line to the lines list
        lines.append(line)
        os.chdir('../..')

    # Add the results to the continuous_analysis_results_${timestamp}.csv file
    print("\n====== RESULTS CSV ======\n")
    print(f'creating continuous_analysis_results_{timestamp}.csv')
    results_csv_file(lines, commit_sha, timestamp)
    print(f'created continuous_analysis_results_{timestamp}.csv')

    # Append the results to the continuous_analysis_over_time_results.csv file
    print("\n====== APPENDING TO RESULTS OVER TIME ======\n")
    print(f'appending to continuous_analysis_over_time_results.csv')
    append_to_results_over_time(lines, commit_sha, timestamp)
    print('appended to continuous_analysis_over_time_results.csv')

if __name__ == "__main__":
    project = sys.argv[1]
    commit_sha = sys.argv[2]
    main(project, commit_sha)
