import http.client, json
c = http.client.HTTPConnection("localhost", 11434, timeout=10)
c.request("GET", "/api/ps")
r = c.getresponse()
print(r.status)
print(r.read().decode()[:2000])
