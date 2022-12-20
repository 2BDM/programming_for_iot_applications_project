import requests

address = "https://wttr.in/Turin?format=j1"
r1 = requests.get(address)
print(r1.status_code)
payload = r1.json
#print(r1.text)
