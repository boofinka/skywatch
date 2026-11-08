#!/usr/bin/env python3

import json
import subprocess


def get_inventory():
    result = subprocess.run(
        ["multipass.exe", "list", "--format", "json"],
        capture_output=True,
        text=True,
        check=True
    )

    data = json.loads(result.stdout)

    inventory = {
        "_meta": {
            "hostvars": {}
        },
        "k3s_server": {
            "hosts": []
        },
        "k3s_agents": {
            "hosts": []
        },
        "k3s_cluster": {
            "children": [
                "k3s_server",
                "k3s_agents"
            ],
            "vars": {
                "ansible_user": "ubuntu",
                "ansible_python_interpreter": "/usr/bin/python3"
            }
        }
    }

    for vm in data["list"]:
        if vm["state"] != "Running":
            continue

        name = vm["name"]

        # First IP is the real VM IP
        ip = vm["ipv4"][0]

        inventory["_meta"]["hostvars"][name] = {
            "ansible_host": ip
        }

        if name == "skywatch-cp":
            inventory["k3s_server"]["hosts"].append(name)

        elif name.startswith("skywatch-worker"):
            inventory["k3s_agents"]["hosts"].append(name)

    return inventory


if __name__ == "__main__":
    print(json.dumps(get_inventory(), indent=2))