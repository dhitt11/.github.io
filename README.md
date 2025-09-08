# .github.io

Mental Health Apps Website - A GitHub Pages site providing expert reviews and comparisons of mental health applications.

## VS Code Setup & GitHub Integration

This repository is configured for optimal development with Visual Studio Code and GitHub integration.

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/dhitt11/.github.io.git
   cd .github.io
   ```

2. **Open in VS Code:**
   ```bash
   code .
   ```

3. **Install recommended extensions:**
   - VS Code will automatically prompt you to install recommended extensions
   - Or manually install from the Extensions panel (Ctrl+Shift+X)

### Recommended Extensions

The following extensions are automatically recommended for this project:

- **GitHub Integration:**
  - GitHub Pull Requests and Issues
  - GitHub Copilot & Copilot Chat
  - GitHub Issue Notebooks

- **Web Development:**
  - Live Server (for local development)
  - Auto Rename Tag
  - HTML CSS Support
  - Path Intellisense
  - Prettier (code formatting)

### Development Workflow

1. **Local Development:**
   - Use `Ctrl+Shift+P` → "Live Server: Open with Live Server" to preview changes
   - Or use the Task: "Open with Live Server" from the Command Palette

2. **Git Integration:**
   - VS Code is configured for seamless Git operations
   - Use the Source Control panel (Ctrl+Shift+G) for staging and commits
   - Available tasks: Git Status, Git Add All, Git Commit

3. **Code Formatting:**
   - Files are automatically formatted on save
   - Manual formatting: `Shift+Alt+F`

### Project Structure

```
.github.io/
├── .vscode/              # VS Code configuration
│   ├── settings.json     # Editor settings
│   ├── extensions.json   # Recommended extensions
│   ├── tasks.json        # Build and development tasks
│   └── launch.json       # Debug configurations
├── index.html            # Main website file
├── README.md             # This file
└── .gitignore           # Git ignore rules
```

### GitHub Pages

This site is automatically deployed to GitHub Pages at: `https://dhitt11.github.io`

Any changes pushed to the main branch will be automatically deployed.