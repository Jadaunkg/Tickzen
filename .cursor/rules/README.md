# TickZen Cursor Rules System

This directory contains specialized rule files for Cursor AI to assist with production-ready development.

## Overview

The rules system provides context-aware guidance for different aspects of the TickZen project. Each rule is automatically applied based on the files you're working on.

## Rule Files

### 1. Testing Standards
**Path:** `testing-standards/RULE.md`  
**Applies to:** `**/*test*.py`, `**/testing/**`, `**/tests/**`  
**Always Apply:** No

Comprehensive testing patterns including:
- Unit, integration, and end-to-end test structures
- Mock Firebase and SocketIO patterns
- Test fixtures and pytest configuration
- 80% coverage requirement for business logic
- WordPress publishing test patterns

### 2. Production Deployment
**Path:** `production-deployment/RULE.md`  
**Applies to:** `**/wsgi.py`, `**/gunicorn.conf.py`, `startup.*`  
**Always Apply:** No

Azure App Service deployment guidance:
- 20-section pre-deployment checklist
- Gunicorn configuration verification (1 worker, 100 threads)
- Firestore indexes and security rules
- Health check implementation
- Blue-green deployment procedures
- Rollback procedures

### 3. Error Handling ⚡
**Path:** `error-handling/RULE.md`  
**Applies to:** All files  
**Always Apply:** **Yes**

Universal error handling patterns:
- 4-level error hierarchy (Critical→Feature→User→Expected)
- Firebase error patterns with availability checks
- SocketIO error handling with try-except wrappers
- API integration error handling with retry logic
- WordPress publishing error recovery
- Structured logging patterns

### 4. Firebase Operations
**Path:** `firebase-operations/RULE.md`  
**Applies to:** `**/*firebase*.py`, `**/*firestore*.py`  
**Always Apply:** No

Firebase best practices:
- Firestore document structures and query patterns
- Storage upload/download with retry logic
- Auth integration patterns
- Batch operations and transactions
- Security rules examples
- Caching strategies

### 5. SocketIO Patterns
**Path:** `socketio-patterns/RULE.md`  
**Applies to:** `main_portal_app.py`, `automation_scripts/*.py`, `templates/run_automation*.html`  
**Always Apply:** No

Real-time progress tracking:
- Connection handling and room management
- Progress emission patterns
- Client-side JavaScript patterns
- Pause/resume automation
- Multi-user support
- Performance throttling

### 6. API Integration
**Path:** `api-integration/RULE.md`  
**Applies to:** `data_processing_scripts/*.py`, `analysis_scripts/*.py`, `**/*gemini*.py`  
**Always Apply:** No

External API patterns for:
- yfinance (stock data)
- Alpha Vantage (financial data with rate limiting)
- Finnhub (earnings calendar, company profiles)
- FRED (economic indicators)
- Google Gemini (AI content generation)
- Perplexity (AI research)
- WordPress REST API (publishing)
- Caching and fallback strategies

### 7. Code Quality ⚡
**Path:** `code-quality/RULE.md`  
**Applies to:** All files  
**Always Apply:** **Yes**

Development standards:
- PEP 8 compliance (naming, imports, formatting)
- Type hints for all functions
- Docstrings (Google style)
- Specific exception handling
- Structured logging
- Testing standards
- Code review checklist

## How It Works

### Automatic Application

Cursor automatically loads relevant rules based on:

1. **File Patterns (globs):** When you open/edit a file matching the pattern, that rule activates
2. **Always Apply:** Rules marked `alwaysApply: true` are active for all files

### Example Scenarios

**Scenario 1: Working on tests**
```
You open: testing/test_automation.py
Active rules: 
  - testing-standards (matches **/*test*.py)
  - error-handling (always apply)
  - code-quality (always apply)
```

**Scenario 2: Deploying to production**
```
You open: wsgi.py
Active rules:
  - production-deployment (matches **/wsgi.py)
  - error-handling (always apply)
  - code-quality (always apply)
```

**Scenario 3: Firebase operations**
```
You open: config/firebase_admin_setup.py
Active rules:
  - firebase-operations (matches **/*firebase*.py)
  - error-handling (always apply)
  - code-quality (always apply)
```

**Scenario 4: Adding API integration**
```
You open: data_processing_scripts/data_collection.py
Active rules:
  - api-integration (matches data_processing_scripts/*.py)
  - error-handling (always apply)
  - code-quality (always apply)
```

## Using the Rules

### In Cursor Chat

Simply ask questions relevant to your current file:

```
You: How should I structure this test?
Cursor: [Uses testing-standards rule to provide pytest patterns]

You: What's the proper error handling pattern here?
Cursor: [Uses error-handling rule for Firebase/SocketIO/API patterns]

You: How do I deploy this change?
Cursor: [Uses production-deployment rule for Azure checklist]
```

### Code Completions

Cursor will suggest code following the patterns in active rules:

- Type hints will be suggested
- Error handling patterns will auto-complete
- Firebase availability checks will be recommended
- Logging statements will follow structured format

## Rule Frontmatter

Each rule file has YAML frontmatter:

```yaml
---
description: "Brief description of what this rule covers"
alwaysApply: true|false  # Apply to all files or only matching globs
globs:  # File patterns this rule applies to
  - "**/*.py"
  - "src/**"
---
```

## Best Practices

1. **Don't modify rule files during active development** - These are reference guides
2. **Use specific questions** - "How do I handle Firebase errors?" vs "Help me code"
3. **Trust the patterns** - Rules are based on production TickZen architecture
4. **Check pre-deployment checklists** - Especially production-deployment rule
5. **Follow code quality standards** - Enforced automatically in all files

## Customization

To add a new rule:

1. Create a directory: `.cursor/rules/your-rule-name/`
2. Create `RULE.md` with frontmatter:
   ```yaml
   ---
   description: "Your rule description"
   alwaysApply: false
   globs:
     - "**/your/pattern/**"
   ---
   ```
3. Add your patterns, examples, and guidance
4. Restart Cursor for changes to take effect

## Troubleshooting

### Rule not applying?
- Check file path matches glob pattern
- Verify frontmatter YAML syntax
- Restart Cursor

### Too many rules active?
- Use more specific glob patterns
- Set `alwaysApply: false` for specialized rules

### Conflicting guidance?
- Error handling and code quality are universal (alwaysApply: true)
- Specialized rules (firebase, socketio) take precedence for their domains

## Quick Reference

| Rule | Always Apply | Key Focus |
|------|--------------|-----------|
| testing-standards | No | Test structure, mocks, coverage |
| production-deployment | No | Azure deployment, checklists |
| **error-handling** | **Yes** | Error patterns (all code) |
| firebase-operations | No | Firestore, Storage, Auth |
| socketio-patterns | No | Real-time progress updates |
| api-integration | No | External APIs, retry logic |
| **code-quality** | **Yes** | PEP 8, type hints, docs |

## Support

For questions about TickZen architecture or these rules:
1. Check `.cursorrules` file for project overview
2. Review relevant RULE.md in this directory
3. Check MASTER_DOCUMENTATION.md for detailed project info
4. Review NAVIGATION_REDESIGN_ROADMAP.md for current architecture plans

---

**Last Updated:** January 2025  
**TickZen Version:** 2.0  
**Cursor Compatibility:** Cursor v0.40+
