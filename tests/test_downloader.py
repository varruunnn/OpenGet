import os
import pytest
from pathlib import Path

from src.downloader import merge_parts, download_whole_file

def test_merge_parts(tmp_path):
    temp_folder = tmp_path / "parts"
    temp_folder.mkdir()
    data_parts = [b'AAA', b'BBBB', b'CC']
    for i, data in enumerate(data_parts):
        part_file = temp_folder / f"part_{i}"
        part_file.write_bytes(data)

    output_file = tmp_path / "output.bin"
    merge_parts(str(output_file), str(temp_folder), num_parts=len(data_parts))
    assert output_file.read_bytes() == b'AAABBBBCC'
    assert not (temp_folder.exists() and any(temp_folder.iterdir()))

def test_download_whole_file(tmp_path, requests_mock):
    url = 'http://example.com/small'
    data = b'Hello, World!'
    requests_mock.get(url, content=data, status_code=200)

    output = tmp_path / "hello.txt"
    download_whole_file(url, str(output))
    assert output.read_bytes() == data

def test_merge_missing_part(tmp_path):
    temp_folder = tmp_path / "parts2"
    temp_folder.mkdir()
    (temp_folder / "part_0").write_bytes(b'A')
    (temp_folder / "part_2").write_bytes(b'C')

    output_file = tmp_path / "out2.bin"
    with pytest.raises(FileNotFoundError):
        merge_parts(str(output_file), str(temp_folder), num_parts=3)
