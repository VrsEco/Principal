from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
LIMITS = {"skill": 80, "agent": 50, "router": 80}
PROJECT_SKILLS = {
    ROOT / 'skills' / 'gestao_versus_core' / 'SKILL.md',
    ROOT / 'skills' / 'workflow-factory-versus' / 'SKILL.md',
    ROOT / 'skills' / 'gestao-versus-incident-response' / 'SKILL.md',
    ROOT / 'skills' / 'deploy_gestao_versus' / 'SKILL.md',
    ROOT / 'skills' / 'bug-investigation-playbook' / 'SKILL.md',
}


def count_lines(path: Path) -> int:
    return len(path.read_text(encoding='utf-8').splitlines())


def check_group(label: str, files: list[Path], limit: int) -> list[str]:
    issues: list[str] = []
    for file in files:
        if not file.exists():
            continue
        lines = count_lines(file)
        if lines > limit:
            issues.append(f'[{label}] {file} possui {lines} linhas (limite sugerido {limit})')
    return issues


def main() -> int:
    issues: list[str] = []
    issues += check_group('agent', sorted((ROOT / 'agents').glob('*.md')), LIMITS['agent'])
    issues += check_group('router', sorted((ROOT / 'router').glob('*.md')), LIMITS['router'])
    issues += check_group('skill', sorted(PROJECT_SKILLS), LIMITS['skill'])

    if issues:
        print('Arquitetura de agentes/skills fora do padrão:\n')
        for issue in issues:
            print(f'- {issue}')
        return 1

    print('Arquitetura de agentes/skills do Gestão Versus validada com sucesso.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
