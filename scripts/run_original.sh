#!/bin/bash

# Original Test Runner Script
# Usage: ./run_original.sh <project_name>

PROJECT=$1

if [ -z "$PROJECT" ]; then
    echo "Usage: $0 <project_name>"
    exit 1
fi

# Print project name
echo "Running Original Test for project: $PROJECT"

# Go to project directory
cd "$PROJECT-original"

# Get the commit timestamp and commit message from the git log
commit_timestamp=$(git log -1 --format="%at" HEAD)
commit_message=$(git log -1 --format="%s" HEAD)
echo "Commit timestamp: $commit_timestamp"
echo "Commit message: $commit_message"

# Add the commit timestamp and commit message to the output file
echo "Commit timestamp:= $commit_timestamp" >> ${PROJECT}_commit_info.txt
echo "Commit message:= $commit_message" >> ${PROJECT}_commit_info.txt

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
if [ -f ./../continuous-analysis/projects_requirements/${PROJECT}_requirements.txt ]; then
    echo "Installing additional required dependencies from $PWD/../continuous-analysis/projects_requirements/${PROJECT}_requirements.txt"
    pip install -r ./../continuous-analysis/projects_requirements/${PROJECT}_requirements.txt
else
    echo "No additional required dependencies found in $PWD/../continuous-analysis/projects_requirements/${PROJECT}_requirements.txt"
fi

# Install the project with all optional dependencies
pip install .

#Install pytest and pytest-cov
pip install pytest
pip install pytest-cov

# Record the start time of the test execution
TEST_START_TIME=$(python3 -c 'import time; print(time.time())')

# Run PyMOP with coverage
timeout -k 9 3600 pytest -W ignore::DeprecationWarning \
                         --continue-on-collection-errors \
                         --cov=${PROJECT} \
                         --cov-report=xml:${PROJECT}_coverage.xml \
                         > "${PROJECT}_Output.txt"
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
mkdir -p "${PROJECT}_original_output"

# Save test results
RESULTS_FILE="${PROJECT}_original_output/${PROJECT}_results.txt"
echo "Test Time: ${TEST_TIME}s" >> $RESULTS_FILE

# Copy all output files
cp "${PROJECT}-original/${PROJECT}_Output.txt" "${PROJECT}_original_output/"
cp "${PROJECT}-original/${PROJECT}_coverage.xml" "${PROJECT}_original_output/"
cp "${PROJECT}-original/${PROJECT}_commit_info.txt" "${PROJECT}_original_output/"

# Copy the folder to local directory (remove the old one first if it exists)
mkdir -p ./continuous-analysis-output
cp -r "${PROJECT}_original_output" ./continuous-analysis-output/
rm -rf "${PROJECT}_original_output"

# Print success message
echo "Original Test completed for $PROJECT"
echo "Output files saved in /continuous-analysis-output/${PROJECT}_original_output/" 
