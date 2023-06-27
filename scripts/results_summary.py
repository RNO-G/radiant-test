import json
import logging
import pathlib

import radiant_test


def summarize_directory(path, failed_only=False, verbose=False):
    p = pathlib.Path(path)
    if not p.is_dir():
        logging.error(f"{p} is not a directory")
        return
    for filename in p.glob("*.json"):
        summarize_file(filename, failed_only, verbose)


def summarize_file(filename, failed_only=False, verbose=False):
    p = pathlib.Path(filename)
    with open(p, "r") as f:
        result_dict = json.load(f)
    radiant_test.Test.print_result(
        name=p, result_dict=result_dict, failed_only=failed_only, verbose=verbose
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, nargs="+", help="input files or directories")
    parser.add_argument(
        "-f",
        "--failed-only",
        dest="failed_only",
        action="store_true",
        help="only list failed tests",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print result of each measurement in test",
    )
    args = parser.parse_args()

    for input in args.input:
        p = pathlib.Path(input)
        if not p.exists():
            logging.error(f"File does not exist: {p}")
            continue
        if pathlib.Path(input).is_dir():
            summarize_directory(p, args.failed_only, args.verbose)
        else:
            summarize_file(p, args.failed_only, args.verbose)
