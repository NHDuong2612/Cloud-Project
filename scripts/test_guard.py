"""Prove that the project guard rules reject unsafe template mutations."""

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guard-bin", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("template_builders", root / "scripts/build_templates.py")
    builders = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builders)
    cases = []
    template = builders.t01()
    template["Resources"]["Instance"]["Properties"]["BlockDeviceMappings"][0]["Ebs"]["Encrypted"] = False
    cases.append(("unencrypted-ebs", template))
    template = builders.t01()
    template["Resources"]["InstanceRole"]["Properties"].pop("PermissionsBoundary")
    cases.append(("unbounded-role", template))
    template = builders.t03()
    template["Resources"]["InstanceSecurityGroup"]["Properties"]["SecurityGroupIngress"][0]["CidrIp"] = "0.0.0.0/0"
    cases.append(("worldwide-ingress", template))
    template = builders.t03()
    template["Resources"]["InstanceSecurityGroup"]["Properties"]["SecurityGroupIngress"][0]["CidrIp"] = {"Ref": "UnapprovedCidr"}
    cases.append(("unapproved-cidr-reference", template))
    template = builders.t03()
    template["Resources"]["Database"]["Properties"]["PubliclyAccessible"] = True
    cases.append(("public-database", template))
    template = builders.t04()
    template["Resources"]["Listener"]["Properties"]["Protocol"] = "HTTP"
    cases.append(("plaintext-load-balancer", template))
    template = builders.t06()
    template["Resources"]["TaskDefinition"]["Properties"]["ContainerDefinitions"][0]["ReadonlyRootFilesystem"] = False
    cases.append(("writable-container-root", template))
    directory = (root / "build" / "guard-negative").resolve()
    if not directory.is_relative_to(root):
        raise ValueError("Guard fixtures must stay inside the workspace.")
    directory.mkdir(parents=True, exist_ok=True)
    for name, body in cases:
        path = directory / f"{name}.json"
        path.write_text(json.dumps(body), encoding="utf-8")
        result = subprocess.run([args.guard_bin, "validate", "--rules", str(root / "security/cloudhub.guard"), "--data", str(path), "--output-format", "json"], capture_output=True, text=True, check=False)
        if result.returncode == 0 or '"status": "FAIL"' not in result.stdout:
            raise RuntimeError(f"Guard failed to reject {name}: {result.stderr}")
        print(f"Rejected: {name}")


if __name__ == "__main__":
    main()
