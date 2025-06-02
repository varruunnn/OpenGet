import os
import threading
import requests
from .utils import split_ranges, get_file_info, download_whole_file
from tqdm import tqdm

class SegmentDownloader(threading.Thread):
    def __init__(self, url, byte_start, byte_end, index, temp_folder, results_dict, retries=3, timeout=(5, 30)):
        super().__init__()
        self.url = url
        self.byte_start = byte_start
        self.byte_end = byte_end
        self.index = index
        self.temp_folder = temp_folder
        self.results = results_dict
        self.retries = retries
        self.timeout = timeout
        self.part_path = os.path.join(temp_folder, f"part_{index}")
        self.total_downloaded = 0

    def run(self):
        headers = {'Range': f'bytes={self.byte_start}-{self.byte_end}'}
        attempt = 0

        while attempt < self.retries:
            try:
                if os.path.exists(self.part_path):
                    existing_size = os.path.getsize(self.part_path)
                else:
                    existing_size = 0

                if existing_size > 0:
                    new_start = self.byte_start + existing_size
                    if new_start > self.byte_end:
                        self.results[self.index] = True
                        return
                    headers['Range'] = f'bytes={new_start}-{self.byte_end}'
                    mode = 'ab'
                else:
                    mode = 'wb'

                with requests.get(self.url, headers=headers, stream=True, timeout=self.timeout) as resp:
                    resp.raise_for_status()
                    with open(self.part_path, mode) as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                self.total_downloaded += len(chunk)

                self.results[self.index] = True
                return

            except Exception:
                attempt += 1
                if attempt >= self.retries:
                    self.results[self.index] = False
                    return

def merge_parts(output_path, temp_folder, num_parts):
    with open(output_path, 'wb') as outfile:
        for i in range(num_parts):
            part_file = os.path.join(temp_folder, f"part_{i}")
            if not os.path.exists(part_file):
                raise FileNotFoundError(f"Missing part file: {part_file}")
            with open(part_file, 'rb') as pf:
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
        print("Server does not support Range requests or single connection specified.")
        download_whole_file(url, output_path)
        return

    temp_folder = output_path + '_parts'
    os.makedirs(temp_folder, exist_ok=True)

    ranges = split_ranges(total_size, connections)
    results = {i: False for i in range(connections)}
    threads = []

    for i, (start, end) in enumerate(ranges):
        seg_thread = SegmentDownloader(
            url=url,
            byte_start=start,
            byte_end=end,
            index=i,
            temp_folder=temp_folder,
            results_dict=results
        )
        threads.append(seg_thread)
        seg_thread.start()

    for t in threads:
        t.join()

    failed_parts = [i for i, ok in results.items() if not ok]
    if failed_parts:
        raise RuntimeError(f"Download failed for parts: {failed_parts}")

    merge_parts(output_path, temp_folder, connections)
    print(f"Download complete: {output_path}")
