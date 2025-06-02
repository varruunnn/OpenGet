import os
import sys
import argparse
from .downloader import download

def parse_args():
    parser = argparse.ArgumentParser(
        description="MyDownloader: Parallel Download Manager"
    )
    parser.add_argument(
        '--url', '-u', type=str, required=True,
        help='URL of the file to download'
    )
    parser.add_argument(
        '--output', '-o', type=str, default=None,
        help='Output filename (default: derives from URL)'
    )
    parser.add_argument(
        '--connections', '-c', type=int, default=4,
        help='Number of parallel connections (default: 4)'
    )
    parser.add_argument(
        '--resume', '-r', action='store_true',
        help='Enable resume if partial files exist'
    )
    return parser.parse_args()

def derive_filename(url):
    basename = os.path.basename(url)
    if not basename:
        return 'downloaded_file'
    return basename

def main():
    args = parse_args()
    url = args.url
    output = args.output or derive_filename(url)
    download(url, output, connections=args.connections, resume=args.resume)
    # try:
    #     download(url, output, connections=args.connections, resume=args.resume)
    # except Exception as e:
    #     print(f"Error: {e}", file=sys.stderr)
    #     sys.exit(1)

if __name__ == '__main__':
    main()
