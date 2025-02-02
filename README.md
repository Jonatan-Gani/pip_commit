# **Automatic Requirements Generation with Git Pre-Commit Hook**

## **Overview**

This setup automatically generates and updates a `requirements.txt` file every time you commit changes in a Git repository. It ensures that dependencies are always up to date and optionally removes unwanted packages. This solution is implemented as a **global Git pre-commit hook**, meaning it applies to all repositories on your system.

---

## **Features**

- Automatically runs before each commit.
- Generates `requirements.txt` in the repository root.
- Optionally removes specific unwanted dependencies.
- Ensures `requirements.txt` is correctly staged for commit.

---

## **Setup Instructions**

### **1. Create a Global Hooks Directory**

Run the following command in **Git Bash**:

```sh
mkdir -p ~/.global-git-hooks
```

### **2. Configure Git to Use the Global Hooks Directory**

```sh
git config --global core.hooksPath ~/.global-git-hooks
```

### **3. Create the Pre-Commit Hook**

Open the hook file in an editor:

```sh
touch ~/.global-git-hooks/pre-commit
nano ~/.global-git-hooks/pre-commit
```

Paste the following **shell script**:

```sh
#!/bin/sh
echo "=== Running Global Pre-Commit Hook ==="

# Get the Git repository root directory
REPO_PATH=$(git rev-parse --show-toplevel)
echo "Detected repository path: $REPO_PATH"

# Navigate to the repository folder
cd "$REPO_PATH" || exit

# Generate requirements.txt inside the repository
pip freeze > "$REPO_PATH/requirements.txt"

# Verify if the file was created
if [ -f "$REPO_PATH/requirements.txt" ]; then
    echo "requirements.txt was created successfully."
else
    echo "ERROR: requirements.txt was NOT created!"
    exit 1
fi

# Optionally remove lines containing specific dependencies (customize as needed)
REMOVE_DEP="ibapi"
if [ -n "$REMOVE_DEP" ]; then
    grep -iv "$REMOVE_DEP" "$REPO_PATH/requirements.txt" > "$REPO_PATH/temp.txt" && mv "$REPO_PATH/temp.txt" "$REPO_PATH/requirements.txt"
fi

# Ensure the file is staged for commit
git add "$REPO_PATH/requirements.txt" || echo "WARNING: Failed to stage requirements.txt"

# Check if the file is staged
if git diff --cached --name-only | grep -q "requirements.txt"; then
    echo "requirements.txt is staged successfully."
else
    echo "WARNING: requirements.txt is still untracked."
fi

echo "=== Pre-Commit Hook Completed Successfully ==="
exit 0
```

### **4. Make the Hook Executable**

Run this in **Git Bash**:

```sh
chmod +x ~/.global-git-hooks/pre-commit
```

### **5. Test the Hook**

Navigate to any Git repository and commit changes:

```sh
git add .
git commit -m "Testing automatic requirements generation"
```

If successful, the output will include:

```
requirements.txt was created successfully.
requirements.txt is staged successfully.
```

---

## **Final Notes**

This setup ensures that `requirements.txt` is **always generated and tracked**, reducing the risk of missing dependencies in your projects. Since it is configured **globally**, it works across all Git repositories on your system without additional setup per project.

If you encounter any issues, verify the **hook execution, Git configuration, and script permissions**. With this in place, you can ensure a consistent development environment with up-to-date dependencies for every commit and GitHub workflow execution.

