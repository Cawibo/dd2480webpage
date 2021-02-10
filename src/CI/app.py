from flask import Flask, request
import pytest
import os
import subprocess
import json
from pylint import epylint as lint
import notification


app = Flask(__name__)


@app.route('/')
def index():
    return "Hello :)"


@app.route("/webhook", methods=['POST'])
def github_webhook_handler():
    payload = json.loads(request.form['payload'])
    event_type = request.headers["X-Github-Event"]
    if event_type == "push":
        handle_push(payload)
    return ""

def handle_push(payload):
    repo_id = payload["repository"]["id"]
    commit_sha = payload["after"]
    repo_directory = "/tmp/testrepo_{}{}".format(repo_id,commit_sha)

    os.system("git clone {} {}".format(payload["repository"]["clone_url"],repo_directory)) 
   
    #Switch to branch
    os.system("git -C {} pull".format(repo_directory))
    os.system("git -C {} checkout {}".format(repo_directory,commit_sha))


    #Run pylint
    (pylint_stdout, pylint_stderr) = lint.py_run(repo_directory, return_std=True)
    pylint_output = pylint_stdout.read()
    print(pylint_output)

    #Run pytest
    pytest_output = subprocess.run(["python3","-m","pytest"],text=True,capture_output=True,cwd=repo_directory).stdout
    print(pytest_output)

    subject = '[{}] {} "{}"'.format(payload["repository"]["full_name"], repo_directory, payload["commits"][0]["message"])
    notification.send_notification('Subject: {}\n\n{}'.format(subject, pylint_output + "\n" + pytest_output))

    os.system("rm -rf {}".format(repo_directory))

if __name__ == '__main__':
    with open("data/demo_payload.json") as f:
        payload = json.load(f)

    handle_push(payload)
    app.run(debug=True, host='0.0.0.0',port=80)
    