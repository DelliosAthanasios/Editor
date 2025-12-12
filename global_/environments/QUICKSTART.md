# Environment Management - Quick Start Guide

## 5-Minute Setup

### Step 1: Install Docker (if not already installed)

**Windows/macOS**:
1. Download from https://www.docker.com/products/docker-desktop
2. Run installer and follow prompts
3. Restart your computer

**Linux**:
```bash
sudo apt-get install docker.io docker-compose
sudo usermod -aG docker $USER
# Log out and back in
```

### Step 2: Create Your First Environment

1. Launch Third Edit
2. Click **Environments** menu
3. Choose **Pre-configured Environments** → Select a language
4. Click **Create Environment**
5. Wait for image build and container startup (may take 2-5 minutes on first run)

### Step 3: Run Code in Your Environment

Once environment is running:

1. Go to **Environments** → **Manage Environments**
2. You'll see your environment listed with status "running"
3. Right-click file in editor and select "Execute in [Environment]"
4. Output appears in the console

## Common Tasks

### Running Python Code
```
1. Menu → Environments → Pre-configured → Python Data Science
2. Create Environment
3. Open your .py file
4. Menu → Tools → Execute in Container → Python Data Science
```

### Starting a Web Server
```
1. Create "Web Development" environment
2. Execute: cd /workspace && npm install && npm start
3. Access at http://localhost:3000
```

### Building C/C++ Projects
```
1. Create "C++ Modern" environment
2. Execute: cd /workspace && cmake . && make
```

### Running Tests
```
Environments → Manage Environments → [Your Environment] → Actions → Test
```

## Keyboard Shortcuts

- **Ctrl+Shift+E** - Open Environments menu
- **Ctrl+Shift+M** - Open Manage Environments

## Status Indicator

Look at the bottom status bar:
- **●** Green = Docker running
- **●** Red = Docker not available
- Shows "1 environment running" etc.

## Tips & Tricks

### 1. Persist Data
All files in `/workspace` are automatically saved to your local project directory.

### 2. Install Packages
While container is running, execute:
```
pip install numpy pandas  # Python
npm install express       # Node.js
cargo add serde          # Rust
```

### 3. Stop Without Deleting
Go to **Manage Environments** → Select environment → **Stop**
(Container can be restarted later)

### 4. View Container Terminal
Once created, open a terminal and type:
```bash
docker exec -it editor-[language]-container /bin/bash
```

### 5. Clean Up Old Images
If disk space is low:
```bash
docker image prune -a  # Remove unused images
```

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| "Docker not found" | Install Docker Desktop and restart editor |
| "Port already in use" | Another app using that port; change mapping or close app |
| Build takes forever | Normal for first build; images are cached after |
| "Permission denied" | Linux: Run `sudo usermod -aG docker $USER` |
| Out of disk space | Run `docker system prune` |

## Next Steps

- Check main README for advanced usage
- Explore custom environment creation
- Set up multiple environments for different projects
- Configure port mappings and volume mounts

Happy coding! 🚀
