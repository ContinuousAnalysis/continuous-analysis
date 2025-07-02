import os, csv, json, subprocess, requests
from urllib.parse import urlparse


# Define file paths
PROJECTS = "projects.csv"
STATE = "project_state.json"
CHANGED_PROJECTS = "changed_projects.txt"
API_BASE = "https://api.github.com/repos"

# Load state
state = {}
if os.path.exists(STATE):
    with open(STATE, "r") as f:
        state = json.load(f)

# Parse "owner/repo" from URL
def parse_owner_repo(url):
    return urlparse(url).path.strip("/")

# Get latest commit from GitHub
def get_latest(owner_repo):
    try:
        r = requests.get(f"{API_BASE}/{owner_repo}/commits")
        if r.status_code == 200 and isinstance(r.json(), list):
            return f"commit:{r.json()[0]['sha']}"
    except: pass

    return None

# Run PyMOP inside Docker
def run_pymop(project, url):
    docker_cmd = f"""
    docker run --rm \
        -v "{os.getcwd()}:/local" \
        pymop-runner \
        bash -c "set -euxo pipefail && \
        cp /local/scripts/run_pymop.sh /workspace/run_pymop.sh && \
        source /workspace/pymop-venv/bin/activate && \
        chmod +x /workspace/run_pymop.sh && \
        /workspace/run_pymop.sh {project} {url} && \
        deactivate"
    """
    proc = subprocess.run(docker_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(proc.stdout)
    print(proc.stderr)

# Main loop
changed_projects = []

with open(PROJECTS) as f:
    reader = csv.DictReader(f)
    for row in reader:
        project, url = row["project"], row["url"]
        key = project.lower()
        owner_repo = parse_owner_repo(url)
        latest = get_latest(owner_repo)

        if not latest:
            print(f"- {project}: unable to fetch version info")
            continue

        if state.get(key) != latest:
            print(f"Change detected for {project}: {latest}")
            print("\n--------------------------------\n")
            try:
                run_pymop(project, url)
                state[key] = latest
                changed_projects.append(project)
            except Exception as e:
                print(f"Failed to run PyMOP for {project}: {e}")
                print("Continuing with next project...")
        else:
            print(f"No change for {project}")

# Save updated state
with open(STATE, "w") as f:
    json.dump(state, f, indent=2)

# Save changed projects to a text file
if changed_projects:
    with open(CHANGED_PROJECTS, "w") as f:
        for project in changed_projects:
            f.write(f"{project}\n")
    print("\n--------------------------------\n")
    print(f"Saved {len(changed_projects)} changed projects to {CHANGED_PROJECTS}")
else:
    print("\n--------------------------------\n")
    print("No projects changed in this run")