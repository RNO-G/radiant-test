import json
import argparse


tests_with_large_output = ["BiasScan"]


parser = argparse.ArgumentParser()
parser.add_argument("files", type=str, nargs="*", help="Json files to add comments to")
parser.add_argument("-c", "--comment", type=str, default=None, help="Comment")
parser.add_argument("-m", "--mode", default="add", type=str, choices=["a", "add", "r", "replace"],
                    help="What do to: (a)dd comment to an existing one, (r)eplace  entire comment.")
parser.add_argument("-f", "--force", action="store_true", help="Do not ask for confirmation")

args = parser.parse_args()

for fn in args.files:
    with open(fn, "r+") as file:
        data = json.load(file)

        if "dut_uid" not in data:
            raise ValueError(f"\"dut_uid not in file. Is that a correct json file: {fn}")

        if "comments" not in data:
            data["comments"] = None

        comment = data["comments"]

        if args.mode in ["a", "add"]:
            if comment is None:
                comment = args.comment
            else:
                if not comment.endswith(" "):
                    comment += " "
                comment += args.comment
        elif args.mode in ["r", "replace"]:
            if comment is None:
                comment = args.comment
            else:
                if not args.force:
                    yn = input(f"Do you want to overwrite this comment:\n\t{comment}\nBy this comment:\n\t{args.comment}\n[y/n]")
                    if yn == "y":
                        comment = args.comment
                    else:
                        continue

        data["comments"] = comment

        file.seek(0)  # rewind
        if data["test_name"] in tests_with_large_output:
            json.dump(data, file)
        else:
            json.dump(data, file, indent=4)
        file.truncate()
