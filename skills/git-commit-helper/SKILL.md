---
name: git-commit-helper
description: Generate descriptive commit messages from git diffs and review staged changes before committing (message quality only; /commit does the stage-and-push).
disable-model-invocation: true
---

# Git Commit Helper

## Quick start

Analyze staged changes and generate commit message:

```bash
# View staged changes
git diff --staged

# Generate commit message based on changes
# (Claude will analyze the diff and suggest a message)
```

## Commit message format

```
<type>: <description>

[optional body]

[optional footer]
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **refactor**: Code refactoring
- **docs**: Documentation changes
- **test**: Adding or updating tests
- **chore**: Maintenance tasks
- **perf**: Performance improvement
- **ci**: CI/CD changes

### Examples

**Feature commit:**
```
feat: add JWT authentication

Implement JWT-based authentication system with:
- Login endpoint with token generation
- Token validation middleware
- Refresh token support
```

**Bug fix:**
```
fix: handle null values in user profile

Prevent crashes when user profile fields are null.
Add null checks before accessing nested properties.
```

**Refactor:**
```
refactor: simplify query builder

Extract common query patterns into reusable functions.
Reduce code duplication in database layer.
```

## Commit message guidelines

**DO:**
- Use imperative mood ("add feature" not "added feature")
- Keep first line under 50 characters
- Capitalize first letter
- No period at end of summary
- Explain WHY not just WHAT in body

**DON'T:**
- Use vague messages like "update" or "fix stuff"
- Include technical implementation details in summary
- Write paragraphs in summary line
- Use past tense

## Multi-file commits

When committing multiple related changes:

```
refactor: restructure authentication module

- Move auth logic from controllers to service layer
- Extract validation into separate validators
- Update tests to use new structure
- Add integration tests for auth flow

Breaking change: Auth service now requires config object
```

## Breaking changes

Indicate breaking changes clearly:

```
feat!: restructure API response format

BREAKING CHANGE: All API responses now follow JSON:API spec

Previous format:
{ "data": {...}, "status": "ok" }

New format:
{ "data": {...}, "meta": {...} }

Migration guide: Update client code to handle new response structure
```

## Template workflow

1. **Review changes**: `git diff --staged`
2. **Identify type**: Is it feat, fix, refactor, etc.?
3. **Write summary**: Brief, imperative description
4. **Add body**: Explain why and what impact
5. **Note breaking changes**: If applicable

## Interactive commit helper

Use `git add -p` for selective staging:

```bash
# Stage changes interactively
git add -p

# Review what's staged
git diff --staged

# Commit with message
git commit -m "type: description"
```

## Amending commits

Only when the user explicitly asks to amend: otherwise create a new commit (global rule).

Fix the last commit message:

```bash
# Amend commit message only
git commit --amend

# Amend and add more changes
git add forgotten-file.js
git commit --amend --no-edit
```

## Best practices

1. **Atomic commits**: One logical change per commit
2. **Test before commit**: Ensure code works
3. **Reference issues**: Include issue numbers if applicable
4. **Keep it focused**: Don't mix unrelated changes
5. **Write for humans**: Future you will read this

## Commit message checklist

- [ ] Type is appropriate (feat/fix/docs/etc.)
- [ ] Summary is under 50 characters
- [ ] Summary uses imperative mood
- [ ] Body explains WHY not just WHAT
- [ ] Breaking changes are clearly marked
- [ ] Related issue numbers are included
