#!/bin/bash

# DyLin Test Runner Script
# Usage: ./run_dylin.sh <project_name>

PROJECT=$1

if [ -z "$PROJECT" ]; then
    echo "Usage: $0 <project_name>"
    exit 1
fi

# Print project name
echo "Running DyLin Test for project: $PROJECT"

# ===== Install the project =====

# Go to project directory
cd "$PROJECT-dylin"

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

# Return back to the parent directory
cd ..

# ===== Install DyLin and dependencies =====

# Set the temporary directory to /tmp
TMPDIR=/tmp
echo "TMPDIR: $TMPDIR"

# Define the fixed repository URL for the DyLin project
DYLIN_REPO_URL="https://github.com/AryazE/DyLin.git"

# Clone DyLin
git clone "$DYLIN_REPO_URL" DyLin

# Install the tool and its dependencies
cd DyLin
pip install -r requirements.txt
pip install .

# Return back to the parent directory
cd ..

# ===== Prepare to run the tests with DyLin =====

# Generate a unique session ID for the DynaPyt run (in order to run multiple analyses in one run)
export DYNAPYT_SESSION_ID=$(uuidgen)
echo "DynaPyt Session ID: $DYNAPYT_SESSION_ID"

# Remove DyLin source files
rm -rf ./DyLin

# Select analyses
python3 -m dylin.select_checkers \
    --include="All" \
    --exclude="None" \
    --output_dir="${TMPDIR}/dynapyt_output-${DYNAPYT_SESSION_ID}" > analyses.txt

# Copy analyses file
cp analyses.txt "${TMPDIR}/dynapyt_analyses-${DYNAPYT_SESSION_ID}.txt"

# ===== Run the Instrumentation =====

# Go to the project directory
cd "$PROJECT-dylin"

# Record the start time of the instrumentation process
INSTRUMENTATION_START_TIME=$(python3 -c 'import time; print(time.time())')

# Run the instrumentation
python3 -m dynapyt.run_instrumentation \
    --directory="." \
    --analysisFile="${TMPDIR}/dynapyt_analyses-${DYNAPYT_SESSION_ID}.txt"

# Record the end time and calculate the instrumentation duration
INSTRUMENTATION_END_TIME=$(python3 -c 'import time; print(time.time())')
INSTRUMENTATION_TIME=$(python3 -c "print($INSTRUMENTATION_END_TIME - $INSTRUMENTATION_START_TIME)")

# ===== Run the tests =====

# Record the start time of the test execution
TEST_START_TIME=$(python3 -c 'import time; print(time.time())')

# Run dylin
timeout -k 9 3600 pytest -W ignore::DeprecationWarning > ${PROJECT}_Output.txt
exit_code=$?

# Process test results if no timeout occurred
if [ $exit_code -ne 124 ] && [ $exit_code -ne 137 ]; then
    # Calculate test duration
    TEST_END_TIME=$(python3 -c 'import time; print(time.time())')
    TEST_TIME=$(python3 -c "print($TEST_END_TIME - $TEST_START_TIME)")

    # Show test summary
    tail -n 3 ${PROJECT}_Output.txt
else
    echo "Timeout occurred"
    TEST_TIME="Timeout"
fi

# ===== Generate the findings report (no coverage) =====

# Record the start time of the post-run process
POST_RUN_START_TIME=$(python3 -c 'import time; print(time.time())')

# Run dylin post-run process
python3 -m dynapyt.post_run \
    --coverage_dir="" \
    --output_dir="${TMPDIR}/dynapyt_output-${DYNAPYT_SESSION_ID}"

python3 -m dylin.format_output \
    --findings_path="${TMPDIR}/dynapyt_output-${DYNAPYT_SESSION_ID}/output.json" > ${PROJECT}_findings.txt

# Record Post-Run end time
POST_RUN_END_TIME=$(python3 -c 'import time; print(time.time())')
POST_RUN_TIME=$(python3 -c "print($POST_RUN_END_TIME - $POST_RUN_START_TIME)")

# ===== Store results =====

# Go back to parent directory
cd ..

# Create output directory
mkdir -p "${PROJECT}_dylin_output"

# Save test results
RESULTS_FILE="${PROJECT}_dylin_output/${PROJECT}_results.txt"
echo "Instrumentation Time: ${INSTRUMENTATION_TIME}s" >> $RESULTS_FILE
echo "Test Time: ${TEST_TIME}s" >> $RESULTS_FILE
echo "Post-Run Time: ${POST_RUN_TIME}s" >> $RESULTS_FILE

# Copy the ${PROJECT}_findings.txt file to the $CLONE_DIR directory
cp "${PROJECT}-dylin/${PROJECT}_findings.txt" "${PROJECT}_dylin_output/"

# Copy the ${PROJECT}_Output.txt file to the $CLONE_DIR directory
cp "${PROJECT}-dylin/${PROJECT}_Output.txt" "${PROJECT}_dylin_output/"

# Copy the /tmp/dynapyt_output-454852b3-74be-498a-8968-c1bceaaf3293/findings.csv and output.json files to the $CLONE_DIR directory
# Rename them to temp_findings.csv and temp_output.json
cp "${TMPDIR}/dynapyt_output-${DYNAPYT_SESSION_ID}/findings.csv" "${PROJECT}_dylin_output/temp_findings.csv"
cp "${TMPDIR}/dynapyt_output-${DYNAPYT_SESSION_ID}/output.json" "${PROJECT}_dylin_output/temp_output.json"

# Copy the folder to local directory (remove the old one first if it exists)
mkdir -p ./continuous-analysis-output
cp -r "${PROJECT}_dylin_output" ./continuous-analysis-output/
rm -rf "${PROJECT}_dylin_output"

# Print success message
echo "DyLin completed for $PROJECT"
echo "Output files saved in /continuous-analysis-output/${PROJECT}_dylin_output/"
