#!/usr/bin/env python3
import json
import requests
from base64 import b64encode


class Imgur(object):

    url = "https://api.imgur.com/3/image?_format=json"

    def __init__(self, client_id):
        self.client_id = client_id

    def upload_image(self, filename):
        with open(filename, 'rb') as f:
            b64img = b64encode(f.read())

        headers = {"Authorization": "Client-ID %s" % self.client_id}
        r = requests.post(
            self.url,
            headers=headers,
            data={
                'image': b64img,
                'type': 'base64',
            }
        )
        ret = json.loads(r.text)
        if ret.get('status', None) != 200 or ret.get('success', False) != True:
            return None

        return ret.get('data', {}).get('link', None)


if __name__ == "__main__":
    import sys
    imgur = Imgur(sys.argv[1])
    print(imgur.upload_image(sys.argv[2]))


# vim: ts=4 sw=4 sts=4 expandtab
