# **Automatic Requirements Generation with Git Pre-Commit Hook**

## **Overview**

This setup automatically generates and updates a `requirements.txt` file every time you commit changes in a Git repository. It ensures that dependencies are always up to date and optionally removes unwanted packages. This solution is implemented as a **global Git pre-commit hook**, meaning it applies to all repositories on your system.

---

## **Features**

- Prompts before generating a new `requirements.txt`.
- Automatically runs before each commit.
- Generates `requirements.txt` in the repository root.
- Optionally removes specific unwanted dependencies (e.g., `ibapi`).
- Ensures `requirements.txt` is correctly staged for commit.

---

## **Setup Instructions**

### **1. Create a Global Hooks Directory**

#### Git Bash / Linux / macOS:

```sh
mkdir -p ~/.global-git-hooks
```

#### Windows PowerShell:

```powershell
New-Item -ItemType Directory -Path "$HOME\.global-git-hooks" -Force
```

---

### **2. Configure Git to Use the Global Hooks Directory**

#### Git Bash / Linux / macOS:

```sh
git config --global core.hooksPath ~/.global-git-hooks
```

#### Windows PowerShell:

```powershell
git config --global core.hooksPath "$HOME\.global-git-hooks"
```

---

### **3. Create the Pre-Commit Hook**

#### Git Bash / Linux / macOS:

```sh
touch ~/.global-git-hooks/pre-commit
nano ~/.global-git-hooks/pre-commit
```

#### Windows PowerShell:

Use any text editor (e.g., Notepad, VS Code):

```powershell
notepad "$HOME\.global-git-hooks\pre-commit"
```

Paste the script inside the file and save.

---

### **4. Make the Hook Executable**

#### Git Bash / Linux / macOS:

```sh
chmod +x ~/.global-git-hooks/pre-commit
```

#### Windows:

Make sure the file has **Unix line endings (LF)** and Git is configured to use `sh` (comes with Git for Windows). No `chmod` needed if using Git Bash.

---

### **5. Test the Hook**

Navigate to any Git repository and make a commit:

```sh
git add .
git commit -m "Testing automatic requirements generation"
```

If successful, the output will include:

```
Do you want to regenerate requirements.txt from current environment? (y/n)
...
requirements.txt was created successfully.
requirements.txt is staged successfully.
```

---

## **Final Notes**

- The hook asks for confirmation before regenerating `requirements.txt`, giving you full control over when updates occur.
- It works globally across all Git repositories.
- For PowerShell users, ensure Git is installed with Bash support (default with Git for Windows).
- Customize the script to exclude additional dependencies if needed (via the `REMOVE_DEP` variable).
