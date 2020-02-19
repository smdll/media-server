#! /usr/bin/python3
import sys
import os
import re
import argparse
import http.server

from socket import error as SocketError
from urllib.parse import quote, unquote
from posixpath import normpath
from io import StringIO
from os.path import (join, exists, abspath, isdir, basename,
    split, splitdrive)
from os import curdir, pardir, fstat

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith('/'):
            f = self.generate_playlist(self.serve_path)
            self.wfile.write(f.read().encode())
            f.close()
            return

        self.range_from, self.range_to = self._get_range_header()

        f = self.send_range_head()
        if f:
            self.copy_file_range(f, self.wfile)
            f.close()

    def copy_file_range(self, in_file, out_file):
        in_file.seek(self.range_from)
        left_to_copy = 1 + self.range_to - self.range_from
        buf_length = 64*1024
        bytes_copied = 0

        while bytes_copied < left_to_copy:
            read_buf = in_file.read(min(buf_length, left_to_copy))
            if len(read_buf) == 0:
                break
            try:
                out_file.write(read_buf)
            except ConnectionResetError:
                pass
            except ConnectionAbortedError:
                break
            bytes_copied += len(read_buf)
        return bytes_copied

    def send_range_head(self):
        path = self.translate_path(self.path)
        f = None
        if isdir(path):
            if not self.path.endswith('/'):
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None

        if not exists(path) and path.endswith('/data'):
            if exists(path[:-5]):
                path = path[:-5]

        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None

        if self.range_from is None:
            self.send_response(200)
        else:
            self.send_response(206)

        self.send_header("Content-type", ctype)
        fs = fstat(f.fileno())
        file_size = fs.st_size
        if self.range_from is not None:
            if self.range_to is None or self.range_to >= file_size:
                self.range_to = file_size-1
            self.send_header("Content-Range",
                             "bytes %d-%d/%d" % (self.range_from,
                                                 self.range_to,
                                                 file_size))
            self.send_header("Content-Length", 
                             (1 + self.range_to - self.range_from))
        else:
            self.send_header("Content-Length", str(file_size))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

    def generate_playlist(self, path) :
        media_list = [join(root, i) for root, dirs, files in os.walk(path) for i in files if self.is_video_file(i)]
        url = f"http://{self.host}:{self.port}/"
        length = len(path)
        f = StringIO()
        f.write("#EXTM3U\n")

        for track in media_list:
            basename = track[length+1:]
            basename = basename.replace('-', ' ').replace(',', ' ')
            track = track[length+1:]
            track = url + quote(track)
            f.write("#EXTINF" + ":-1" + "," + basename + "\n" + track + "\n")

        length = f.tell()
        f.seek(0)
        self.send_response(200)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-type", f"application/mpegurl; charset={encoding}")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def translate_path(self, path):
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = normpath(unquote(path))
        if sys.platform in ("win32", "cygwin"):
            words = path.split('\\')
        else:
            words = path.split('/')
        words = [_f for _f in words if _f]
        path = self.serve_path
        for word in words:
            drive, word = splitdrive(word)
            head, word = split(word)
            if word in (curdir, pardir): continue
            path = join(path, word)
        return path

    def _get_range_header(self):
        range_header = self.headers["Range"]
        if range_header is None:
            return (None, None)
        if not range_header.startswith("bytes="):
            return (None, None)
        regex = re.compile(r"^bytes=(\d+)\-(\d+)?")
        rangething = regex.search(range_header)
        if rangething:
            from_val = int(rangething.group(1))
            if rangething.group(2) is not None:
                return (from_val, int(rangething.group(2)))
            else:
                return (from_val, None)
        else:
            return (None, None)

    def is_video_file(self, filename):
        global video_file_extensions
        return True if filename.endswith((video_file_extensions)) else False

def main():
    parser = argparse.ArgumentParser(description="HTTP Media Server for VLC")
    parser.add_argument("--directory", "-d", default=".", help="Directory where the media is located")
    parser.add_argument("--host", "-H", default="127.0.0.1", help="Host the Media Server will serve at")
    parser.add_argument("--port", "-p", default=80, help="Port the Media Server will bind to", type=int)

    args = parser.parse_args()

    print(f"HTTP Media Server running on {sys.platform}")
    print(f"Run on the client: vlc http://{args.host}:{args.port}/")
    
    Handler = RequestHandler
    Handler.serve_path = abspath(args.directory)
    Handler.host = args.host
    Handler.port = args.port
    
    try:
        httpd = http.server.ThreadingHTTPServer(("", args.port), Handler)
        httpd.serve_forever()
    except SocketError:
        print("Address or port already in use, exiting.")
    except KeyboardInterrupt:
        print("KeyboardInterrupt caught, exiting...")

video_file_extensions = ( '.264', '.3g2', '.3gp', '.3gp2', '.3gpp', '.3gpp2', '.3mm', '.3p2', '.60d', '.787', '.89', '.aaf', '.aec', '.aep', '.aepx', '.aet', '.aetx', '.ajp', '.ale', '.am', '.amc', '.amv', '.amx', '.anim', '.aqt', '.arcut', '.arf', '.asf', '.asx', '.avb', '.avc', '.avd', '.avi', '.avp', '.avs', '.avs', '.avv', '.axm', '.bdm', '.bdmv', '.bdt2', '.bdt3', '.bik', '.bin', '.bix', '.bmk', '.bnp', '.box', '.bs4', '.bsf', '.bvr', '.byu', '.camproj', '.camrec', '.camv', '.ced', '.cel', '.cine', '.cip', '.clpi', '.cmmp', '.cmmtpl', '.cmproj', '.cmrec', '.cpi', '.cst', '.cvc', '.cx3', '.d2v', '.d3v', '.dat', '.dav', '.dce', '.dck', '.dcr', '.dcr', '.ddat', '.dif', '.dir', '.divx', '.dlx', '.dmb', '.dmsd', '.dmsd3d', '.dmsm', '.dmsm3d', '.dmss', '.dmx', '.dnc', '.dpa', '.dpg', '.dream', '.dsy', '.dv', '.dv-avi', '.dv4', '.dvdmedia', '.dvr', '.dvr-ms', '.dvx', '.dxr', '.dzm', '.dzp', '.dzt', '.edl', '.evo', '.eye', '.ezt', '.f4p', '.f4v', '.fbr', '.fbr', '.fbz', '.fcp', '.fcproject', '.ffd', '.flc', '.flh', '.fli', '.flv', '.flx', '.gfp', '.gl', '.gom', '.grasp', '.gts', '.gvi', '.gvp', '.h264', '.hdmov', '.hkm', '.ifo', '.imovieproj', '.imovieproject', '.ircp', '.irf', '.ism', '.ismc', '.ismv', '.iva', '.ivf', '.ivr', '.ivs', '.izz', '.izzy', '.jss', '.jts', '.jtv', '.k3g', '.kmv', '.ktn', '.lrec', '.lsf', '.lsx', '.m15', '.m1pg', '.m1v', '.m21', '.m21', '.m2a', '.m2p', '.m2t', '.m2ts', '.m2v', '.m4e', '.m4u', '.m4v', '.m75', '.mani', '.meta', '.mgv', '.mj2', '.mjp', '.mjpg', '.mk3d', '.mkv', '.mmv', '.mnv', '.mob', '.mod', '.modd', '.moff', '.moi', '.moov', '.mov', '.movie', '.mp21', '.mp21', '.mp2v', '.mp4', '.mp4v', '.mpe', '.mpeg', '.mpeg1', '.mpeg4', '.mpf', '.mpg', '.mpg2', '.mpgindex', '.mpl', '.mpl', '.mpls', '.mpsub', '.mpv', '.mpv2', '.mqv', '.msdvd', '.mse', '.msh', '.mswmm', '.mts', '.mtv', '.mvb', '.mvc', '.mvd', '.mve', '.mvex', '.mvp', '.mvp', '.mvy', '.mxf', '.mxv', '.mys', '.ncor', '.nsv', '.nut', '.nuv', '.nvc', '.ogm', '.ogv', '.ogx', '.osp', '.otrkey', '.pac', '.par', '.pds', '.pgi', '.photoshow', '.piv', '.pjs', '.playlist', '.plproj', '.pmf', '.pmv', '.pns', '.ppj', '.prel', '.pro', '.prproj', '.prtl', '.psb', '.psh', '.pssd', '.pva', '.pvr', '.pxv', '.qt', '.qtch', '.qtindex', '.qtl', '.qtm', '.qtz', '.r3d', '.rcd', '.rcproject', '.rdb', '.rec', '.rm', '.rmd', '.rmd', '.rmp', '.rms', '.rmv', '.rmvb', '.roq', '.rp', '.rsx', '.rts', '.rts', '.rum', '.rv', '.rvid', '.rvl', '.sbk', '.sbt', '.scc', '.scm', '.scm', '.scn', '.screenflow', '.sec', '.sedprj', '.seq', '.sfd', '.sfvidcap', '.siv', '.smi', '.smi', '.smil', '.smk', '.sml', '.smv', '.spl', '.sqz', '.srt', '.ssf', '.ssm', '.stl', '.str', '.stx', '.svi', '.swf', '.swi', '.swt', '.tda3mt', '.tdx', '.thp', '.tivo', '.tix', '.tod', '.tp', '.tp0', '.tpd', '.tpr', '.trp', '.ts', '.tsp', '.ttxt', '.tvs', '.usf', '.usm', '.vc1', '.vcpf', '.vcr', '.vcv', '.vdo', '.vdr', '.vdx', '.veg','.vem', '.vep', '.vf', '.vft', '.vfw', '.vfz', '.vgz', '.vid', '.video', '.viewlet', '.viv', '.vivo', '.vlab', '.vob', '.vp3', '.vp6', '.vp7', '.vpj', '.vro', '.vs4', '.vse', '.vsp', '.w32', '.wcp', '.webm', '.wlmp', '.wm', '.wmd', '.wmmp', '.wmv', '.wmx', '.wot', '.wp3', '.wpl', '.wtv', '.wve', '.wvx', '.xej', '.xel', '.xesc', '.xfl', '.xlmv', '.xmv', '.xvid', '.y4m', '.yog', '.yuv', '.zeg', '.zm1', '.zm2', '.zm3', '.zmv' )

if __name__ == "__main__" :
    main()
