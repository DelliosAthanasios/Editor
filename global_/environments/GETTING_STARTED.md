# Getting Started with Docker Environments in Third Edit

Welcome! This guide will walk you through setting up and using Docker environments in Third Edit.

## Prerequisites

- **Docker Desktop** (Windows/macOS) or Docker CLI (Linux)
- **Third Edit** editor running
- **Internet connection** (for initial image downloads)

## Step-by-Step Setup (5 Minutes)

### Step 1: Install Docker

**If you don't have Docker installed:**

#### Windows
1. Go to https://www.docker.com/products/docker-desktop
2. Click "Download for Windows"
3. Run the installer
4. Choose "WSL 2" during installation
5. Restart your computer
6. Launch Docker Desktop from Start menu

#### macOS
1. Go to https://www.docker.com/products/docker-desktop
2. Click "Download for Mac"
3. Open the .dmg file
4. Drag Docker to Applications folder
5. Launch Docker from Applications

#### Linux
```bash
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo usermod -aG docker $USER
# Log out and log back in
```

### Step 2: Create Your First Environment

1. **Open Third Edit**
2. **Click Environments menu** in the menu bar
3. **Select "Create Environment"**

You'll see two options:
- **Pre-configured Environments** (recommended for first-time)
- **Custom** (for advanced users)

### Step 3: Choose an Environment

Click **"Pre-configured Environments"** to see available options:

```
Lisp Machine       → Lisp/Scheme development
C Development      → C with GCC, GDB, Valgrind
C++ Modern         → Modern C++ with Boost
Python Data Science → Python with Jupyter, NumPy, Pandas
Web Development    → Node.js, Express, React
Rust Workspace     → Rust with Cargo
Go Development     → Go with Delve debugger
Java Enterprise    → Java with Maven, Spring
Ruby/Rails         → Ruby with Rails
Haskell Stack      → Haskell with Stack
```

### Step 4: Build and Run

Click **"Create Environment"**

You'll see a progress dialog showing:
- "Building Docker image..." (downloads packages, ~2-5 minutes first time)
- "Starting container..." (launches environment)
- "✓ Environment ready!" (click OK to finish)

**That's it! Your environment is ready.**

## Using Your Environment

### Execute a File

**Method 1: From Menu**
1. Open a code file in the editor
2. Go to **Tools** → **Execute in Container**
3. Select your environment
4. Output appears in console

**Method 2: From Keyboard**
```
Ctrl+Shift+E → Select environment → Run
```

### Example: Run Python Code

1. Create a file: `test.py`
```python
import numpy as np
print("NumPy version:", np.__version__)
print("Hello from Python Data Science environment!")
```

2. Go to **Environments** → **Manage Environments**
3. You'll see "Python Data Science" listed
4. Click "Actions" → "Execute"
5. Output shows in console

### Example: Build a C Program

1. Create: `hello.c`
```c
#include <stdio.h>
int main() {
    printf("Hello from C!\n");
    return 0;
}
```

2. Select **"C Development"** environment
3. Execute command: `gcc hello.c -o hello && ./hello`
4. See output in console

### Example: Run a Web Server

1. Select **"Web Development"** environment
2. Execute: `npm init -y && npm install express`
3. Create `server.js`:
```javascript
const express = require('express');
const app = express();
app.get('/', (req, res) => res.send('Hello from Docker!'));
app.listen(3000, () => console.log('Server running on port 3000'));
```
4. Execute: `node server.js`
5. Open browser: http://localhost:3000

## Managing Environments

### View All Environments

**Environments** → **Manage Environments**

Shows:
- Name and language
- Current status (running/stopped)
- Container ID
- Action buttons

### Stop an Environment

1. Go to **Manage Environments**
2. Select environment
3. Click **Actions** → **Stop**

The container pauses but retains all files and packages.

### Remove an Environment

1. Go to **Manage Environments**
2. Select a stopped environment
3. Click **Actions** → **Remove**

**Note**: This deletes the container (image remains for rebuilding).

### Restart an Environment

1. Go to **Manage Environments**
2. Click **Refresh**
3. Stopped environments can be restarted (coming in next update)

## Tips & Tricks

### 1. Workspace Automatic Mounting
Your project folder is automatically available at `/workspace` in all containers.

Local files ↔ Container `/workspace` (auto-synced)

### 2. Install Packages On-the-Fly
While environment is running, execute:
```
pip install package-name          # Python
npm install package-name          # Node.js
cargo add crate-name              # Rust
go get github.com/user/package    # Go
```

All installations persist in that container.

### 3. Jupyter Notebooks
In **Python Data Science** environment, start Jupyter:
```
jupyter notebook --ip=0.0.0.0 --allow-root
```
Access at http://localhost:8888

### 4. Access Container Directly
Open system terminal and run:
```bash
docker exec -it editor-python-ds-container /bin/bash
```
Now you're in a shell inside the container!

### 5. View Container Output
In system terminal:
```bash
docker logs editor-python-ds-container
```

### 6. Multiple Environments
Create multiple environments for different projects:
- "Project A - Python"
- "Project B - Node"
- "Project C - Rust"

Each maintains its own packages and state.

## Common Tasks

### Task 1: Data Analysis with Jupyter
```
1. Environment: Python Data Science
2. Execute: jupyter lab
3. Open http://localhost:8888
4. Create notebook and write Python code
5. All libraries (numpy, pandas, sklearn) available
```

### Task 2: Full-Stack Development
```
1. Environment: Web Development
2. Backend: npm install && npm start
3. Port 3000: Access at http://localhost:3000
4. Port 5000: Backend API
5. Edit files locally, see changes in browser
```

### Task 3: Rust Project Development
```
1. Environment: Rust Workspace
2. Execute: cargo new myproject && cd myproject
3. Execute: cargo build
4. Execute: cargo test
5. Edit src/main.rs locally and test
```

### Task 4: Database Development
```
1. Create custom environment with PostgreSQL
2. Execute: psql -U developer
3. Create database and tables
4. Connect from application code
```

### Task 5: Compile C/C++ Code
```
1. Environment: C Development or C++ Modern
2. Execute: gcc myfile.c -o myprogram
3. Execute: ./myprogram
4. For C++: g++ myfile.cpp -o myprogram
```

## Status Bar Indicator

Watch the bottom status bar of Third Edit:

```
● Green circle = Docker is running
● Red circle   = Docker is not available

"Environments: 1 running" = Shows active containers
```

## Troubleshooting

### "Docker not installed" Error
✓ Solution: Install Docker Desktop and restart editor

### "Port 3000 already in use"
✓ Solution: Close the other app or change port in environment config

### Environment creation taking too long
✓ This is normal! First build downloads base image (2-5 min)
✓ Later builds are much faster (cached layers)

### "Permission denied" Error (Linux)
✓ Run: `sudo usermod -aG docker $USER`
✓ Log out and back in

### Container won't start
✓ Check available disk space: `docker system df`
✓ Clean up: `docker system prune`

## What Gets Saved

Third Edit automatically saves:

1. **Container State** → `.editor_containers.json`
   - Which environments you've created
   - Their configurations
   - Current status

2. **Files in Project** → `/workspace` in container
   - All your code files sync automatically
   - Changes persist even if container stops

3. **Installed Packages** → Inside container
   - pip packages (Python)
   - npm modules (Node.js)
   - Rust crates
   - etc.

## Accessing Services

Environments expose ports that you can access locally:

| Environment | Port | Service |
|-------------|------|---------|
| Web Dev | 3000 | Node.js/Express |
| Python DS | 8888 | Jupyter |
| Java | 8080 | Spring Boot |
| Go | 8080 | Go Server |
| Web Dev | 5000 | Second server |

Access with: `http://localhost:XXXX`

## Advanced: Custom Environments

For specialized setups:

1. Go to **Environments** → **Create Environment**
2. Select **"Custom"** tab
3. Enter:
   - Environment name
   - Base image (e.g., `ubuntu:22.04`)
   - Dockerfile content
4. Click **Create Environment**

Example Dockerfile:
```dockerfile
FROM python:3.11
RUN pip install numpy scipy matplotlib
RUN pip install pytorch torchvision
WORKDIR /workspace
CMD ["/bin/bash"]
```

## Performance Notes

- **First build**: 2-5 minutes (downloads ~300MB-1GB)
- **Subsequent builds**: 30 seconds (uses cached layers)
- **Storage**: Each full environment ~1-3GB
- **Memory**: Running container ~100MB-1GB depending on setup

## Next Steps

1. ✅ Install Docker (if needed)
2. ✅ Create your first environment
3. ✅ Run a simple program
4. ✅ Explore other pre-configured environments
5. ✅ Create a custom environment for your needs
6. ✅ Set up multiple environments for different projects

## Learning Resources

- **Docker Basics**: https://docs.docker.com/get-started/
- **Dockerfile Reference**: https://docs.docker.com/engine/reference/builder/
- **Language-Specific**: Check official language documentation

## Need Help?

- **Quick Issues?** Check "Troubleshooting" section above
- **More Info?** Read `README.md` in environments folder
- **Code Examples?** See `CONFIGURATION_EXAMPLES.md`
- **Technical Details?** Check `IMPLEMENTATION_GUIDE.md`

---

## Quick Reference

```
Environments Menu Structure:
├── Create Environment      → Choose from 10 pre-configured
├── Pre-configured          → Submenu with all 10 options
│   ├── Lisp Machine
│   ├── C Development
│   ├── C++ Modern
│   ├── Python Data Science
│   ├── Web Development
│   ├── Rust Workspace
│   ├── Go Development
│   ├── Java Enterprise
│   ├── Ruby/Rails
│   └── Haskell Stack
├── Manage Environments     → View, stop, remove containers
└── Environment Settings    → Docker status and info
```

## Success Indicators

You'll know it's working when you see:

✓ Environment listed in "Manage Environments"
✓ Status shows "running"
✓ Status bar shows "Green ●"
✓ Code executes and shows output
✓ Files persist between sessions
✓ Can access exposed services (http://localhost:XXXX)

---

**Welcome to containerized development in Third Edit! Happy coding! 🚀**

For detailed information, see the complete documentation in `global_/environments/`
