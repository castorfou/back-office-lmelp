## Github-cli: `gh`

### installation and upgrade

Installation is made through devcontainer configuration

```json
"features": {
  "ghcr.io/devcontainers/features/github-cli:1": {}
}
```

And to upgrade without having to rebuild your container

```bash
gh extension upgrade --all
```

### config

Config file is not in workspace but is in the home directory.

#### add user and token

Authenticate with your GitHub account:

```bash
gh auth login
```

Or set a token manually via environment variable:

```bash
export GH_TOKEN=ghp_<your_token>
```

#### auth (interactive example)

```bash
gh auth login
```

Typical answers for GitHub:

```text
Where do you use GitHub? GitHub.com
How would you like to authenticate? Paste an authentication token
auth token: <personal access token with repo, workflow scopes>
```

Full example session:

```text
? Where do you use GitHub? GitHub.com
? What is your preferred protocol for Git operations on this host? SSH
? Upload your SSH public key to your GitHub account? /home/vscode/.ssh/id_rsa.pub
? How would you like to authenticate GitHub CLI? Login with a web browser
! First copy your one-time code: F8B2-D97A
Press Enter to open https://github.com/login/device in your browser...
✓ Logged in as <USER>
```

#### pager

A pager (default: less) displays the output. You can change or disable it via environment variables (PAGER / GIT_PAGER) or by adjusting less options (LESS).

```bash
GH_PAGER=cat gh repo view        # no pager, raw output — this is the config used in devcontainer
# or
GH_PAGER='less -FRX' gh repo view  # less without clearing the screen
```

### commands

#### repo

```bash
gh repo view
```

#### issues

```bash
# List project issues.
gh issue list

# Create an issue
gh issue create

# Display the title, body, and other information about an issue.
gh issue view 3

# Assign an issue.
gh issue edit 3 --add-assignee @me
```

#### pr

```bash
# List pull requests.
gh pr list

# Display the title, body, and other information about a pull request.
gh pr view 3

# Check out an open pull request.
gh pr checkout 3

# Create a new pull request.
gh pr create --title "My feature" --body "Closes #3"
```

### help

```bash
❯ gh --help
Work seamlessly with GitHub from the command line.

USAGE
  gh <command> <subcommand> [flags]

CORE COMMANDS (extract)
  auth:        Authenticate gh and git with GitHub
  browse:      Open the repository in the browser
  codespace:   Connect to and manage codespaces
  gist:        Manage gists
  issue:       Manage issues
  org:         Manage organizations
  pr:          Manage pull requests
  project:     Work with GitHub Projects
  release:     Manage GitHub releases
  repo:        Manage repositories
  run:         View details about workflow runs
  workflow:    View details about GitHub Actions workflows

FLAGS
  -h, --help      Show help for this command.
  -v, --version   Show gh version information
```


## Contributing workflow

Everything starts with an issue ;)

### Code Contributions

For traceability and clarity, we use the following process

#### Create an issue on GitHub

Using the web interface or gh-cli:

```bash
gh issue create
```

#### From issue create a branch and pull request

Using gh-cli to create a branch linked to the issue:

```bash
gh issue develop 3
```

This creates a branch named after the issue (e.g. `3-document-code-contribution-policy`).

Or create a pull request directly:

```bash
gh pr create --title "My feature" --body "Closes #3"
```

#### Work within this branch

In this example the branch is `3-document-code-contribution-policy`

```bash
git fetch
gco 3-document-code-contribution-policy # (1)
git pull
```

1. gco comes from [oh-my-zsh-git](https://kapeli.com/cheat_sheets/Oh-My-Zsh_Git.docset/Contents/Resources/Documents/index) and stands for git checkout

#### Add / Commit / Push

as you are used to

#### Merge to main

When ready, mark the pull request as ready for review:

```bash
gh pr ready 3
```

Then merge:

```bash
gh pr merge 3
```

Or from the web interface: click **"Merge pull request"**.

#### Get back to main

```bash
git fetch
gco main
git pull
```

## git tag, release

### What is a Tag?
A tag in Git is an immutable marker pointing to a specific commit. Tags are commonly used to indicate releases (e.g., `v1.0`, `v2.0`) or important milestones, but you can also use them to mark development stages (e.g., `dev-ready`, `stable`).

### Typical Workflow
- Mark a development stage with a tag (e.g., `dev-ready`).
- Continue working and create new tags for further milestones (e.g., `stable`, `v2.0`).
- Return to a previous tag to restore the project state at that point.

### Common Git Commands

#### Create a Tag
```zsh
git tag dev-ready
```
Tag the current commit. To tag a specific commit:
```zsh
git tag stable <commit_sha>
```

#### List Tags
```zsh
git tag
```

#### Push Tags to Remote
Push a single tag:
```zsh
git push origin dev-ready
```
Push all tags:
```zsh
git push --tags
```

#### Delete a Tag
Delete locally:
```zsh
git tag -d dev-ready
```
Delete on remote:
```zsh
git push origin --delete dev-ready
```

#### Checkout a Tag
Restore the state at a tag (detached HEAD):
```zsh
git checkout dev-ready
```

### Retagging (Update a Tag)
Tags are immutable. To update a tag to a new commit:
```zsh
git tag -d dev-ready
# Create the tag again on the new commit
git tag dev-ready
# Force-push the updated tag
git push origin --force dev-ready
```

### GitHub Interface
- Go to your repository > **Releases** > **Tags**.
- Create a tag with "Create a new release".
- Delete or view existing tags.
- To return to a tag, browse the history or download the code at that tag.

### Notes
- Tags are not branches; they do not move and only mark a commit.
- To continue development from a tag, create a branch from that tag.


### Changelog and Tag Descriptions

You cannot directly attach a full changelog to a Git tag. Here are common practices for describing changes associated with tags:

#### Annotated Tags with Messages
You can add a short message to a tag when creating it:
```zsh
git tag -a v1.0 -m "Release v1.0: Added feature X, fixed bug Y"
```
To view the message:
```zsh
git show v1.0
```

### GitHub Releases
On GitHub, you can associate a tag with a Release and add a detailed description or changelog via the web interface or gh-cli. This is the recommended way to publish release notes for users and collaborators.

```bash
# Create a release with auto-generated notes
gh release create v1.0 --generate-notes

# Create a release with a custom title and notes
gh release create v1.0 --title "Release v1.0" --notes "Added feature X, fixed bug Y"
```

#### CHANGELOG.md File
Maintain a `CHANGELOG.md` file at the root of your project. Add a section for each version/tag, describing the changes in detail.

**Summary:**
- Use tag messages for brief descriptions.
- Use `CHANGELOG.md` or GitHub Releases for complete changelogs.
