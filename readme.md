<div align = "center">
    <h1 style = "color: green;">BLOOPS</h1>
    <h5>Build server for simple `rust` applications with `cross`</h5>
    <h5>Name comes from `build + loops` </h5>
</div>

## About
This is a pythin server build with `flask`. It monitors last commits for git repositories and builds simple `rust` applications.

1) Go to `<server_ip>::<port>/new`
2) Enter public repository url and password (place hashed with SHA256 in .env) from .env and click `Add url`
3) Now server monitors for last commits in repository at master branch.
4) On new commit it creates jobs for building rust applications for differnet target.
5) On each job it clones the master branch of the repository and starts building
6) All repositories can be found on `<server_ip>::<port>/identifiers`
7) Click on repository and search for commit you need and then you'll see completed and failed builds.
8) You can also download the prebuild for any platform (if build was successful)

<hr>

## Requirements
Check that you have installed:
- python
- pipenv
```bash
py -m pip install pipenv
```
- rust
- cargo
- cross 
```bash
cargo install cross
```
- docker

Before startup make shure that you started docker.service
```bash
sudo systemctl enable docker
sudo systemctl start docker
```

<hr>


## Installation
- go to directory you prefer
```bash
cd /path/to/any/dir
```

- clone the repository
```bash
git clone https://github.com/clowzed/bloops.git
```

- run pipenv install
```
cd bloops
pipenv install
```
- update `.env` file and add custom password so only you can add urls for monitoring 

<hr>


## Running
- Without any proxy
```bash
pipenv run python server.py
```

<hr>


## Tips
- use `gunicorn` or `uwsgi` and `nginx` if you need
- add cron job on restart 
- you can install it on `pi` and use port forwarding

<hr>

## Endpoints
- /new
- /identifiers
- /builds/<identifier>
- /builds/<identifier>/<commit>
- /builds/<identifier>/<commit>/<platform> will download binary
- /builds/<identifier>/latest
- /builds/<identifier>/latest/<platform> will download latest binary for platform

## TODO
- [ ] On builds database locks causing 500 error code
- [ ] Add jobs endpoint
- [ ] Add failed build reason for job