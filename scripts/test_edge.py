import urllib.request
import json

url = "https://b82wq2xh-8000.inc1.devtunnels.ms/api/v1/workspaces/27c383d5-c97c-48f6-9151-7787f9fb299d/edges"
data = {
    "source": "90b94866-22a4-499b-9e14-dc72f7031984",
    "target": "1d2b01dd-8541-4583-b014-2f4ec4276854",
    "type": "related_to"
}
req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as response:
        print("Success:", response.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.read().decode())
