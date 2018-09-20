# Contributing guidelines

For now this file just contains an example of how to use the testing API:

```python
import requests
import zipfile
import io
from gl_runner_api.testing import FakeGitlabAPI, API_ENDPOINT

# Instead of using the context manager enter it manually
# with FakeGitlabAPI(n_pending=10) as gitlab_api:
gitlab_api = FakeGitlabAPI(n_pending=10)
gitlab_api.__enter__()
repo_token = gitlab_api.token

# Alternatively use the live GitLab instance
# repo_token = 'ADD_TOKEN_HERE'

# Add a runner
data = {
    'token': repo_token,
    'description': 'A description',
    'info': {
        'name': 'a name',
        'version': 'a version',
        'revision': 'a revision',
        'platform': 'a platform',
        'architecture': 'a architecture',
        'executor': 'a executor',
        'features': {},
    },
    'active': True,
    'locked': False,
    'run_untagged': True,
    'tag_list': ['cvmfs,dirac'],
    'maximum_timeout': 10*60*60,
}
response = requests.post(API_ENDPOINT+'/runners/', json=data)
assert response.status_code == 201
runner_id = response.json()['id']
runner_token = response.json()['token']

# Check the runner token works
response = requests.post(API_ENDPOINT+'/runners/verify', json={'token': runner_token})
assert response.status_code == 200

# Request a job
response = requests.post(API_ENDPOINT+'/jobs/request', json={'token': runner_token, 'info': data['info']})
assert response.status_code == 201
job_info = response.json()

# Update the job's log
data = 'First line\nSecond line\n'
response = requests.patch(
    API_ENDPOINT+'/jobs/'+str(job_info['id'])+'/trace', data,
    headers={'JOB-TOKEN': job_info['token'], 'Content-Range': '0-'+str(len(data))}
)
assert response.status_code == 202
_, current_log_length = response.content.decode().split('-')

# Update the job's log again
data = 'Third line\n'
response = requests.patch(
    API_ENDPOINT+'/jobs/'+str(job_info['id'])+'/trace', data,
    headers={'JOB-TOKEN': job_info['token'], 'Content-Range': current_log_length+'-'+str(len(data))}
)
assert response.status_code == 202

# Create a fake job artifacts zipfile
fp = io.BytesIO()
with zipfile.ZipFile(fp, 'w') as zf:
    zf.writestr(zipfile.ZipInfo('some_dir/test.txt', (2012, 12, 25, 11, 9, 50)), 'Example file')
fp.seek(0)

# Upload job artifacts
response = requests.post(
    API_ENDPOINT+'/jobs/'+str(job_info['id'])+'/artifacts',
    {'expire_in': '4 hours'}, headers={'JOB-TOKEN': job_info['token']}, files={'file': ('artifacts.zip', fp)}
)
assert response.status_code == 201

# Finish the job
data = {
    'token': job_info['token'],
    'trace': 'First line\nSecond line\nThird line\n',  # Optional
    'state': 'success',  # 'success' or 'failed'
    'failure_reason': 'script_failure',  # Ignored if state is 'success'
}
response = requests.put(API_ENDPOINT+'/jobs/'+str(job_info['id']), json=data)
assert response.status_code == 200

# Download the artifacts again (id and token should be taken from job_info['dependencies'])
response = requests.get(API_ENDPOINT+'/jobs/'+str(job_info['id'])+'/artifacts',
                        headers={'JOB-TOKEN': job_info['token']})
assert response.status_code == 200
fp.seek(0)
assert response.content == fp.read()

gitlab_api.__exit__(None, None, None)
```
