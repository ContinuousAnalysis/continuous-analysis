import os
import csv
import zipfile


# Declare a variable to store the project name
project = ''

# Get all the zip files in the downloaded-assets folder
zip_files = [f for f in os.listdir('downloaded-assets') if f.endswith('.zip')]

# Unzip all the zip files to a new folder called unzipped-assets
for zip_file in zip_files:
    with zipfile.ZipFile(f'downloaded-assets/{zip_file}', 'r') as zip_ref:
        zip_ref.extractall(f'unzipped-assets/{zip_file.replace('.zip', '')}')
        if len(zip_file.replace('.zip', '').split('-results-')) == 2:
            project = zip_file.replace('.zip', '').split('-results-')[0]

# Check if the project name is empty
if project == '':
    print('Error: Project name is empty')
    exit(1)

# Get all the commits from the all-commits.txt file (newest to oldest)
commits = []
with open('all_commits.txt', 'r') as f:
    commits = f.read().splitlines()

# Reverse the commits list (newest to oldest)
commits = reversed(commits)

# Append the results to the continuous_analysis_over_time_results.csv file
output_file = 'continuous_analysis_over_time_results.csv'
output_exists = os.path.exists(output_file)

# Write the results to the output file
with open(output_file, 'a', newline='') as out_f:
    writer = csv.writer(out_f)

    # Iterate through all the extracted commits
    for commit in commits:
        results_csv_file = f'unzipped-assets/{project}-results-{commit}/{project}-results-{commit}/continuous_analysis_over_time_results.csv'

        # Read the results from the unzipped asset
        if os.path.exists(results_csv_file):
            with open(results_csv_file, 'r', newline='') as in_f:
                reader = csv.reader(in_f)
                rows = list(reader)

                # Skip if there are no rows
                if not rows:
                    continue

                # Write header only if output file did not exist before and this is the first file
                if not output_exists:
                    writer.writerow(rows[0])
                    output_exists = True
                    data_rows = rows[1:]
                else:
                    data_rows = rows[1:]  # skip header

                # Write the data rows to the output file
                writer.writerows(data_rows)

# Filter out the new violations based on the commit changes
# for commit in commits:
#     # run the filter_new_violations.py script
#     os.system(f"python3 filter_new_violations.py {project}-original {commit}")
