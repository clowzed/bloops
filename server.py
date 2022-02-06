import json
import os
import pathlib
import re
import shutil
import subprocess
import uuid
import zipfile
import hashlib

import flask
import requests
from dotenv import load_dotenv

load_dotenv() 

import warnings

import bs4
from apscheduler.schedulers.background import BackgroundScheduler

import models

import logging

import coloredlogs

warnings.filterwarnings("ignore")


logger = logging.getLogger(__name__)
coloredlogs.install(level  = 'DEBUG', 
					logger = logger)

PLATFORMS = list(map(
					lambda platform: platform.strip(), 
					os.environ.get('PLATFORMS', "")
							  .strip()
							  .split(',')
					)
				)
				
class Repository:
	def __init__(self, url):
		self.url = url
		self.reponame = self.parse_reponame(url)
		self.username = self.parse_username(url)
	
	def parse_username(self, url):
		return url.split('/')[-2]
	
	def parse_reponame(self, url):
		return url.split('/')[-1]
		
	def last_commit(self):
		url = f"https://api.github.com/repos/{self.username}/{self.reponame}/commits"
		response = requests.get(url, params = {"per_page": 1})
		if response.status_code == 200:
			commits = response.json()
			if commits:
				last = commits[0]["sha"]
				return last

	def download(self):
		url = self.url + "/archive/master.zip"
	
		logger.info(f"Fetching zip from {url}")
	
		response = requests.get(url, stream = True)
	
		if response.status_code == 200:
			zip_file_path = pathlib.Path.cwd() / f"{self.reponame}.zip"
   
			logger.info(f"Writing zip to: {zip_file_path}")

			with open(zip_file_path, 'wb') as package_zip_file:
				for chunk in response.iter_content(chunk_size=1024):
					if chunk:
						package_zip_file.write(chunk)
	
			logger.info(f"Zip file was saved!")
			logger.info(f"Extracting zip {zip_file_path} to current dir")
	
			with zipfile.ZipFile(zip_file_path) as zip_ref:
				zip_ref.extractall(pathlib.Path.cwd())
			zip_file_path.unlink()
   
			return True
		return False

	def exists(self):
		url = f"https://api.github.com/repos/{self.username}/{self.reponame}"
		response = requests.get(url)
		return response.status_code == 200
	

def process_repos():
	logger.info("Processing each repo")
	repos = models.Repo.select()
	for repo in repos:
		repo_data = Repository(repo.url)
     
		logger.info(f"Inspecting {repo}")
  
		last_commit = repo_data.last_commit()
		
		if last_commit and last_commit != repo.last_commit:
			logger.info("Last commit has changed. Creating new Jobs")
   
			for target in PLATFORMS:
				models.Job.create(url = repo.url, commit = last_commit, platform = target).save()
				logger.info("New Job was created")
			repo.last_commit = last_commit
			repo.save()
		else:
			logger.info("Last commit has not changed")

def cleanup(folder, last_dir = None, ret = False):
	shutil.rmtree(folder)
	if last_dir:
		os.chdir(last_dir)
	return ret




def build(job):

	repo = Repository(job.url)
 
	logger.info(f"repo name = {repo.reponame}")
 
	if repo.download():
		last_dir = os.getcwd()
		os.chdir(f"{repo.reponame}-master")
  
		logger.info(f"Adding target {job.platform	} with rustup")
  
		res = subprocess.run(["rustup", "target", "add", job.platform])
  
		if res.returncode: 
			logger.error(f"Failed to add target {job.platform	} with rustup")
			return cleanup(f"../{repo.reponame}-master", last_dir)


		logger.info("Starting cross build...")
  
  
		res = subprocess.run(["cargo", "build", "--release", "--target", job.platform], stdout = subprocess.PIPE, 
                       																	stderr = subprocess.PIPE)
  
		if res.returncode: 
			logger.error(f"Failed to build target with cross")
			return cleanup(f"../{repo.reponame}-master", last_dir)
		else: 
			logger.info("Target was sucessfully built")
  
		os.chdir(last_dir)
  
		executable = pathlib.Path.cwd() / f"{repo.reponame}-master" / "target" / job.platform / "release" / f"{repo.reponame}"
  
		if executable.exists():
			target_folder = pathlib.Path(os.environ["BUILD_DIR"]) / f"{repo.reponame}-builds" / job.commit / job.platform	
			target_folder.mkdir(parents = True, exist_ok = True)
   
			logger.info(f"Moving executable from {executable} to {target_folder / executable.name}")
			shutil.copy(executable, target_folder / executable.name)
		else:
			logger.error(f"Failed to build executable for {repo.reponame} target = {job.platform}")

		logger.info(f"Cleanong unnecessary files and folders...")
		cleanup(f"./{repo.reponame}-master")
  
		return (target_folder / executable.name).resolve()

	logger.error(f"Failed to build executable for {repo.reponame} target = {job.platform}")
	


def run_jobs():
	logger.info("Running jobs...")
	jobs = list(models.Job.select().where(models.Job.status == "scheduled"))

	for job in jobs:
		job.status = "pending"
		job.save()
  
		targetpath = build(job)
		repo = models.Repo.select().where(models.Repo.url == job.url).limit(1)[0]
		models.Artifact.create(identifier = repo.identifier, targetpath = str(targetpath), commit = job.commit, platform = job.platform	, is_successful = bool(targetpath)).save()
		logger.info("Artifact were succesfully created")
		logger.info("Job finished. Deleting job...")
		job.status = "finished"
		job.save()
		
	

sched = BackgroundScheduler(daemon = True)

sched.add_job(process_repos, 'interval', seconds = 5)
sched.add_job(run_jobs,      'interval', seconds = 15)

sched.start()



app = flask.Flask("self-hosted build server for rust apps", template_folder = "./templates")


def sha256(password):
	hasher = hashlib.sha256()
	hasher.update(password.encode("utf-8"))
	return hasher.hexdigest()

@app.route("/static/<path:path>")
def static_dir(path):
    return flask.send_from_directory("static", path)

@app.get('/')
def redirect1():
    return flask.redirect('/identifiers')


@app.get('/index')
def redirect2():
    return flask.redirect('/identifiers')
    
    
@app.get('/new')
def new():
	return flask.render_template('new.html')


@app.get("/identifiers")
def identifiers():
	repos = list(models.Repo.select())
	return flask.render_template('identifiers.html', repos = repos)


@app.post('/addnew')
def addnew():
	url      = flask.request.form.get("url")
	password = flask.request.form.get("password")
	
	if not url:
		return flask.render_template("error.html", message = "Git URL is required!")
	
	if not password:
		return flask.render_template("error.html", message = "Password is required!")

	if sha256(password) != os.environ["PASSWORD_HASH_SHA_256"]:
		return flask.render_template("error.html", message = "Invalid password!")

	regexp = re.compile(r'(https://)github.com[:/](.*)')

	url = url.strip()
 
	if not regexp.match(url):
		return flask.render_template("error.html", message = "Url does not match github url!")

	if not Repository(url).exists():
		return flask.render_template("error.html", message = "Specified repository does not exist!")


	if models.Repo.select()                      \
				  .where(models.Repo.url == url) \
				  .exists():
	
		return flask.render_template("error.html", message = "We are currently monitoring this link!")


	models.Repo 																  \
		  .create(identifier = uuid.uuid4().hex, url = url) \
		  .save()

	return flask.redirect("/identifiers")



@app.get("/build/<identifier>/commits")
def get_commit_builds(identifier):
	if not models.Repo.select().where(models.Repo.identifier == identifier).exists():
		return flask.render_template("404.html", message = "Identifier was not found!")
	
	repo = models.Repo.select().where(models.Repo.identifier == identifier).first()
	commits = models.Artifact.select(models.Artifact.commit).where(models.Artifact.identifier == identifier)
	commits = set(map(lambda x: x.commit, commits))

	if not len(commits):
		return flask.render_template("404.html", message = "No commits were found for this repo! May be we've not checked repository yet?")
  
	return flask.render_template("commits.html", url        = repo.url, 
												 identifier = repo.identifier,
												 commits    = commits)
																		  
																		  

@app.get("/build/<identifier>/latest")
def get_latest_commit_builds(identifier):
	if not models.Repo.select().where(models.Repo.identifier == identifier).exists():
		return flask.render_template("404.html", message = "Identifier was not found!")
	
	repo = models.Repo.select().where(models.Repo.identifier == identifier).first()
	
	if not repo.last_commit:
		return flask.render_template("404.html", message = "No builds were found for last commit as repo was not processed!")
		
	return flask.redirect(f"/builds/{identifier}/{repo.last_commit}")


@app.get("/build/<identifier>/<commit>/<platform>")
def get_build(identifier, commit, platform):
	if not models.Artifact.select()                                         \
						  .where(models.Artifact.identifier == identifier, \
								 models.Artifact.platform   == platform, \
								 models.Artifact.commit     == commit)\
						  .exists():

		return flask.render_template("404.html", message = "Build with this params was not found!")

	artifact = models.Artifact.select()\
							  .where(models.Artifact.identifier == identifier, \
							         models.Artifact.platform   == platform, \
							         models.Artifact.commit     == commit) \
							  .first()

	return flask.send_file(artifact.targetpath, as_attachment = True)



@app.get("/build/<identifier>/<commit>")
def get_builds(identifier, commit):
	if not models.Artifact.select() \
						  .where(models.Artifact.identifier == identifier, models.Artifact.commit == commit) \
						  .exists(): \
		return flask.render_template("404.html", message = "Builds for this identifier and commit were not found!")

	artifacts = models.Artifact.select().where(models.Artifact.identifier == identifier)
	
	return flask.render_template('builds.html', artifacts  = artifacts)


if __name__ == '__main__':
	app.run()
