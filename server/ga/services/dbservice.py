from flask import current_app as app
from ..models.gitlab_analytics_models import *
import hashlib

# use python module as singleton
# so we don't need to create a DBService class here

_connected = False
_initialized = False

setting_keys = ['external_url', 'gitlab_url', 'private_token']


def connect():
    global _connected
    if _connected:
        return
    mysql_host = app.config['mysql_host']
    mysql_port = app.config['mysql_port']
    mysql_user = app.config['mysql_user']
    mysql_password = app.config['mysql_password']
    mysql_database = app.config['mysql_database']
    app.logger.debug(
        "setup db connection {}@{}:{}".format(mysql_user, mysql_host,
                                              mysql_database))
    database.database = mysql_database
    database.connect_params = {'host': mysql_host, 'port': int(mysql_port),
                               'user': mysql_user,
                               'password': str(mysql_password),
                               'charset': 'utf8', 'use_unicode': True}
    _connected = True


def is_initialized():
    global _initialized
    if _initialized:
        return True
    _initialized = Settings.table_exists()
    return _initialized


def initialize():
    app.logger.info("initialize_db")
    database.execute_sql(
        'alter database gitlab_analytics default character set utf8 collate utf8_general_ci')
    database.create_tables([GitlabCommits, GitlabIssues, GitlabWikiCreate,
                            GitlabWikiUpdate, GitlabIssueComment,
                            GitlabMergeRequest, GitlabMRAssigneeComment,
                            GitlabMRInitiatorComment, Settings])
    global _initialized
    _initialized = True


def password_exists():
    r = Settings.get_or_none(name='password')
    return r is not None and r.value is not None and len(r.value) > 0


def _password_salt(password):
    v = password + "this is a long long salt"
    return hashlib.sha256(v.encode('utf8')).hexdigest()


def save_password(password):
    s, exists = Settings.get_or_create(name='password')
    # TODO what to do when password exists?
    s.value = _password_salt(password)
    s.save()


def check_password(password):
    r = Settings.get(name='password')
    app.logger.debug(password)
    return r.value == _password_salt(password)


def load_settings():
    for name in setting_keys:
        row = Settings.get_or_none(name=name)
        if row is not None:
            app.config[name] = row.value
        else:
            app.config[name] = ''


def save_settings(d):
    for name in setting_keys:
        s, exists = Settings.get_or_create(name=name)
        s.value = d[name]
        s.save()
    """
    creaet_app 里会调用 load_settings
    但是，create_app 只有 flask app 启动时才会被执行，后续web请求过来时，并不会触发。
    所以当settings变化时，需要再 load_settings 一次。
    """
    load_settings()
