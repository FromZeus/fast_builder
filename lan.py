import requests

parameters = {'openid.assoc_handle': '',
              'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select',
              'openid.ext2.mode': 'fetch_request',
              'openid.ext2.required': 'FirstName,LastName,Email',
              'openid.ext2.type.Email': 'http://schema.openid.net/contact/email',
              'openid.ext2.type.FirstName': 'http://schema.openid.net/namePerson/first',
              'openid.ext2.type.LastName': 'http://schema.openid.net/namePerson/last',
              'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
              'openid.mode': 'checkid_setup',
              'openid.ns': 'http://specs.openid.net/auth/2.0',
              'openid.ns.ext2': 'http://openid.net/srv/ax/1.0',
              'openid.ns.sreg': 'http://openid.net/sreg/1.0',
              'openid.realm': 'https://review.fuel-infra.org/',
              'openid.return_to': 'https://review.fuel-infra.org/OpenID?gerrit.mode=SIGN_IN&'
                                  'gerrit.token=%2Fq%2Fstatus%3Aopen',
              'openid.sreg.required': 'fullname,email',
              }


def get_requirements_from_url(url, gerritAccount):
    s = requests.Session()
    s.headers.update({'Cookie': 'GerritAccount=' + gerritAccount})
    r = s.get(url)

    if r.status_code == 200:
        return r.iter_lines()
    elif r.status_code == 404:
        raise KeyError
    else:
        print r.status_code
        raise SystemExit


def login_to_launchpad(launchpad_id, launchpad_pw):
    s = requests.Session()
    r = s.get('https://login.launchpad.net')

    login_data = {'openid.usernamepassword': '',
                  'csrfmiddlewaretoken': requests.utils.dict_from_cookiejar(s.cookies)['csrftoken'],
                  'email': launchpad_id,
                  'password': launchpad_pw,
                  'user-intentions': 'login',
                  }

    Cookies = 'C=1; csrftoken=' + requests.utils.dict_from_cookiejar(s.cookies)['csrftoken']
    s.headers.update({'Referer': 'https://login.launchpad.net'})
    s.headers.update({'Cookie': Cookies})
    r = s.post('https://login.launchpad.net/+login', data=login_data)

    ss = requests.Session()
    rf = ss.get('https://review.fuel-infra.org/login/q/status:open')
    start_post = rf.content.find('openid.assoc_handle" type="hidden" value="')
    parameters['openid.assoc_handle'] = rf.content[start_post+42: start_post+42+33]

    cookies = 'csrftoken=' + requests.utils.dict_from_cookiejar(s.cookies)['csrftoken']
    try:
        cookies += '; C=1; sessionid=' + requests.utils.dict_from_cookiejar(s.cookies)['sessionid']
    except KeyError:
        print 'Could not authenticate'
        raise SystemExit
    cookies += '; openid_referer="https://review.fuel-infra.org/login/q/status:open"'

    ss.headers.update({'Referer': 'https://review.fuel-infra.org/login/q/status:open'})
    ss.headers.update({'Cookie': cookies})
    r = ss.post('https://login.launchpad.net/+openid', data=parameters, allow_redirects=True)

    d_data = {'csrfmiddlewaretoken': requests.utils.dict_from_cookiejar(s.cookies)['csrftoken'],
              'email': 'on',
              'fullname': 'on',
              'ok': '',
              'openid.usernamepassword': ''
    }

    ss.headers.update({'Referer': r.url})

    header = s.headers
    rd = ss.post(r.url, data=d_data, allow_redirects=True)

    if requests.utils.dict_from_cookiejar(ss.cookies).has_key('GerritAccount'):
        return requests.utils.dict_from_cookiejar(ss.cookies)['GerritAccount']
    else:
        print 'Could not authenticate'
        raise SystemExit