import requests
from bs4 import BeautifulSoup
import re
url = 'https://infoloker.karawangkab.go.id/Dashboard_pelamar'
req = requests.get(url, allow_redirects=True)
print("Redirect URL:", req.url)
soup = BeautifulSoup(req.text, 'html.parser')
csrf = soup.find('input', {'name': 'ini_csrf'})
print("CSRF found on redirect page?", csrf is not None)
if csrf:
    print("CSRF value:", csrf['value'])

h_ajax = {'X-Requested-With': 'XMLHttpRequest'}
payload = {'draw': '1', 'start': '0', 'length': '10', 'ini_csrf': csrf['value'] if csrf else ''}
req_jobs = requests.post('https://infoloker.karawangkab.go.id/Dashboard_pelamar/lowongan_new', data=payload, headers=h_ajax)
links = re.findall(r'<a target="_blank" href="[^"]*?detail_lowongan/([^"]+)">(.*?)</a>', req_jobs.text, re.DOTALL)
print("Jobs found while logged out:", len(links))
print("Jobs HTML snapshot:", req_jobs.text[:200])
