import requests

'''
url = "http://127.0.0.1:8000/users/"
data = {
  "email" : "jfrends@comcast.net",
  "username": "my_epic_username",
  "password": "12345"
}


response = requests.post(url,  json=data)
print(response.json())
'''

url = "http://127.0.0.1:8000/users/6966fec3c7eac7ca75ad25a0/files"
files = {
    "file": open("./test_file.txt", "rb")
}
data = {
    "path": "/home/"
}

response = requests.post(url, files=files, json=data)
print(response.json())