HTTP Media Server for VLC
=========================

This is a HTTP media server for VLC, originated from animeshkundu's repository <a href="https://github.com/animeshkundu/media-server">here</a>, rewritten in Python3 and removed some of the features.

## Requirements

NOTHING other than Python3 standard library, not even `netifaces` from the original repo (and by doing so, you have to designate your IP address manually).

Runs okay on Windows, should work fine on Linux but not tested.


Usage
-----
python video.py [-h] [--directory DIRECTORY] [--host HOST] [--port PORT]


optional arguments:

  -h, --help                         show this help message and exit

  --directory DIRECTORY, -d DIRECTORY
                                          Directory where the media is located

  --host HOST, -H HOST  Host the Media Server will serve at

  --port PORT, -p PORT   Port the Media Server will bind to


Watch
------
Just run `vlc http://[HOST]:[PORT]/vlc`

**If you want to watch videos on H5 supported browser, I'd advise you to use WebDAV systems instead (like WsgiDAV). **


Misc
----
Many thanks for animeshkundu.

Issues and Pull Requests are welcome.