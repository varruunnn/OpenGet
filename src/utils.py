import requests

def get_file_info(url, timeout=(5, 10)):
    resp = requests.head(url, allow_redirects=True, timeout=timeout)
    resp.raise_for_status()
    content_length = resp.headers.get('Content-Length')
    if content_length is None:
        raise ValueError("Server did not provide Content-Length header.")
    total_size = int(content_length)
    accepts = resp.headers.get('Accept-Ranges', '').lower() == 'bytes'
    return total_size, accepts

def split_ranges(total_size, num_parts):
    part_size = total_size // num_parts
    ranges = []
    for i in range(num_parts):
        start = i * part_size
        end = total_size - 1 if i == num_parts - 1 else (i + 1) * part_size - 1
        ranges.append((start, end))
    return ranges

def download_whole_file(url, output_path, timeout=(5, 30)):
    with requests.get(url, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
