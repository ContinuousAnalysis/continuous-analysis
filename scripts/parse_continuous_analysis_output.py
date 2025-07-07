# Import necessary libraries
import os
import json
from collections import OrderedDict
from collections import Counter
import csv
from datetime import datetime
import sys


def get_time_from_json():
    """Extract time information from JSON file"""
    filename = f'D-time.json'
    if not os.path.isfile(filename):
        return None
    
    # Check if file is empty
    if os.path.getsize(filename) == 0:
        return None
    
    try:
        with open(filename, 'r') as f:
            json_data = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing JSON file {filename}: {e}")
        return None

    instrumentation_duration = json_data.get('instrumentation_duration', 0)
    create_monitor_duration = json_data.get('create_monitor_duration', 0)
    test_duration = json_data.get('test_duration', 0)

    return instrumentation_duration, create_monitor_duration, test_duration

def get_monitors_and_events_from_json(algorithm):
    """Extract monitor and event information from JSON file"""
    filename = f'{algorithm}-full.json'
    if not os.path.isfile(filename):
        return None
    
    # Check if file is empty
    if os.path.getsize(filename) == 0:
        return None
    
    try:
        with open(filename, 'r') as f:
            json_data = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing JSON file {filename}: {e}")
        return None

    return_str_monitors = ""
    return_str_events = ""
    total_monitors = 0
    total_events = 0

    for spec in json_data.keys():
        num_monitors = json_data[spec]["monitors"]
        total_events_spec = sum(json_data[spec]["events"].values())
        return_str_monitors += f'{spec}={num_monitors}<>'
        for event, count in json_data[spec]["events"].items():
            return_str_events += f'{spec}={event}={count}<>'
        total_monitors += num_monitors
        total_events += total_events_spec

    return return_str_monitors[:-2], return_str_events[:-2], total_monitors, total_events

def get_num_violations_from_json():
    """Extract violation information from JSON file"""
    filename = f'D-violations.json'
    if not os.path.isfile(filename):
        return None
    
    # Check if file is empty
    if os.path.getsize(filename) == 0:
        return None
    
    try:
        with open(filename, 'r') as f:
            json_data = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing JSON file {filename}: {e}")
        return None

    return_spec_string = ""
    total_violations = 0
    unique_violations_count = ""
    violations_by_location = {}

    for spec in json_data.keys():
        size = len(json_data[spec])
        return_spec_string += f'{spec}={size};'

        violations = []
        for item in json_data[spec]:
            violations.append(item['violation'])
            
            # Extract file name and line number from violation string
            violation_str = item['violation']
            if 'file_name:' in violation_str and 'line_num:' in violation_str:
                file_name = violation_str.split('file_name:')[1].split(',')[0].strip()
                line_num = violation_str.split('line_num:')[1].strip()
                location_key = f"{spec}:{file_name}:{line_num}"
                violations_by_location[location_key] = violations_by_location.get(location_key, 0) + 1

        violations_counter = Counter(violations)
        unique_violations_count += f'{spec}={len(dict(violations_counter))};'
        total_violations += size

    return (return_spec_string[:-1], total_violations, unique_violations_count, violations_by_location)

def results_csv_file(lines, timestamp):
    """Write results to a CSV file"""
    if not lines:
        print('No data to write.')
        return

    max_columns_line = max(lines, key=lambda line: len(line.keys()))

    with open(f'continuous-analysis-results_{timestamp}.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=max_columns_line.keys())
        writer.writeheader()
        for line in lines:
            if 'execution_problems' in line:
                del line['execution_problems']
            # Convert violations_by_location dict to string if it exists and is a dict
            if isinstance(line.get('violations_by_location'), dict):
                # Clean up file paths based on the tool type
                cleaned_violations = {}
                for loc, count in line['violations_by_location'].items():
                    try:
                        spec, filepath, line_num = loc.rsplit(':', 2)
                        clean_loc = f"{spec}:{filepath}:{line_num}"
                        cleaned_violations[clean_loc] = count
                    except ValueError:
                        filepath, line_num = loc.rsplit(':', 1)
                        clean_loc = f"{filepath}:{line_num}"
                        cleaned_violations[clean_loc] = count
                line['violations_by_location'] = ';'.join(f"{loc}={count}" for loc, count in cleaned_violations.items())
            try:
                writer.writerow(line)
            except Exception as e:
                print('could not write line:', line.keys(), str(e))

def process_test_summary(test_summary):
    """Process test summary to extract time and test results"""
    time = None
    if test_summary:
        parts = test_summary.split()
        for part in parts:
            if part.endswith('s') and parts[parts.index(part)-1] == "in":
                time = part[:-1]
    return time

def create_base_data_structure(project, algorithm):
    """Create base OrderedDict for test results"""
    return OrderedDict({
        'project': project,
        'algorithm': algorithm,
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'xfailed': 0,
        'xpassed': 0,
        'errors': 0,
        'time': None,
        'type_project': algorithm,
        'time_instrumentation': 'x',
        'time_create_monitor': 'x',
        'test_duration': 'x',
        'post_run_time': 'x',
        'end_to_end_time': 'x',
        'total_violations': 'x',
        'violations': '',
        'unique_violations_count': '',
        'violations_by_location': '',
    })

def process_test_results(test_summary, time, line):
    """Process test results and update line dictionary"""
    if test_summary and time:
        parts = test_summary.split()
        for i in range(len(parts)):
            for key in line.keys():
                if key in parts[i].lower():
                    try:
                        line[key] = int(parts[i-1])
                    except ValueError:
                        pass
    else:
        columns_to_cross_out = ['passed', 'failed', 'skipped', 'xfailed', 'xpassed', 'errors', 'time']
        for column in columns_to_cross_out:
            line[column] = 'x'

def get_test_info_from_files(result_file, output_file):
    """Extract test information from result and output files"""
    test_duration = "x"
    end_to_end_time = "x"
    post_run_time = "x"
    if result_file is not None:
        with open(result_file, 'r') as file:
            for l in file:
                if 'Test Time:' in l:
                    test_time = l.split(' ')[-1].replace('s', '').strip()
                    if test_time != "Timeout":
                        test_duration = float(test_time)
                        end_to_end_time = float(test_time)
                elif 'Post-Run Time:' in l:
                    post_run_time_val = l.split('Post-Run Time:')[1].strip()
                    if post_run_time_val.endswith('s'):
                        post_run_time_val = post_run_time_val[:-1]
                    try:
                        post_run_time = float(post_run_time_val)
                    except ValueError:
                        post_run_time = post_run_time_val

    test_summary = None
    if output_file:
        with open(output_file, 'r') as file:
            for line in reversed(file.readlines()):
                if "in" in line:
                    for part in ['passed', 'failed', 'skipped', 'xfailed', 'xpassed', 'errors']:
                        if part in line.lower():
                            test_summary = line.strip()
                            break
                
                if test_summary:
                    break

    return test_duration, end_to_end_time, test_summary, post_run_time

def append_to_results_over_time(lines, timestamp):
    """Append results to a CSV file that tracks results over time"""
    if not lines:
        print('No data to append.')
        return

    # Check if pymop_results_over_time.csv exists
    file_exists = os.path.isfile('pymop_over_time_results.csv')
    
    with open('pymop_over_time_results.csv', 'a', newline='', encoding='utf-8') as f:
        # Get fieldnames from the first line
        max_columns_line = max(lines, key=lambda line: len(line.keys()))
        fieldnames = list(max_columns_line.keys())
        
        # Add timestamp to fieldnames if it's not already there
        if 'timestamp' not in fieldnames:
            fieldnames.append('timestamp')
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write header only if file doesn't exist
        if not file_exists:
            writer.writeheader()
        
        for line in lines:
            line_copy = line.copy()
            if 'execution_problems' in line_copy:
                del line_copy['execution_problems']
            # Convert violations_by_location dict to string if it exists and is a dict
            if isinstance(line_copy.get('violations_by_location'), dict):
                # Clean up file paths based on the tool type
                cleaned_violations = {}
                for loc, count in line_copy['violations_by_location'].items():
                    filepath, line_num = loc.rsplit(':', 1)
                    clean_loc = f"{filepath}:{line_num}"
                    cleaned_violations[clean_loc] = count
                line_copy['violations_by_location'] = ';'.join(f"{loc}={count}" for loc, count in cleaned_violations.items())
            
            # Add timestamp to the line
            line_copy['timestamp'] = timestamp
            
            try:
                writer.writerow(line_copy)
            except Exception as e:
                print('could not write line:', line_copy.keys(), str(e))

def main(project: str):
    """Main function to process projects and generate results"""
    # Get the timestamp for the current run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # Initialize the lines list
    lines = []

    # Parse the output for the project
    original_folder = f"./continuous-analysis-output/{project}_original_output"
    pymop_folder = f"./continuous-analysis-output/{project}_pymop_output"
    dylin_folder = f"./continuous-analysis-output/{project}_dylin_output"

    # ===============================================
    # Process Original files
    # ===============================================

    # Change to the original folder
    os.chdir(original_folder)

    # Get all files in the original folder
    files = os.listdir()

    # Get the result and output files
    result_files = [f for f in files if f.endswith(f'results.txt')]
    output_files = [f for f in files if f.endswith('Output.txt')]

    # If no result or output files, print error and skip to next project
    if not result_files or not output_files:
        print(f'No original files found for {project}')
        result_file = None
        output_file = None
    else:
        # Get the first result and output files
        result_file = result_files[0]
        output_file = output_files[0]

    # Get the test duration, end-to-end time, and test summary
    algorithm = 'original'
    test_duration, end_to_end_time, test_summary, post_run_time = get_test_info_from_files(result_file, output_file)

    # If no result file, print error and skip to next project
    if result_file is None:
        print(f"No test results found for {project} with algorithm {algorithm}")
        os.chdir('../..')
        return

    # Get the time from the test summary
    time = process_test_summary(test_summary)

    # If no test summary, print error and skip to next project
    if not test_summary:
        print(f"No test summary found for {project} with algorithm {algorithm}")
        os.chdir('../..')
        return

    # Create the base data structure
    line = create_base_data_structure(project, algorithm)

    # Process the test results
    line['time'] = time
    process_test_results(test_summary, time, line)

    # Add the type of project
    line['type_project'] = 'original'

    # Add the instrumentation time
    line['time_instrumentation'] = 0.0

    # Add the test duration
    line['test_duration'] = test_duration

    # Add the time to create the monitor
    line['time_create_monitor'] = 0.0

    # Add end-to-end time
    line['end_to_end_time'] = end_to_end_time

    # Add the post-run time
    line['post_run_time'] = 0.0

    # Add the line to the lines list
    lines.append(line)

    # Change to the original folder
    os.chdir('../..')

    # ===============================================
    # Process Pymop files with libraries
    # ===============================================

    # If no pymop folder, print error and skip to next project
    if not os.path.exists(pymop_folder):
        print(f'No pymop folder found for {project}')
        line = OrderedDict({
            'project': project,
            'algorithm': 'pymop',
            'passed': 'x',
            'failed': 'x',
            'skipped': 'x',
            'xfailed': 'x',
            'xpassed': 'x',
            'errors': 'x',
            'time': 'x',
            'type_project': 'pymop',
            'time_instrumentation': 'x',
            'test_duration': 'x',
            'time_create_monitor': 'x',
            'total_violations': 'x',
            'violations': 'x',
            'unique_violations_count': 'x',
            'monitors': 'x',
            'total_monitors': 'x',
            'events': 'x',
            'total_events': 'x',
            'end_to_end_time': 'x',
            'post_run_time': 'x',
        })
        lines.append(line)
    else:
        os.chdir(pymop_folder)

        # Process Algorithm D results
        for algorithm in ["D"]:
            files = os.listdir()
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

            # Get the test duration, end-to-end time, and test summary
            test_duration, end_to_end_time, test_summary, post_run_time = get_test_info_from_files(result_file, output_file)

            # Get the time from the test summary
            time = process_test_summary(test_summary)

            # Create the base data structure
            line = create_base_data_structure(project, algorithm)
            line['time'] = time
            process_test_results(test_summary, time, line)

            # Set the type of project
            line['type_project'] = 'pymop'

            # Get the instrumentation time, create monitor time, and test duration
            try:
                ret_time = get_time_from_json()
            except Exception as e:
                ret_time = None

            # If ret_time is not None, set the instrumentation time, create monitor time, and test duration
            if ret_time is not None and time is not None and isinstance(end_to_end_time, float) and isinstance(test_duration, float):
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

            if algorithm != "original":
                ret_violation = get_num_violations_from_json()

                if ret_violation is not None:
                    (
                        violations_str,
                        total_violations,
                        unique_violations_count,
                        violations_by_location
                    ) = ret_violation
                
                    line['total_violations'] = total_violations
                    line['violations'] = violations_str
                    line['unique_violations_count'] = unique_violations_count
                    line['violations_by_location'] = violations_by_location

                ret_full = get_monitors_and_events_from_json(algorithm)

                if ret_full is not None:
                    monitors_str, events_str, total_monitors, total_events = ret_full

                    line['monitors'] = monitors_str
                    line['total_monitors'] = total_monitors
                    line['events'] = events_str
                    line['total_events'] = total_events

                # Add the post-run time
                line['post_run_time'] = 0.0

            lines.append(line)

        # Change back to parent directory
        os.chdir('../..')

    # ===============================================
    # Process Dylin files without libraries
    # ===============================================

    # If no dylin folder, print error and skip to next project
    if not os.path.exists(dylin_folder):
        print(f'No dylin folder found for {project}')
        line = OrderedDict({
            'project': project,
            'algorithm': 'dylin',
            'passed': 'x',
            'failed': 'x',
            'skipped': 'x',
            'xfailed': 'x',
            'xpassed': 'x',
            'errors': 'x',
            'time': 'x',
            'type_project': 'dylin',
            'time_instrumentation': 'x',
            'test_duration': 'x',
            'time_create_monitor': 'x',
            'end_to_end_time': 'x',
            'total_violations': 'x',
            'violations': 'x',
            'unique_violations_count': 'x',
            'violations_by_location': 'x',
            'post_run_time': 'x',
        })
        lines.append(line)
    else:
        # Change to the dylin folder
        os.chdir(dylin_folder)

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
        algorithm = 'dylin'
        instrumentation_duration = "x"
        test_duration = "x"
        if result_file is not None:
            with open(result_file, 'r') as file:
                for l in file:
                    if 'Instrumentation Time:' in l:
                        instrumentation_duration = float(l.split(' ')[-1].replace('s', '').strip())
                    elif 'Test Time:' in l:
                        test_time = l.split(' ')[-1].replace('s', '').strip()
                        if test_time != "Timeout":
                            test_duration = float(test_time)
                    elif 'Post-Run Time:' in l:
                        post_run_time = l.split(' ')[-1].replace('s', '').strip()
                        if post_run_time != "Timeout":
                            post_run_time = float(post_run_time)
        
        # Get the total violations, violations, total events, and events
        total_violations = 0
        violations_map = []
        unique_violations_count = {}
        violations_by_location = {}  # New dict to track violations by location

        # If there are statistics files, parse them
        if findings_csv and findings_txt:

            # Parse the findings csv
            with open(findings_csv[0], 'r') as file:
                reader = csv.reader(file)
                for row in reader:
                    if int(row[1]) > 0:
                        spec_name = row[0]
                        violations_map.append(f"{spec_name}={row[1]}")
                        total_violations += int(row[1])

            # Parse the findings txt
            with open(findings_txt[0], 'r') as file:
                for l in file:
                    if l.strip() != "":
                        l_split = l.split(': ')
                        if len(l_split) < 3 or '-' not in l_split[0]:
                            continue
                        violation_number = l_split[0].strip()
                        violation_file = l_split[1].strip()
                        violation_line = l_split[2].strip()
                        violation_location = f"{violation_file}:{violation_line}"
                        if violation_location not in violations_by_location:
                            violations_by_location[violation_location] = 1
                            unique_violations_count[violation_number] = unique_violations_count.get(violation_number, 0) + 1
                        else:
                            violations_by_location[violation_location] += 1

        # Convert lists to strings
        violations_map = ';'.join(violations_map) if violations_map else ""  # Changed to PyMOP format: "spec1=count1;spec2=count2"
        unique_violations_count_list = []
        for key, value in unique_violations_count.items():
            unique_violations_count_list.append(f"{key}={value}")
        unique_violations_count = ';'.join(unique_violations_count_list) if unique_violations_count_list else ""
        total_violations = str(total_violations)

        # Get the test summary from the output file
        test_summary = None
        if output_file:
            with open(output_file, 'r') as file:
                for line in reversed(file.readlines()):
                    if "passed" in line.lower() and "in" in line:
                        test_summary = line.strip()
                        break

        # Get the time from the test summary
        time = process_test_summary(test_summary)

        # Create the base data structure
        line = create_base_data_structure(project, algorithm)
        line['time'] = time
        process_test_results(test_summary, time, line)

        # Add the type of project
        line['type_project'] = 'dylin'

        # Add the instrumentation time
        line['time_instrumentation'] = instrumentation_duration

        # If no time, set the test duration to x
        if time is None:
            line['test_duration'] = 'x'
            line['end_to_end_time'] = 'x'
            line['total_violations'] = 'x'
            line['violations'] = 'x'
            line['unique_violations_count'] = 'x'
            line['violations_by_location'] = 'x'
        else:
            line['test_duration'] = test_duration
            if test_duration != "x":
                line['end_to_end_time'] = float(instrumentation_duration) + float(test_duration) + float(post_run_time)
            else:
                line['end_to_end_time'] = 'x'
            
            # Add the total violations, violations, total events, and events
            line['total_violations'] = total_violations
            line['violations'] = violations_map
            line['unique_violations_count'] = unique_violations_count
            line['violations_by_location'] = violations_by_location

        # Add the time to create the monitor
        line['time_create_monitor'] = 0.0  # DynaPyt doesn't track this

        # Add the post-run time
        line['post_run_time'] = post_run_time

        # Add the line to the lines list
        lines.append(line)
        os.chdir('../..')

    # Add the results to the pymop_results_${timestamp}.csv file
    print("\n====== RESULTS CSV ======\n")
    print(f'creating pymop_results_{timestamp}.csv')
    results_csv_file(lines, timestamp)
    print(f'created pymop_results_{timestamp}.csv')

    # Append the results to the pymop_over_time_results.csv file
    # print("\n====== APPENDING TO RESULTS OVER TIME ======\n")
    # print(f'appending to pymop_over_time_results.csv')
    # append_to_results_over_time(lines, timestamp)
    # print('appended to pymop_over_time_results.csv')

if __name__ == "__main__":
    project = sys.argv[1]
    main(project)
