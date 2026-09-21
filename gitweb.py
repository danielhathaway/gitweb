"""
GitWeb
Usage:
    flask --app gitweb run --debug
See:
    https://flask.palletsprojects.com/en/stable/
    https://jinja.palletsprojects.com/en/stable/templates/
Details:
    Forms created by this module have CSRF protection

### !!! TODO: Need to pull all repos in list when the app starts, and when repo is selected !!! ###

"""



import secrets
from datetime import datetime
import os
from flask import Flask, request, redirect, url_for, session, flash, get_flashed_messages
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, CSRFError
from markupsafe import escape
from chempy.files import (
    is_child_of_dir,
    dir_contents,
    parent_path,
    file_read,
    file_safe_write,
    file_name,
    sanitize_path,
    file_exists
)
from chempy.cloak import encrypt_aes, decrypt_aes, generate_aes_key
from chempy.conf import read_conf
from chempy.pysub import shsub



def set_current_repo(target:str):
    target = os.path.abspath(target)
    valid = False
    for repo in repo_list:
        if is_child_of_dir(target, repo) and os.path.isdir(target):
            valid = True
            set_session_var('current_repo', target)
            break
    return valid



def dtstr() -> str:
    now = datetime.now()
    formatted_date_time = now.strftime('%Y%m%d%H%M%S')
    return formatted_date_time



def get_messages():
    messages = get_flashed_messages()
    if len(messages) > 0: messages = ''.join(messages)
    else: messages = ''
    return messages



def encrypt(value:str) -> str:
    try: return encrypt_aes(value, session_key)
    except: return None



def decrypt(value:str) -> str:
    try: return decrypt_aes(value, session_key)
    except: return None



def clean_encrypt(path:str) -> str:
    try:
        clean_path = sanitize_path(path)
        enc_path = encrypt(clean_path)
        return enc_path
    except:
        return None



def clean_decrypt(enc_path:str) -> str:
    try:
        path = decrypt(enc_path)
        clean_path = sanitize_path(path)
        return clean_path
    except:
        return None



def alert(ok:bool = True, message:str = None):
    css_classes = ['fail-msg', 'success-msg']
    default_messages = ['Failed!', 'Success!']
    if message == None: message = default_messages[ok]
    flash(f'<p class="{css_classes[ok]}">{message}</p>')



def get_session_var(name:str) -> str:
    return decrypt(session.get(name, None))



def get_current_repo() -> str:
    return sanitize_path(get_session_var('current_repo'))



def get_current_path() -> str:
    return sanitize_path(get_session_var('path'))



def set_session_var(name:str, value:str) -> bool:
    try: session[name] = encrypt(value)
    except: return False
    return True



def set_current_repo(repo:str) -> bool:
    clean_repo = sanitize_path(repo)
    if clean_repo in repo_list:
        return set_session_var('current_repo', clean_repo)
    return False



def set_current_path(path:str) -> bool:
    clean_path = sanitize_path(path)
    current_repo = get_current_repo()
    if is_child_of_dir(clean_path, current_repo):
        return set_session_var('path', clean_path)
    return False



def clear_session_vars() -> bool:
    set_session_var('path', '')
    set_session_var('current_repo', '')
    return True



def invalid_handler():
    clear_session_vars()
    #alert(False)
    return redirect(url_for('repos'))



def in_repo(target_path:str) -> bool:
    target_path = sanitize_path(target_path)
    current_repo = get_current_repo()
    if is_child_of_dir(target_path, current_repo):
        return True
    return False



def target_handler(target:str):
    if target == 'Back': return back_handler()
    target_path = decrypt(target)
    if target_path == 'Back': return back_handler()
    else:
        clean_path = sanitize_path(target_path)
        if os.path.exists(clean_path):
            set_current_path(clean_path)
            if os.path.isfile(clean_path): return redirect(url_for('edit'))
            elif os.path.isdir(clean_path): return redirect(url_for('browse'))
    return invalid_handler()



def back_handler():
    current_path = get_current_path()
    path = parent_path(current_path)
    current_repo = get_current_repo()
    if is_child_of_dir(path, current_repo):
        set_current_path(path)
        return redirect(url_for('browse'))
    else:
        return invalid_handler()



def target_aquisition(request):
    try: target = request.form['submit']
    except: return 'Back'
    return target



class ReposForm(FlaskForm):
    ## This object just needs to be instantiated to use it's CSRF token functionalty.
    ## Python requires at least one indented line after the class declaration:
    unused_variable = 0



class BrowseForm(FlaskForm):
    ## This object just needs to be instantiated to use it's CSRF token functionalty.
    ## Python requires at least one indented line after the class declaration:
    unused_variable = 0



class FileEditForm(FlaskForm):
    ## This object just needs to be instantiated to use it's CSRF token functionalty.
    ## Python requires at least one indented line after the class declaration:
    unused_variable = 0



## App Configuration

## Load values from .conf file:
conf = read_conf('./gitweb.conf')
if conf == None or 'repo_list' not in conf:
    print('YOU NEED TO SPECIFY A "repo_list" in "./gitweb.conf"!')
    exit(1)

repo_list = conf['repo_list'].split(', ')
## Ensure all repo entries are proper paths that exist:
for i in range(len(repo_list)):
    repo_list[i] = sanitize_path(repo_list[i])
    ## Remove path from 'repo_list' if it doesn't exist:
    if not file_exists(repo_list[i]):
        del repo_list[i]


### TODO: Pull all repos in 'repo_list"


## Set the size of SVG images
if 'svg_size' in conf:
    svg_size = conf['svg_size']
else:
    svg_size = 30

## Generate AES encryption key for session data at rest:
try: session_key = generate_aes_key()
except: exit(1)



app = Flask(__name__)
app.secret_key = secrets.token_hex()
csrf = CSRFProtect(app)



def html_head(page_title:str = None):
    title = 'GitWeb'
    if page_title != None: title += f'{title} - {page_title}'
    return f'''
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {style}
</head>
'''



@app.route('/')
def index():
    return redirect(url_for('repos'))



@app.route('/repos', methods=['GET', 'POST'])
def repos():
    form = ReposForm()
    session.pop('_flashes', None) ## Remove any queued flash messages
    buttons = ''
    for repo in repo_list:
        masked = clean_encrypt(repo)
        buttons += f'<button name="submit" type="submit" value="{masked}" class="btn file-btn">{repo_svg()}{file_name(repo)}</button>\n'
    messages = get_messages()
    page_contents = f'''<!DOCTYPE html>
    <html>
        {html_head('Repos')}
        <body>
            <div class="container">
                <div class="form-container">
                    <form method="POST">
                        <div class="header-container">
                            <h2>Select Repo</h2>
                        </div>
                        {messages}
                        {form.hidden_tag()}
                        {buttons}
                    </form>
                </div>
            </div>
        </body>
    </html>'''
    if request.method == 'POST' and form.validate_on_submit():
        target = target_aquisition(request)
        if not set_current_repo(clean_decrypt(target)):
            return invalid_handler()
        return target_handler(target)
    return page_contents



@app.route('/browse', methods=['GET', 'POST'])
def browse():
    form = BrowseForm()
    path = get_current_path()
    if path == None: return invalid_handler()
    try: files = dir_contents(path)
    except: files = []
    messages = get_messages()
    buttons = ''
    sorted_dirs = []
    sorted_files = []
    for file in files:
        if os.path.isdir(file):sorted_dirs.append(f'{file}')
        else:sorted_files.append(f'{file}')
    sorted_dirs.extend(sorted_files)
    for file in sorted_dirs:
        icon = file_svg()
        if os.path.isdir(file): icon = dir_svg()
        masked = clean_encrypt(file)
        buttons += f'<button name="submit" type="submit" value="{masked}" class="btn file-btn">{icon}{file_name(file)}</button>\n'
    if buttons == '':
        buttons = '<p>This directory is empty.</p>'
    page_contents = f'''<!DOCTYPE html>
    <html>
        {html_head('Browse')}
        <body>
            <div class="container">
                <div class="form-container">
                    <form method="POST">
                        <div class="header-container">
                            <button name="submit" type="submit" value="Back" class="btn back-arrow">🡰</button>
                            <h2>Select File</h2>
                        </div>
                        {messages}
                        {form.hidden_tag()}
                        {buttons}
                    </form>
                </div>
            </div>
        </body>
    </html>'''
    if request.method == 'POST' and form.validate_on_submit():
        return target_handler(target_aquisition(request))
    return page_contents



@app.route('/edit', methods=['GET', 'POST'])
def edit():
    form = FileEditForm()
    path = get_current_path()
    if path == None: return invalid_handler()
    ## Ensure that directories can't be viewed in the edit scene:
    if os.path.isdir(path): return redirect(url_for('browse'))
    masked = clean_encrypt(path)
    messages = get_messages()
    file_contents = file_read(path, fallback = False)
    if file_contents == None:
        file_contents = file_read(path)
        messages += '<p class="fail-msg">Plaintext failed, showing hex contents... Be careful saving!</p>'
    page_contents = f'''<!DOCTYPE html>
    <html>
        {html_head('Edit')}
        <body>
            <div class="container edit-container">
                <div class="form-container">
                    <form method="POST">
                        <div class="header-container">
                            <h2>{file_name(path)}</h2>
                        </div>
                        {messages}
                        {form.hidden_tag()}
                        <input id="commit-message" name="commit-message" type="text" value="GitWeb {dtstr()}" required>
                        <label>
                            <input id="commit" name="commit" type="checkbox" value="True">
                            Commit changes
                        </label>
                        <label>
                            <input id="push" name="push" type="checkbox" value="True">
                            Push changes
                        </label>
                        <textarea id="edited-contents" name="edited-contents">{escape(file_contents)}</textarea>
                        <button id="submit" name="submit" type="submit" value="{masked}" class="btn save-btn submit-btn">Save</button>
                    </form>
                    <form method="POST">
                        {form.hidden_tag()}
                        <button id="back" name="submit" type="submit" value="Back" class="btn back-btn">Back</button>
                    </form>
                </div>
            </div>
        </body>
    </html>'''

    if request.method == 'POST' and form.validate_on_submit():
        target = target_aquisition(request)
        if target == 'Back':
            return back_handler()
        elif clean_decrypt(target) == get_current_path():
            contents = request.form['edited-contents'].replace('\r', '')
            if file_safe_write(path, contents):
                alert(message = 'File saved!')

                if 'commit' in request.form:
                    ## Add, commit, and push changes to the repo:
                    response = shsub(f'git -C {get_current_repo()} add {get_current_path()}')
                    if response['code'] != 0:
                        alert(False, f'Staging changes failed! {response['output']}')

                    else:
                        response = shsub(f'git -C {get_current_repo()} commit -m "{escape(request.form["commit-message"])}"')
                        if response['code'] != 0:
                            ## Unstage changes on failed commit
                            response = shsub(f'git -C {get_current_repo()} reset HEAD')
                            alert(False, f'Committing changes failed! {response['output']}')

                        else:
                            if 'push' in request.form:
                                response = shsub(f'git -C {get_current_repo()} push')
                                if response['code'] != 0:
                                    ## Undo last commit on failed push
                                    response = shsub(f'git -C {get_current_repo()} reset --soft HEAD~1')
                                    alert(False, f'Pushing changes failed! {response['output']}')

                                else:
                                    alert(message = 'Changes successfully pushed!')

                            else:
                                alert(message = 'Changes successfully committed!')

                return redirect(url_for('edit'))

            else:
                alert(False)
                return redirect(url_for('edit'))

    return page_contents



@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return invalid_handler()



def dir_svg() -> str:
    #svg_size = 30
    return f'''
<svg height="{svg_size}px" width="{svg_size}px" version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 512 512" xml:space="preserve" fill="#000000"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"> <g> <path style="fill:#2D527C;" d="M465.334,193.319c-8.399,0-15.211-6.81-15.211-15.211V87.875c0-6.891-5.608-12.497-12.499-12.497 H287.449c-8.399,0-15.211-6.81-15.211-15.211s6.811-15.211,15.211-15.211h150.176c23.667,0,42.921,19.254,42.921,42.919v90.233 C480.545,186.509,473.734,193.319,465.334,193.319z"></path> <path style="fill:#2D527C;" d="M470.914,482.771H41.086C18.431,482.771,0,464.341,0,441.686V71.96 c0-23.562,19.169-42.731,42.731-42.731h125.804c23.562,0,42.731,19.169,42.731,42.731v37.468h259.649 c22.655,0,41.086,18.431,41.086,41.085c0,8.401-6.811,15.211-15.211,15.211c-8.4,0-15.211-6.81-15.211-15.211 c0-5.879-4.784-10.663-10.664-10.663h-274.86c-8.399,0-15.211-6.81-15.211-15.211V71.96c0-6.787-5.522-12.309-12.309-12.309H42.731 c-6.787,0-12.309,5.522-12.309,12.309v369.726c0,5.879,4.784,10.663,10.664,10.663h429.827c8.399,0,15.211,6.81,15.211,15.211 C486.125,475.961,479.313,482.771,470.914,482.771z"></path> </g> <path style="fill:#CEE8FA;" d="M496.788,384.61V150.514c0-14.289-11.585-25.874-25.874-25.874h-274.86V71.96 c0-15.199-12.321-27.52-27.52-27.52H42.731c-15.199,0-27.52,12.321-27.52,27.52v52.68v47.177v212.795h481.577V384.61z"></path> <path style="fill:#2D527C;" d="M496.789,399.821H15.211C6.811,399.821,0,393.011,0,384.61V71.96 c0-23.562,19.169-42.731,42.731-42.731h125.804c23.562,0,42.731,19.169,42.731,42.731v37.468h259.649 c22.655,0,41.086,18.431,41.086,41.085v234.096C512,393.011,505.189,399.821,496.789,399.821z M30.422,369.399h451.156V150.514 c0-5.879-4.784-10.663-10.664-10.663h-274.86c-8.399,0-15.211-6.81-15.211-15.211V71.96c0-6.787-5.522-12.309-12.309-12.309H42.731 c-6.787,0-12.309,5.522-12.309,12.309V369.399z"></path> </g></svg>
'''



def repo_svg() -> str:
    #svg_size = 30
    return f'''
<svg height="{svg_size}px" width="{svg_size}px" version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 512 512" xml:space="preserve" fill="#000000"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"> <path style="fill:#2D527C;" d="M435.122,497.167h-299.78c-25.238,0-45.772-20.533-45.772-45.772V169.581 c0-25.238,20.533-45.772,45.772-45.772h57.486c25.237,0,45.77,20.533,45.77,45.772v6.414h227.63 c25.238,0,45.772,20.533,45.772,45.772v201.011c0,8.243-6.684,14.927-14.927,14.927s-14.927-6.684-14.927-14.927V221.767 c0-8.777-7.141-15.918-15.918-15.918H223.671c-8.243,0-14.927-6.684-14.927-14.927v-21.341c0-8.777-7.14-15.918-15.917-15.918 h-57.486c-8.777,0-15.918,7.141-15.918,15.918v281.814c0,8.777,7.141,15.918,15.918,15.918h299.78 c8.243,0,14.927,6.684,14.927,14.927S443.365,497.167,435.122,497.167z"></path> <path style="fill:#CEE8FA;" d="M104.497,169.581c0-17.035,13.809-30.845,30.845-30.845h57.486c17.035,0,30.845,13.81,30.845,30.845 v21.341h183.83V112.79c0-17.036-13.81-30.845-30.845-30.845H134.101V60.604c0-17.036-13.809-30.845-30.845-30.845H45.77 c-17.035,0-30.843,13.809-30.843,30.845V343.91c0,17.036,13.809,30.845,30.845,30.845h58.725V169.581z"></path> <path style="fill:#2D527C;" d="M104.497,389.682H45.77C20.533,389.682,0,369.148,0,343.91V60.604 c0-25.238,20.533-45.772,45.77-45.772h57.486c25.238,0,45.772,20.533,45.772,45.772v6.414h227.63 c25.238,0,45.772,20.533,45.772,45.772v78.132c0,8.243-6.684,14.927-14.927,14.927H223.671c-8.243,0-14.927-6.684-14.927-14.927 v-21.341c0-8.777-7.141-15.918-15.918-15.918H135.34c-8.777,0-15.917,7.141-15.917,15.918v205.174 C119.424,382.998,112.74,389.682,104.497,389.682z M45.77,44.687c-8.777,0-15.917,7.141-15.917,15.918V343.91 c0,8.777,7.14,15.918,15.917,15.918h43.8V169.581c0-25.238,20.533-45.772,45.77-45.772h57.486c25.238,0,45.772,20.533,45.772,45.772 v6.414h153.978V112.79c0-8.777-7.141-15.918-15.918-15.918H134.101c-8.243,0-14.927-6.684-14.927-14.927V60.604 c0-8.777-7.141-15.918-15.918-15.918C103.256,44.687,45.77,44.687,45.77,44.687z"></path> </g></svg>
'''



def file_svg() -> str:
    #svg_size = 30
    return f'''
<svg height="{svg_size}px" width="{svg_size}px" version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 512 512" xml:space="preserve" fill="#000000"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"> <g> <path style="fill:#2D527C;" d="M359.465,512c-1.866,0-3.748-0.361-5.54-1.102c-5.411-2.242-8.941-7.523-8.941-13.382v-81.165 c0-7.998,6.486-14.484,14.484-14.484h81.165c5.859,0,11.139,3.53,13.382,8.941c2.241,5.413,1.001,11.642-3.14,15.784 l-81.165,81.165C366.94,510.528,363.235,512,359.465,512z M373.952,430.835v31.714l31.714-31.714H373.952z"></path> <path style="fill:#2D527C;" d="M295.402,512H92.287c-19.523,0-35.404-15.881-35.404-35.403V60.262 c0-19.523,15.881-35.404,35.404-35.404h327.428c19.523,0,35.403,15.883,35.403,35.404v356.088c0,3.841-1.527,7.524-4.242,10.241 l-81.165,81.165c-5.657,5.654-14.826,5.654-20.484,0c-5.656-5.656-5.656-14.827,0-20.484l76.923-76.923V60.262 c0-3.549-2.887-6.437-6.435-6.437H92.287c-3.549,0-6.437,2.888-6.437,6.437v416.333c0,3.549,2.888,6.435,6.437,6.435h203.116 c7.998,0,14.484,6.486,14.484,14.484C309.886,505.513,303.4,512,295.402,512z"></path> </g> <path style="fill:#CEE8FA;" d="M440.635,138.081V60.262c0-11.554-9.367-20.919-20.92-20.919H92.287 c-11.554,0-20.92,9.365-20.92,20.919v77.818H440.635z"></path> <g> <path style="fill:#2D527C;" d="M440.635,152.564H71.366c-7.999,0-14.484-6.486-14.484-14.484V60.262 c0-19.523,15.881-35.403,35.404-35.403h327.428c19.523,0,35.403,15.881,35.403,35.403v77.818 C455.119,146.079,448.633,152.564,440.635,152.564z M85.85,123.597h340.3V60.262c0-3.549-2.887-6.435-6.435-6.435H92.287 c-3.549,0-6.437,2.887-6.437,6.435V123.597z"></path> <path style="fill:#2D527C;" d="M129.63,80.627c-7.999,0-14.484-6.486-14.484-14.484V14.484C115.146,6.486,121.631,0,129.63,0 s14.484,6.486,14.484,14.484v51.659C144.114,74.141,137.63,80.627,129.63,80.627z"></path> <path style="fill:#2D527C;" d="M213.876,80.627c-7.999,0-14.484-6.486-14.484-14.484V14.484C199.393,6.486,205.877,0,213.876,0 s14.484,6.486,14.484,14.484v51.659C228.36,74.141,221.876,80.627,213.876,80.627z"></path> <path style="fill:#2D527C;" d="M298.124,80.627c-7.998,0-14.484-6.486-14.484-14.484V14.484C283.64,6.486,290.126,0,298.124,0 s14.484,6.486,14.484,14.484v51.659C312.608,74.141,306.122,80.627,298.124,80.627z"></path> <path style="fill:#2D527C;" d="M382.371,80.627c-7.998,0-14.484-6.486-14.484-14.484V14.484C367.888,6.486,374.373,0,382.371,0 s14.484,6.486,14.484,14.484v51.659C396.855,74.141,390.369,80.627,382.371,80.627z"></path> <path style="fill:#2D527C;" d="M129.63,440.789c-7.999,0-14.484-6.486-14.484-14.484V194.083c0-7.998,6.484-14.484,14.484-14.484 s14.484,6.486,14.484,14.484v232.222C144.114,434.303,137.63,440.789,129.63,440.789z"></path> </g> </g></svg>
'''



style = '''
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    body {
        width: 100%;
        justify-content: center;
        align-items: center;
        min-height: 700px;
        background-color: #e4eef5;
        padding: 20px;
    }

    .container {
        margin: auto;
        width: 60%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 16px;
        padding: 30px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
    }

    .container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 6px;
        background: linear-gradient(90deg, #a5d8ff, #74c0fc, #4dabf7);
        z-index: 1;
    }

    .form-container {
        display: inline-block;
        width: 100%;
    }

    .container, .form-container {
        background-color: #f5f7f8;
    }

    .header-container {
        display: flex;
        margin-bottom: 16px;
    }

    .edit-container {
        width: 90%;
    }

    h1, h2 {
        font-size: 28px;
        font-weight: 600;
        display: inline-block;
        height: 100%;
    }

    p {
        padding: 16px;
    }

    p, h1, h2 {
        color: #495057;
    }

    p.success-msg {
        padding: 0 0 16px 0;
        color: #168f14;
    }

    p.fail-msg {
        padding: 0 0 16px 0;
        color: #ab2218;
    }

    input, textarea {
        width: 100%;
        margin-bottom: 8px;
        padding: 12px 16px;
        border: 2px solid #dee2e6;
        border-radius: 8px;
        font-size: 15px;
        color: #495057;
        background-color: #fff;
        transition: all 0.3s ease;
    }

        input:focus, textarea:focus {
            outline: none;
            border-color: #74c0fc;
            box-shadow: 0 0 0 3px rgba(116, 192, 252, 0.25);
        }

    textarea {
        min-height: 400px;
        resize: vertical;
    }

    input[type="checkbox"] {
        width: auto;
        margin: 0 6px 0 0;
        padding: 0;
        vertical-align: middle;
    }

    label {
        display: inline-flex;
        align-items: center;
        margin-right: 16px;
        color: #495057;
    }

    .btn {
        border: none;
        padding: 12px 10px;
        font-size: 16px;
        border-radius: 8px;
        cursor: pointer;
        font-weight: 500;
        transition: all 0.3s ease;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }

    .save-btn {
        width: 100%;
    }

    .submit-btn {
        background-color: #a5d8ff;
    }

    .submit-btn, .file-btn {
        color: #14548F;
        box-shadow: 0 4px 10px rgba(116, 192, 252, 0.3);
    }

    .file-btn {
        justify-content: left;
        background-color: #ffffff;
        width: 100%;
        margin-bottom: 8px;
        padding: 12px 16px;
        border: 2px solid #dee2e6;
        border-radius: 8px;
        font-size: 16px;
        color: #14548F;
        transition: all 0.3s ease;
    }

        .file-btn:hover, .submit-btn:hover {
            background-color: #74c0fc;
            box-shadow: 0 6px 16px rgba(116, 192, 252, 0.4);
            transform: translateY(-2px);
        }

    .back-btn {
        background-color: #ffa6a5;
        color: #ab2218;
        width: 100%;
        box-shadow: 0 4px 10px rgba(252, 119, 116, 0.3);
    }

        .back-btn:hover {
            background-color: #fc7774;
            box-shadow: 0 6px 16px rgba(252, 119, 116, 0.4);
            transform: translateY(-2px);
        }

    .back-arrow {
        background-color: #a5d8ff;
        color: #14548F;
        padding: 6px 10px;
        margin-right: 10px;
        font-size: 16px;
        font-weight: 1600;
        box-shadow: 0 4px 10px rgba(116, 192, 252, 0.3);
    }

        .back-arrow:hover {
            background-color: #74c0fc;
            box-shadow: 0 6px 16px rgba(116, 192, 252, 0.4);
            transform: translateY(-2px);
        }

    .back-arrow-disabled {
        background-color: #d2d2d2;
        color: #616161;
        padding: 6px 10px;
        margin-right: 10px;
        font-size: 16px;
        font-weight: 1600;
        box-shadow: 0 4px 10px rgba(210, 210, 210, 0.3);
    }

    svg {
        margin-right: 10px;
    }
</style>
'''


if __name__ == '__main__':
    shsub('flask --app gitweb run')
