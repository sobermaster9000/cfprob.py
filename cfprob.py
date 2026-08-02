from sys import argv
import argparse
import requests
from random import randint
import json

ALLOWED_RATINGS = [x*100 for x in range(8, 36)]
ALLOWED_TAGS = [
    "implementation",
    "math",
    "greedy",
    "dp",
    "data structures",
    "brute force",
    "constructive algorithms",
    "graphs",
    "sortings",
    "binary search",
    "dfs and similar",
    "trees",
    "strings",
    "number theory",
    "combinatorics",
    "geometry",
    "bitmasks",
    "two pointers",
    "dsu",
    "shortest paths",
    "probabilities",
    "divide and conquer",
    "hashing",
    "games",
    "flows",
    "interactive",
    "matrices",
    "string suffix structures",
    "fft",
    "graph matchings",
    "ternary search",
    "expression parsing",
    "meet-in-the-middle",
    "2-sat",
    "chinese remainder theorem",
    "schedules",
]

CODEFORCES_URL = "https://codeforces.com/"
API_ENDPOINT = CODEFORCES_URL + "api/"

DESCRIPTION = "A command line utility for suggesting problem from Codeforces, with limited ThemeCP support. Learn more about ThemeCPs here: https://codeforces.com/blog/entry/136704."

print_to_stdout = True

def _print(*args):
    if print_to_stdout:
        print(' '.join(args))

def _print_json(rating=None, tag=None, level=None, user=None, cf_only=False, problems=None):
    if print_to_stdout: return
    json_dict = {
            "rating": rating,
            "tag": tag,
            "level": level,
            "user": user,
            "cf_only": cf_only,
            "problems": problems
    }
    print(json.dumps(json_dict))

def is_cf_contest(contestId):
    try:
        response = requests.get(API_ENDPOINT + "contest.standings", params={"contestId": contestId})
        if response.status_code != requests.codes.ok:
            response.raise_for_status()
        return "codeforces round" in response.json()["result"]["contest"]["name"].lower()
    except Exception as e:
        # fallback return value
        return False

def get_user_handle(fallback_handle):
    saved_data = dict()
    try:
        with open("saved.json", "r") as file:
            saved_data = json.loads(file.read().strip())
    except FileNotFoundError:
        _print("[-] Cannot open saved.json")
    if fallback_handle is not None:
        return fallback_handle
    return saved_data.get("user_handle", fallback_handle)

def get_themecp_data(level):
    lines = []
    with open("themecp_level_sheet.csv", "r") as file:
        lines = [line.strip()  for line in file.readlines()]
    _, time, perf, p1, p2, p3, p4 = map(int, lines[level].split(","))
    return {
        "time": time,
        "perf": perf,
        "problem_ratings": [p1, p2, p3, p4]
    }

def suggest_problem(rating=None, tag=None, user_handle=None, themecp_problems=None, cf=False):
    solved_problems = set()
    if user_handle is not None:
        response = requests.get(API_ENDPOINT + "user.status", params={"handle": user_handle})
        if response.status_code != requests.codes.ok:
            response.raise_for_status()

        submissions = response.json()["result"]
        solved_problems = {(x["contestId"], x["problem"]["index"]) for x in submissions if x["verdict"] == "OK"}
            
    response = requests.get(API_ENDPOINT + "problemset.problems", params={"tags": tag if tag is not None else ""})
    if response.status_code != requests.codes.ok:
        response.raise_for_status()

    problems = response.json()["result"]["problems"]
    idx = randint(0, len(problems)//4) # starting index was set to this in order to accomodate for problems with updated ratings
    problem = None
    scanned = 0
    
    while True:
        idx = (idx + 1) % len(problems)
        problem = problems[idx]
        if scanned >= len(problems):
            raise Exception("Could not find requested problem")
        scanned += 1

        if rating is not None:
            if "rating" not in problem:
                continue
            if problem["rating"] != rating:
                continue

        if (problem["contestId"], problem["index"]) in solved_problems:
            continue

        if cf:
            if not is_cf_contest(problem["contestId"]):
                continue

        break

    if themecp_problems is not None:
        themecp_problems.add((problem["contestId"], problem["index"]))

    return CODEFORCES_URL + f"problemset/problem/{problem["contestId"]}/{problem["index"]}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("-r", "--rating", type=int, help=f"sets rating of problem to suggest; valid values for RATING:\n{', '.join([str(x) for x in ALLOWED_RATINGS])}")
    parser.add_argument("-t", "--tag", type=str, help=f"sets tag of problem to suggest; valid values for TAG (enclose multi-worded ones in quotes):\n{', '.join(ALLOWED_TAGS)}")
    parser.add_argument("-l", "--level", type=int, help="sets ThemeCP level, and suggests 4 problems based on that level; this cannot be used with -r/--rating; valid values for LEVEL are integers from 1 to 109")
    parser.add_argument("-u", "--user", type=str, help="sets user handle such that the suggested problem/s are ones that have not yet been solved by this user; overrides the current saved user handle")
    parser.add_argument("--set-user", type=str, help="saves user handle to check for, which eliminates the need to repeatedly include the user handle in the arguments")
    parser.add_argument("--cf", action="store_true", help="adding this flag blacklists problems from non-Codeforces contests")
    parser.add_argument("--json", action="store_true", help="outputs only the details about the suggested problem/s in JSON format")
    args = parser.parse_args()
    
    if args.rating is not None and args.rating not in ALLOWED_RATINGS:
        # print allowed values in two columns
        parser.error("argument value for -r/--rating is invalid")
    
    if args.tag is not None and args.tag not in ALLOWED_TAGS:
        # print allowed values in two columns
        parser.error("argument value for -t/--tag is invalid")
    
    if args.level is not None and args.rating is not None:
        parser.error("argument -l/--level cannot be used with -r/--rating")
    
    if args.level is not None:
        if args.level < 1 or args.level > 109:
            parser.error("argument value for -l/--level is invalid")
   
    print_to_stdout = (not args.json)

    if args.set_user is not None:
        saved_data = dict()
        try:
            with open("saved.json", "r") as file:
                saved_data = json.loads(file.read().strip())
        except FileNotFoundError:
            _print("[-] Could not open saved.json")
        saved_data["user_handle"] = args.set_user
        with open("saved.json", "w") as file:
            file.write(json.dumps(saved_data))
        _print(f"[+] User handle {args.set_user} saved")

    user_handle = get_user_handle(args.user)

    try:
        if args.level is None:
            if args.rating is not None:
                _print("[*] Rating present:", args.rating)
            if args.tag is not None:
                _print("[*] Tag present:", args.tag)
            if user_handle is not None:
                _print("[*] Using user handle:", user_handle)

            problem_link = suggest_problem(rating=args.rating, tag=args.tag, user_handle=user_handle, cf=args.cf)
            _print(f"[+] Suggested problem: {problem_link}")

            _print_json(rating=args.rating, tag=args.tag, level=args.level, user=user_handle, cf_only=args.cf, problems=[{"rating": args.rating, "link": problem_link}]) 
        else:
            _print("[*] ThemeCP level present:", args.level)
            if args.tag is not None:
                _print("[*] Tag present:", args.tag)
            if user_handle is not None:
                _print("[*] Using user handle:", user_handle)

            themecp_data = get_themecp_data(args.level)
            themecp_problems = set()

            _print("[+] Suggested problems:")
            _print("RATING\t|\tLINK")
            _print("-----------------------------------------------------------------")

            problems = []

            for rating in themecp_data["problem_ratings"]:
                problem_link = suggest_problem(rating=rating, tag=args.tag, user_handle=user_handle, themecp_problems=themecp_problems, cf=args.cf)
                _print(f"{rating}\t|\t{problem_link}")
                problems.append({"rating": rating, "link": problem_link})

            _print_json(rating=args.rating, tag=args.tag, level=args.level, user=user_handle, cf_only=args.cf, problems=problems)

    except Exception as e:
        _print("[!] An error occured while searching for problem/s:")
        _print(e)

# OPTIONAL:
# allow -t/--tag to receive multiple tags
