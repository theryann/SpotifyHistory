import requests
import urllib.parse
import base64


print('input client_id and secret_id. they are ound in the spotify dashbord of the project')

client_id = input('client id: ').strip()
secret_id = input('client secret: ').strip()

scopes = [
    'user-read-recently-played',
    'user-top-read',
    'user-library-read',
    'playlist-modify-public',
    'playlist-modify-private',
    'playlist-read-private',
]

plain_redirect_uri = "https://github.com/theryann"

### FUNKTIONIERENDE URI. DAS SO IN BROWSER SEARCHABR PASTEN (Redirect muss genau mit registrierter überisnstimmen aber url encoded sein)
uri = 'https://accounts.spotify.com/authorize' \
        + '?client_id=' + client_id \
        + '&response_type=code' \
        + '&redirect_uri=' + urllib.parse.quote_plus(plain_redirect_uri) \
        + '&scope=' + urllib.parse.quote( ' '.join(scopes) )

print('paste the following URL in a browser and accept.')
print('this will redirect to a url which will include the access code as a parameter.')
print('if you already have an access code just paste it here and don\'t follow the link\n')

print(uri)
print('\nnow paste the access code here')
access_code: str = input('access code: ').strip()

print('\nrequest new refresh token...')
client_id_and_secret_base64_encoded = base64.b64encode( f'{client_id}:{secret_id}'.encode() ).decode()


refresh_token_res = requests.post(
    'https://accounts.spotify.com/api/token',
    data={
        "redirect_uri": plain_redirect_uri,
        "grant_type": "authorization_code",
        "code": access_code
    },
    headers={
        "Authorization": "Basic " + client_id_and_secret_base64_encoded,
        'Content-Type': 'application/x-www-form-urlencoded',
    }
)

res_dict: dict = refresh_token_res.json()

print('received following response:')
for key, val in res_dict.items():
    print('\t',key + ':' , val)

print('\nNEW REFRESH TOKEN:')
print(res_dict['refresh_token'])
