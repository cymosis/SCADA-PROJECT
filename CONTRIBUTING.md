# Contributing to NT-SCADA

Thank you for contributing to the NT-SCADA project! This guide will help you contribute effectively.

---

## 🤝 Team Workflow

### Branch Strategy

We use **feature branches** for all changes:

```
main (protected)
  ├── feature/your-feature-name
  ├── bugfix/issue-description
  └── docs/documentation-update
```

**Never push directly to `main`!**

---

## 🚀 Contributing Process

### Step 1: Get Latest Code

```bash
# Navigate to project
cd NT-SCADA-LOCAL-TEST

# Pull latest from main
git checkout main
git pull origin main
```

### Step 2: Create Feature Branch

```bash
# Create and switch to new branch
git checkout -b feature/your-feature-name

# Examples:
# feature/ml-model-training
# feature/alert-system
# bugfix/kafka-connection-timeout
# docs/api-documentation
```

### Step 3: Make Your Changes

- Write clean, documented code
- Follow existing code style
- Test locally before committing
- Update documentation if needed

### Step 4: Commit Your Changes

```bash
# Check what changed
git status

# Add files
git add file1.py file2.py
# Or add all changes:
git add .

# Commit with descriptive message
git commit -m "Add feature: Real-time anomaly detection dashboard"
```

**Good commit messages:**
- ✅ "Add Grafana dashboard for Stage P1 sensors"
- ✅ "Fix: Kafka consumer timeout in stream processor"
- ✅ "Docs: Update setup guide with Docker troubleshooting"

**Bad commit messages:**
- ❌ "Update"
- ❌ "Fix bug"
- ❌ "Changes"

### Step 5: Push Your Branch

```bash
# Push branch to GitHub
git push origin feature/your-feature-name
```

### Step 6: Create Pull Request

1. **Go to GitHub**: https://github.com/cymosis/SCADA-PROJECT
2. **Click**: "Compare & pull request" (yellow banner)
3. **Fill in**:
   - Title: Clear description of changes
   - Description: What you changed and why
   - Link any related issues
4. **Assign reviewers**: Tag team members
5. **Click**: Create pull request

### Step 7: Code Review

- Team members will review your code
- Address any feedback
- Make additional commits if needed
- Once approved, changes will be merged

---

## 📝 Commit Message Guidelines

### Format

```
<type>: <subject>

<body (optional)>

<footer (optional)>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code formatting (no logic change)
- **refactor**: Code restructuring
- **test**: Adding tests
- **chore**: Maintenance tasks

### Examples

```
feat: Add ML anomaly detection model

Implemented binary classification model using scikit-learn
for real-time anomaly detection in sensor data.

- Trained on SWaT attack dataset
- Achieves 95% accuracy on test set
- Integrated with stream processor

Closes #23
```

```
fix: Resolve Kafka consumer timeout

Stream processor was timing out when Kafka was slow to start.
Added retry logic with exponential backoff.

Fixes #45
```

---

## 🧪 Testing Guidelines

### Before Committing

```bash
# Test your code locally
python your_script.py

# Check Docker services
docker-compose up -d
docker-compose ps

# Run any tests
python -m pytest tests/
```

### Test Checklist

- [ ] Code runs without errors
- [ ] Docker services start successfully
- [ ] Data flows through pipeline
- [ ] Grafana dashboard displays correctly
- [ ] No breaking changes to existing features
- [ ] Documentation updated if needed

---

## 📂 What to Commit

### ✅ DO Commit

- Source code (Python scripts)
- Configuration files (YAML, conf)
- Documentation (Markdown files)
- Requirements.txt updates
- Grafana dashboard JSONs
- Small test data samples

### ❌ DON'T Commit

- Large data files (>10MB)
- Model files (*.pkl, *.h5) - use Git LFS
- Log files (*.log)
- Temporary files
- IDE config (.vscode/, .idea/)
- Virtual environments (venv/)
- Docker volumes data
- Compiled Python files (*.pyc, __pycache__)

**Our .gitignore handles most of this automatically**

---

## 📐 Code Style

### Python

- Follow **PEP 8** guidelines
- Use **4 spaces** for indentation (not tabs)
- Maximum line length: **88 characters** (Black formatter)
- Add **docstrings** to functions and classes
- Use **type hints** where helpful

### Example

```python
def process_sensor_data(
    sensor_id: str, 
    value: float, 
    timestamp: str
) -> dict:
    """
    Process raw sensor data and return formatted dict.
    
    Args:
        sensor_id: Sensor identifier (e.g., 'FIT_101')
        value: Sensor reading value
        timestamp: ISO format timestamp
        
    Returns:
        Dictionary with processed sensor data
    """
    return {
        'id': sensor_id,
        'value': round(value, 2),
        'timestamp': timestamp
    }
```

---

## 📚 Documentation

### Update Documentation When:

- Adding new features
- Changing configurations
- Fixing bugs that affect users
- Adding dependencies

### Documentation Files

- **README.md**: Update if architecture changes
- **SETUP_GUIDE.md**: Update for new setup steps
- **GRAFANA_SETUP.md**: Update for dashboard changes
- **CHANGELOG.md**: Always update with your changes
- **Code comments**: Explain complex logic

---

## 🐛 Reporting Issues

### Before Creating an Issue

1. Check if issue already exists
2. Try troubleshooting steps in documentation
3. Test on latest `main` branch

### Creating an Issue

Include:
- **Title**: Clear, concise description
- **Description**: What happened vs. what you expected
- **Steps to reproduce**
- **Environment**: OS, Docker version, Python version
- **Logs**: Relevant error messages
- **Screenshots**: If applicable

**Template:**
```markdown
## Description
Brief description of the issue

## Steps to Reproduce
1. Start services with `docker-compose up -d`
2. Run sensor producer
3. ...

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: Windows 11
- Docker: 24.0.0
- Python: 3.9.0

## Logs
```
[Paste relevant logs here]
```

## Screenshots
[If applicable]
```

---

## 👥 Team Communication

### Daily Standup (Optional)
- What did you work on?
- What will you work on?
- Any blockers?

### Pull Request Reviews
- Review within 24 hours
- Be constructive and respectful
- Ask questions if unclear
- Approve when satisfied

### Asking for Help
- Post in team chat/channel
- Tag relevant team members
- Provide context and what you've tried
- Share error messages

---

## 🎯 Task Assignment

### Claiming Tasks
1. Check GitHub Issues or Project Board
2. Comment "I'll work on this"
3. Get assigned by team lead
4. Create branch and start work

### Current Priorities
Check our [Project Board](https://github.com/cymosis/SCADA-PROJECT/projects) for:
- High priority tasks
- In progress work
- Available tasks

---

## ✅ Pull Request Checklist

Before submitting PR:

- [ ] Code follows project style guidelines
- [ ] Tested locally and works correctly
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No merge conflicts with main
- [ ] Commit messages are clear
- [ ] No sensitive data in commits
- [ ] requirements.txt updated (if dependencies added)

---

## 🚨 Emergency Fixes

For critical bugs in production:

1. **Create hotfix branch**: `hotfix/critical-bug-name`
2. **Fix and test thoroughly**
3. **Create PR** with "URGENT" in title
4. **Get immediate review**
5. **Merge** after approval
6. **Notify team**

---

## 📞 Questions?

- Team Lead: [Contact info]
- Slack/Discord: [Channel name]
- Email: [Team email]
- GitHub Discussions: [Link]

---

## 🎓 Learning Resources

- [Git Basics](https://git-scm.com/book/en/v2/Getting-Started-Git-Basics)
- [Docker Documentation](https://docs.docker.com/)
- [Python Style Guide](https://pep8.org/)
- [Writing Good Commit Messages](https://chris.beams.io/posts/git-commit/)

---

**Thank you for contributing! 🚀**

**Last Updated**: November 2025
