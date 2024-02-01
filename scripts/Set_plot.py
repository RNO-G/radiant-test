import argparse
import os
import glob
import re
import logging
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Set directory")

    args = parser.parse_args()

    if not os.path.isdir(args.input):
        raise ValueError(f"Pass a directory to this function: {args.input}")


    test_files = glob.glob(f"{args.input}/*json")
    scripts = glob.glob(f"{os.path.dirname(__file__)}/*_plot.py")

    test_files.sort()  # To have a defined order
    print(f"Found the following tests: {test_files}")
    for fn in test_files:

        any = False
        for script in scripts:
            test_name = os.path.basename(script).replace("_plot.py", "")
            if test_name == "Set":
                continue

            if re.search(test_name, fn) is not None:
                any = True
                break

        if not any:
            logging.info(f"Skip {fn}")
            continue

        logging.info(f"Run plotting script for {test_name} on {os.path.basename(fn)}")
        os.system(f"python3 {script} {fn}")