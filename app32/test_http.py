
import requests

s = requests.Session()
# Login
resp_login = s.post('http://127.0.0.1:5032/login', data={'email': 'admin@configr.com', 'password': 'admin'})
print("Login status:", resp_login.status_code)
# Portal -> Set company
# It seems login redirects to portal. 
# We don't need to select company via POST, portal does it or we can just hit /incentives?
# Let's hit /portal to see if it sets anything
resp_portal = s.get('http://127.0.0.1:5032/portal')

# Let's force company 1 via API if we need to? Or just hit incentives
resp_inc = s.get('http://127.0.0.1:5032/incentives')
print("Incentives status:", resp_inc.status_code)
if resp_inc.status_code == 500:
    print(resp_inc.text[:1000])
else:
    print("Success, length:", len(resp_inc.text))
