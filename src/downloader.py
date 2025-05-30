import os
import threading
import requests
from tqdm import tqdm
from .utils import split_ranges, get_file_info

class SegmentDownloader(threading.Thread):
    def __init__(self, url, start, end, index, temp_folder, results_dict, retries=3, timeout=(5, 30)):
        super().__init__()
        self.url = url
        self.start = start
        self.end = end
        self.index = index
        self.temp_folder = temp_folder
        self.results = results_dict  
        self.retries = retries
        self.timeout = timeout
        self.part_path = os.path.join(temp_folder, f"part_{index}")
        self.total_downloaded = 0 

    def run(self):
        headers = { 'Range': f'bytes={self.start}-{self.end}' }
        attempt = 0
        while attempt < self.retries:
            try:
                mode = 'ab' if os.path.exists(self.part_path) else 'wb'
                existing_size = os.path.getsize(self.part_path) if os.path.exists(self.part_path) else 0
                if existing_size > 0:
                    new_start = self.start + existing_size
                    if new_start > self.end:
                        self.results[self.index] = True
                        return
                    headers['Range'] = f'bytes={new_start}-{self.end}'
                    mode = 'ab'
                with requests.get(self.url, headers=headers, stream=True, timeout=self.timeout) as resp:
                    resp.raise_for_status()
                    with open(self.part_path, mode) as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                self.total_downloaded += len(chunk)
                self.results[self.index] = True
                return
            except Exception as e:
                attempt += 1
                if attempt >= self.retries:
                    self.results[self.index] = False
                    return


def merge_parts(output_path, temp_folder, num_parts):
    """
    Merge all part files (part_0, part_1, ..., part_{num_parts-1}) into the final output.
    """
    with open(output_path, 'wb') as outfile:
        for i in range(num_parts):
            part_path = os.path.join(temp_folder, f"part_{i}")
            if not os.path.exists(part_path):
                raise FileNotFoundError(f"Missing part file: {part_path}")
            with open(part_path, 'rb') as pf:
                while True:
                    chunk = pf.read(8192)
                    if not chunk:
                        break
                    outfile.write(chunk)
    for i in range(num_parts):
        os.remove(os.path.join(temp_folder, f"part_{i}"))
    try:
        os.rmdir(temp_folder)
    except OSError:
        pass


def download(url, output_path, connections=4, resume=False):
    total_size, accepts_ranges = get_file_info(url)
    if not accepts_ranges or connections == 1:
        from .utils import download_whole_file
        print("Server does not support Range requests or single connection specified. Using single-stream mode.")
        download_whole_file(url, output_path)
        return
    temp_folder = output_path + '_parts'
    os.makedirs(temp_folder, exist_ok=True)

    ranges = split_ranges(total_size, connections)
    results = {i: False for i in range(connections)}

    threads = []
    for i, (start, end) in enumerate(ranges):
        seg_thread = SegmentDownloader(url, start, end, i, temp_folder, results)
        threads.append(seg_thread)
        seg_thread.start()
    for t in threads:
        t.join()
    failed_parts = [idx for idx, ok in results.items() if not ok]
    if failed_parts:
        raise RuntimeError(f"Download failed for parts: {failed_parts}")
    merge_parts(output_path, temp_folder, connections)
    print(f"Download complete: {output_path}")


def download_whole_file(url, output_path, timeout=(5, 30)):
    """
    Download the entire file in one request (no range support).
    """
    with requests.get(url, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)