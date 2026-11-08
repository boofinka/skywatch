#!/usr/bin/env python3

import json
import shutil
import subprocess


def get_inventory():
    multipass_bin = (
        shutil.which("multipass.exe")
        or shutil.which("multipass")
        or "multipass.exe"
    )

    result = subprocess.run(
        [multipass_bin, "list", "--format", "json"],
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
        "control": {
            "hosts": []
        },
        "k3s_agents": {
            "hosts": []
        },
        "workers": {
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

    for vm in data.get("list", []):
        if vm.get("state") != "Running":
            continue

        name = vm["name"]
        ipv4_list = vm.get("ipv4", [])
        if not ipv4_list:
            continue

        # First IP is the real VM IP
        ip = ipv4_list[0]

        inventory["_meta"]["hostvars"][name] = {
            "ansible_host": ip
        }

        if name == "skywatch-cp":
            inventory["k3s_server"]["hosts"].append(name)
            inventory["control"]["hosts"].append(name)

        elif name.startswith("skywatch-worker"):
            inventory["k3s_agents"]["hosts"].append(name)
            inventory["workers"]["hosts"].append(name)

    return inventory


if __name__ == "__main__":
    print(json.dumps(get_inventory(), indent=2))
