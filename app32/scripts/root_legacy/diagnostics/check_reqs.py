import pkg_resources
import sys

def check_requirements(requirements_file):
    with open(requirements_file, 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    missing = []
    for req in requirements:
        try:
            pkg_resources.require(req)
        except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict) as e:
            missing.append(str(e))
    
    if missing:
        print("Missing or conflicting requirements:")
        for m in missing:
            print(f"  - {m}")
    else:
        print("All requirements satisfied.")

if __name__ == "__main__":
    check_requirements('requirements.txt')
