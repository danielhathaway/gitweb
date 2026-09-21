# GitWeb

GitWeb is a lightweight Flask-based web application for browsing and editing files within local Git repositories.

It provides a browser-based interface for selecting a configured repository, navigating its directory structure, editing files, and saving changes. Changes can optionally be committed and pushed directly from the web interface.

GitWeb is intended for use on systems where repositories are hosted locally and a simple web interface is useful for making controlled file changes without requiring a full Git client.

## Features

* Browse multiple configured Git repositories
* Navigate repository directories and files
* Edit files through a web-based editor
* Save file changes directly to the repository
* Optionally create a Git commit when saving
* Optionally push committed changes to the configured remote
* Configurable repository list
* Configurable SVG icon size
* CSRF protection for web forms
* Session data is encrypted
* Path validation to restrict navigation to configured repositories
* Lightweight Flask application with minimal dependencies

## How It Works

GitWeb is configured with a list of local Git repository paths in `gitweb.conf`.

When the application starts, it reads the configured repository list and removes entries that do not exist. The repository paths are then presented through the web interface.

The application provides three primary views:

1. **Repository selection** - Select a configured repository.
2. **File browser** - Navigate directories and select files.
3. **File editor** - View and modify the contents of a file.

The root URL redirects to the repository selection page.

## Requirements

GitWeb currently requires:

* Python 3
* Flask >= 3.1.3
* Flask-WTF >= 1.2.2
* MarkupSafe >= 2.1.5
* WTForms >= 3.2.1
* `chemlibrary_chempy` >= 2.3.1

These dependencies are specified in `requirements.txt`.

Git must also be installed on the host if commit and push functionality is going to be used.

## Installation

Clone the repository:

```bash
git clone https://github.com/danielhathaway/gitweb.git
cd gitweb
```

Create a Python virtual environment:

```bash
python3 -m venv venv
```

Activate the virtual environment:

```bash
source venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

GitWeb uses `gitweb.conf` for configuration.

A basic configuration looks like:

```ini
# This is an example config file for gitweb.py

repo_list = /home/user/Desktop/test

svg_size = 30
```

The repository currently supports the following configuration values:

| Setting     | Description                                        | Default  |
| ----------- | -------------------------------------------------- | -------- |
| `repo_list` | Comma-separated list of local Git repository paths | Required |
| `svg_size`  | Size of the repository/file SVG icons              | `30`     |

The application requires `repo_list` to be present. If it is missing, GitWeb exits during startup. Repository paths that do not exist are removed from the active list.

### Multiple Repositories

Multiple repositories can be specified as a comma-separated list:

```ini
repo_list = /home/user/code/project1, /home/user/code/project2, /home/user/code/project3
```

The paths should be separated by a comma followed by a space.

For example:

```ini
repo_list = /home/user/code/repos/medusa, /home/user/code/repos/gitweb
```

### Icon Size

The size of the SVG icons displayed by the application can be changed with:

```ini
svg_size = 40
```

If `svg_size` is not specified, GitWeb uses `30`.

## Running GitWeb

GitWeb can be started using Flask's development server:

```bash
flask --app gitweb run
```

For development, debug mode can be enabled:

```bash
flask --app gitweb run --debug
```

The application's own module documentation identifies the Flask command above as the development invocation.

By default, Flask listens on:

```text
http://127.0.0.1:5000
```

To make the application available on the local network:

```bash
flask --app gitweb run --host 0.0.0.0
```

Do not use Flask's development server as the public-facing production server. For production deployments, use a WSGI server such as Gunicorn behind an appropriate reverse proxy.

## Using GitWeb

### 1. Select a Repository

Open GitWeb in a browser.

The application initially redirects to `/repos`, where the configured repositories are displayed. Selecting a repository establishes it as the current repository and opens its contents.

### 2. Browse Files

After selecting a repository, GitWeb displays its directory contents.

Directories can be opened to navigate through the repository. Files can be selected for editing.

The application sorts directories before files in the browser view.

### 3. Edit a File

Selecting a file opens the editor.

The editor provides:

* The current file contents
* A commit message field
* A **Commit changes** option
* A **Push changes** option
* A Save button

The application attempts to read the file as plaintext. If that fails, it falls back to displaying the file contents in hexadecimal form and warns the user before saving.

### 4. Save Changes

Click **Save** to write the modified contents back to the file.

GitWeb uses a safe-write helper supplied by `chemlibrary_chempy` when writing the file.

### 5. Commit Changes

If **Commit changes** is selected, GitWeb stages the current file and creates a Git commit.

The commit message is taken from the commit message field in the editor.

Conceptually, GitWeb performs:

```bash
git -C <repository> add <file>
git -C <repository> commit -m "<commit message>"
```

If the commit fails, GitWeb attempts to unstage the changes.

### 6. Push Changes

If **Push changes** is also selected, GitWeb pushes the newly created commit to the repository's configured remote:

```bash
git -C <repository> push
```

If the push fails, GitWeb attempts to undo the commit while preserving the changes as a soft reset.

## Security

GitWeb is designed to modify files and execute Git commands on the host system. It should therefore be treated as an administrative application.

Anyone with sufficient access to GitWeb may potentially:

* Read files from configured repositories
* Modify files
* Create Git commits
* Push changes to Git remotes

### Repository Restrictions

GitWeb restricts navigation to configured repositories. Paths are sanitized and checked to ensure that selected paths remain within the currently selected repository.

Only configure repositories that you intend to make accessible through the application.

### Run as an Unprivileged User

Do not run GitWeb as `root` unless there is a specific requirement to do so.

A dedicated service account is recommended:

```text
gitweb
```

The account should have only the filesystem and Git permissions required to manage the configured repositories.

### Network Access

If GitWeb is deployed on a server, avoid exposing it directly to the public Internet unless additional authentication and access controls are in place.

A typical production architecture is:

```text
Browser
   |
   v
Reverse Proxy
   |
   v
Gunicorn
   |
   v
GitWeb
   |
   v
Local Git Repositories
```

A VPN or private network can also be used when GitWeb is intended for internal administration.

## CSRF Protection

GitWeb uses Flask-WTF and enables Flask-WTF's CSRF protection. Forms used by the application inherit CSRF protection through the Flask-WTF form classes.

CSRF failures are handled by redirecting the user back to the repository selection page.

## Session Security

GitWeb generates an AES encryption key for session data when the application starts and uses it to encrypt values stored in the Flask session.

The Flask application also generates a random secret key when it starts:

```python
app.secret_key = secrets.token_hex()
```

Because the key is generated at startup, existing Flask sessions are invalidated when the application restarts.

For a long-running production deployment, consider changing the application to load a persistent secret key from a protected environment variable or configuration file.

## Production Deployment

For production use, GitWeb should be run using a WSGI server rather than Flask's development server.

### Install Gunicorn

Inside the virtual environment:

```bash
pip install gunicorn
```

Test the application:

```bash
gunicorn --bind 127.0.0.1:8000 gitweb:app
```

GitWeb should then be available locally at:

```text
http://127.0.0.1:8000
```

### systemd Service

A `systemd` service can be used to automatically start GitWeb and restart it if it exits.

Create:

```bash
sudo nano /etc/systemd/system/gitweb.service
```

Example:

```ini
[Unit]
Description=GitWeb Flask Application
After=network.target

[Service]
Type=simple

User=gitweb
Group=gitweb

WorkingDirectory=/opt/gitweb

ExecStart=/opt/gitweb/venv/bin
```
