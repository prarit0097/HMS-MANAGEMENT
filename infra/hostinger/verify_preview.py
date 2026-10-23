"""HTTPS deployment smoke checks; credentials only from private bootstrap JSON.

Run on the VPS after preview publication. Prints assertions only, never secrets.
"""
import base64
import http.cookiejar
import json
from pathlib import Path
import ssl
import urllib.error
import urllib.request

access = json.loads(Path('/opt/hms/secrets/owner-access.json').read_text())
base = access['url']
credentials = base64.b64encode((access['username']+':'+access['password']).encode()).decode()
cookies = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
def request(path, method='GET', body=None, *, basic=True, csrf=False, headers=None):
    supplied = dict(headers or {})
    if method not in {'GET', 'HEAD', 'OPTIONS'}:
        supplied['Origin'] = base
    if basic:
        supplied['Authorization'] = 'Basic '+credentials
    if csrf:
        supplied['X-CSRFToken'] = next(cookie.value for cookie in cookies if cookie.name=='csrftoken')
    data = None if body is None else json.dumps(body).encode()
    if data is not None:
        supplied['Content-Type'] = 'application/json'
    try:
        response=opener.open(urllib.request.Request(base+path, data=data, method=method, headers=supplied), timeout=15)
    except urllib.error.HTTPError as error:
        response=error
    return response.status, response.headers, response.read()

assert request('/', basic=False)[0] == 401
print('PASS outer authentication required')
status, headers, body = request('/')
assert status == 200 and b'<div id="root">' in body
for header in ['Strict-Transport-Security', 'X-Content-Type-Options', 'Content-Security-Policy', 'X-Frame-Options']:
    assert headers.get(header)
print('PASS HTTPS static app and browser security headers')
assert request('/api/v1/health/')[0] == 200
assert request('/api/v1/patients/')[0] in {401,403}
assert request('/.env')[0] in {403,404}
assert request('/backend/hms/settings.py')[2].startswith(b'<!doctype html>')
print('PASS protected API denial and no repository file serving')
assert request('/api/v1/auth/login/', 'POST', {'username':access['username'], 'password':access['password']})[0] == 403
assert request('/api/v1/auth/csrf/')[0] == 200
csrf_cookie=next(cookie for cookie in cookies if cookie.name=='csrftoken')
assert csrf_cookie.secure
assert request('/api/v1/auth/login/', 'POST', {'username':access['username'], 'password':access['password']}, csrf=True)[0] == 200
session_cookie=next(cookie for cookie in cookies if cookie.name=='sessionid')
assert session_cookie.secure and 'HttpOnly' in session_cookie._rest
assert session_cookie._rest.get('SameSite')=='Lax'
assert request('/api/v1/auth/me/')[0] == 200
assert request('/api/v1/patients/', 'POST', {})[0] == 403
print('PASS session login, secure HttpOnly SameSite cookies and mutation CSRF denial')
status, _, body=request('/api/v1/beds/?limit=25&offset=100')
assert status == 200 and json.loads(body)['count'] == 120 and len(json.loads(body)['results'])==20
assert request('/api/v1/patients/?branch=00000000-0000-0000-0000-000000000000')[0] == 403
print('PASS bed101+ API pagination and invalid branch scope denial')
assert request('/api/v1/auth/logout/', 'POST', {}, csrf=True)[0] == 204
assert request('/api/v1/auth/me/')[0] in {401,403}
print('PASS logout invalidates application session')
statuses=[]
for i in range(9):
    statuses.append(request('/api/v1/auth/login/', 'POST', {'username':'invalid-preview-check', 'password':'invalid'}, csrf=True, headers={'X-Forwarded-For':f'198.51.100.{i+1}'})[0])
assert 429 in statuses, statuses
print('PASS shared edge login throttling despite changing forged forwarded IPs')
