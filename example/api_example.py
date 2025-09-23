import requests
import hexss.env

hexss.env.unset_proxy()

r = requests.post(
    'http://127.0.0.1:3000/api/change_image',
    files={'image': open('image.png', 'rb')}
)
print(r.status_code, r.text)

r = requests.post(
    'http://127.0.0.1:3000/',
    data={'button': 'Predict'}
)
print(r.status_code)
