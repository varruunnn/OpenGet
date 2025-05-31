import os
import threading
import time
import subprocess
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
import pytest

class TestHTTPServer(threading.Thread):
    def __init__(self, directory, port=8000):
        super().__init__(daemon=True)
        self.port = port
        self.directory = directory
        self.httpd = None

    def run(self):
        os.chdir(self.directory)
        handler = SimpleHTTPRequestHandler
        self.httpd = HTTPServer(('localhost', self.port), handler)
        self.httpd.serve_forever()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()

@pytest.fixture(scope='module')
def http_server(tmp_path_factory):
    tmpdir = tmp_path_factory.mktemp('data')
    test_file = tmpdir / 'large.bin'
    with open(test_file, 'wb') as f:
        f.write(os.urandom(1024 * 1024))  # 1 MB

    server = TestHTTPServer(str(tmpdir), port=8000)
    server.start()
    time.sleep(1)  
    yield 'http://localhost:8000/large.bin'
    server.stop()

def test_parallel_download(tmp_path, http_server):
    url = http_server
    output = tmp_path / 'downloaded.bin'
    cmd = [
        sys.executable, '-m', 'src.cli',
        '--url', url,
        '--output', str(output),
        '--connections', '4'
    ]
    result = subprocess.run(cmd, capture_output=True)
    assert result.returncode == 0
    # Verify file size matches the original 1 MB
    assert output.stat().st_size == 1024 * 1024

def test_resume_download(tmp_path, http_server):
    url = http_server
    output = tmp_path / 'resumable.bin'
    # Start download and kill after 1 second
    proc = subprocess.Popen([
        sys.executable, '-m', 'src.cli',
        '--url', url,
        '--output', str(output),
        '--connections', '4'
    ])
    time.sleep(1)
    proc.terminate()
    proc.wait()
    # Now resume
    cmd = [
        sys.executable, '-m', 'src.cli',
        '--url', url,
        '--output', str(output),
        '--connections', '4',
        '--resume'
    ]
    result = subprocess.run(cmd, capture_output=True)
    assert result.returncode == 0
    assert output.stat().st_size == 1024 * 1024
