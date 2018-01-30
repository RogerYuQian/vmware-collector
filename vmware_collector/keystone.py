from keystoneauth1.loading import conf as keystone_conf
from keystoneauth1 import session


AUTH = None
SESSION = None


def get_auth(conf):
    global AUTH
    if not AUTH:
        AUTH = keystone_conf.load_from_conf_options(conf, 'keystone_authtoken')
    return AUTH


def get_session(conf):
    auth = get_auth(conf)
    global SESSION
    if not SESSION:
        SESSION = session.Session(auth=auth)
    return SESSION
