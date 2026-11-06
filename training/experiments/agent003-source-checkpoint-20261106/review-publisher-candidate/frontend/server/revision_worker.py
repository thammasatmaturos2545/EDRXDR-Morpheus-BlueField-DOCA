"""Candidate stdio bridge. Named authentication remains in revision_reader."""
import argparse, json, os, sys
from pathlib import Path
import decision_review as legacy
import revision_reader

def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--catalog-sha256', required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(legacy.MAX_REQUEST + 1)
        legacy.need(len(raw) <= legacy.MAX_REQUEST, 'REQUEST_LIMIT', 413)
        result = revision_reader.handle(
            legacy.parse_json(raw), Path(args.root), args.catalog_sha256)
    except legacy.Rejected as error:
        result = {'status': error.status, 'body': {'error': error.code}}
    except Exception:
        result = {'status': 503, 'body': {'error': 'DECISION_REVIEW_UNAVAILABLE'}}
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))

if __name__ == '__main__':
    main()
