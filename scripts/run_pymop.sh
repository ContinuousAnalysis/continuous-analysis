#!/bin/bash

# PyMOP Runner Script
# Usage: ./run_pymop.sh <project_name>

PROJECT=$1

if [ -z "$PROJECT" ]; then
    echo "Usage: $0 <project_name>"
    exit 1
fi

# Print project name
echo "Running PyMOP for project: $PROJECT"

# Go to project directory
cd "$PROJECT-pymop"

# Install github submodules if they exist
if [ -f .gitmodules ]; then
    git submodule update --init --recursive
fi

# Install dependencies from all requirement files if they exist
shopt -s nullglob
for file in requirements*.txt; do
    echo "Installing from $file"
    pip install -r "$file"
done

# Install additional required dependencies
if [ -f /local/projects_requirements/${PROJECT}_requirements.txt ]; then
    echo "Installing additional required dependencies from local/projects_requirements/${PROJECT}_requirements.txt"
    pip install -r /local/projects_requirements/${PROJECT}_requirements.txt
else
    echo "No additional required dependencies found in local/projects_requirements/${PROJECT}_requirements.txt"
fi

# Install the project with all optional dependencies
pip install .

# Record the start time of the test execution
TEST_START_TIME=$(python3 -c 'import time; print(time.time())')

# Run PyMOP
timeout -k 9 3600 pytest -W ignore::DeprecationWarning --path=$PWD/../pymop-artifacts-rv/pymop/specs-new \
       --algo=D \
       --continue-on-collection-errors \
       --json-report \
       --json-report-indent=2 \
       --statistics \
       --statistics_file=D.json > "${PROJECT}_Output.txt"
exit_code=$?

# Process test results if no timeout occurred
if [ $exit_code -ne 124 ] && [ $exit_code -ne 137 ]; then
    # Record the end time and calculate the test execution duration
    TEST_END_TIME=$(python3 -c 'import time; print(time.time())')
    TEST_TIME=$(python3 -c "print($TEST_END_TIME - $TEST_START_TIME)")

    # Display the last few lines of the test output for quick status check
    tail -n 3 ${PROJECT}_Output.txt
else
    echo "Timeout occurred"
    TEST_TIME="Timeout"
fi

# Go back to parent directory
cd ..

# Create output directory
mkdir -p "${PROJECT}_pymop_output"

# Save test results
RESULTS_FILE="${PROJECT}_pymop_output/${PROJECT}_results.txt"
echo "Test Time: ${TEST_TIME}s" >> $RESULTS_FILE

# Copy all output files
cp "${PROJECT}-pymop/${PROJECT}_Output.txt" "${PROJECT}_pymop_output/"
cp "${PROJECT}-pymop/.report.json" "${PROJECT}_pymop_output/.report.json"
cp "${PROJECT}-pymop/D-full.json" "${PROJECT}_pymop_output/D-full.json"
cp "${PROJECT}-pymop/D-time.json" "${PROJECT}_pymop_output/D-time.json"
cp "${PROJECT}-pymop/D-violations.json" "${PROJECT}_pymop_output/D-violations.json"

# Copy the folder to local directory (remove the old one first if it exists)
mkdir -p /local/continuous-analysis-output
cp -r "${PROJECT}_pymop_output" /local/continuous-analysis-output/
rm -rf "${PROJECT}_pymop_output"

# Print success message
echo "PyMOP completed for $PROJECT"
echo "Output files saved in /local/continuous-analysis-output/${PROJECT}_pymop_output/" 