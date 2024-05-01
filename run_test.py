import argparse
import logging
import time
import radiant_test

def run(args, host):
    for test in args.tests:
        test_class = getattr(module, test)
        t0 = time.time()
        test_obj = radiant_test.run(test_class, {"comment": args.comment}, host=host)
        logging.info(f"Test {test} finished in {time.time() - t0:.2f} s")
        if args.plot:
            scripts = __import__("scripts")
            try:
                import os
                script = getattr(scripts, test + "_plot")
                print(f"Run python {script.__file__} {test_obj.fname}")
                os.system(f"python {script.__file__} {test_obj.fname}")
            except AttributeError:
                print(f"Not plotting script for {test} found!")

module = __import__("tests")
tests = [t for t in module.__dir__() if not t.startswith("__")]

parser = argparse.ArgumentParser()
parser.add_argument("tests", type=str, nargs="+", choices=tests, help="Test to execute")
parser.add_argument("--comment", type=str, default=None, help="add a comment to the result dict of every test")
parser.add_argument("--host", "--hosts", dest="hosts", type=str, default=[None], nargs="+",
                    help="Specify ip address of host. If `None`, use ip from config in stationrc.")
parser.add_argument("--debug", action="store_true", help="Set logger setting to DEBUG")
parser.add_argument("--parallel", action="store_true", help="Set logger setting to DEBUG")
parser.add_argument("--plot", action="store_true", help="Run the plotting script (if available)")
args = parser.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

if args.parallel:
    raise NotImplementedError("Parallel mode is not yet implemented")

else:
    for host in args.hosts:
        run(args, host)