import peewee
import pathlib
import os

dbpath = pathlib.Path(os.environ["DB_PATH"])
if not dbpath.exists(): dbpath.touch()

db = peewee.SqliteDatabase(dbpath)
    


class Repo(peewee.Model):
    url = peewee.CharField()
    identifier = peewee.CharField()
    last_commit = peewee.CharField(default="")
    class Meta:
        database = db

class Artifact(peewee.Model):
    identifier    = peewee.CharField()
    targetpath    = peewee.CharField()
    platform      = peewee.CharField()
    commit = peewee.CharField()
    is_successful = peewee.BooleanField(default=False)
    class Meta:
        database = db

class Job(peewee.Model):
    url = peewee.CharField()
    commit = peewee.CharField()
    platform = peewee.CharField()
    status = peewee.CharField(default = "scheduled")
    class Meta:
        database = db

    

Repo.create_table()
Artifact.create_table()
Job.create_table()