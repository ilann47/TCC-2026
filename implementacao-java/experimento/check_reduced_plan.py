"""Read-only v2 preflight usable on WSL without Node or additional packages."""
import argparse
import importlib.util
from pathlib import Path
import sys
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('reduced', Path(__file__).with_name('reduced_campaign.py'))
reduced = importlib.util.module_from_spec(spec);spec.loader.exec_module(reduced)


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('plan');parser.add_argument('--require-unused', action='store_true');parser.add_argument('--allow-pending', action='store_true');args = parser.parse_args()
    f = reduced.read(reduced.APP / 'experimento/FROZEN-PROTOCOL.json')
    if f.get('schema_version') != 2 or f['status'] not in ('pilot_pending', 'ready_for_definitive_runs'): raise ValueError('V2 inválida')
    ready = f['status'] == 'ready_for_definitive_runs'
    if not ready and (not args.allow_pending or args.require_unused): raise ValueError('V2 não congelada; execução definitiva proibida')
    expected = reduced.APP / f['report'] / f['plan'];plan = Path(args.plan).resolve()
    if plan != expected.resolve(): raise ValueError('Caminho não é o plano congelado')
    if reduced.sha(plan.read_bytes()) != f['plan_sha256']: raise ValueError('Plano alterado')
    checks = [('base_compose_sha256', reduced.APP / 'docker-compose.yml'), ('observer_compose_sha256', reduced.APP / 'experimento/compose.yml'), ('controller_sha256', Path(__file__).with_name('reduced_campaign.py')), ('reduced_policy_sha256', reduced.POLICY)]
    if ready: checks.append(('pilot_catalog_sha256', reduced.REPORT / 'pilot-catalog.json'))
    for key, path in checks:
        if reduced.sha(path.read_bytes()) != f[key]: raise ValueError('Fingerprint divergente: ' + key)
    if reduced.instrument_hash() != f['instrument_source_sha256']: raise ValueError('Instrumentação alterada')
    if f.get('analytical_amendment'):
        import qualified_analysis
        qualified_analysis.verify_extension(f)
        if args.require_unused: raise ValueError('A1 exige audit-amendment e launch-reviewed-campaign, sem repetir UUIDs')
    rows = reduced.plan_rows(plan);reduced.validate_plan(rows)
    if args.require_unused:
        if any(reduced.folder(row).exists() for row in rows): raise ValueError('UUID definitivo já usado; não iniciar nem sobrescrever')
        if reduced.read(reduced.STATE)['phase'] != 'pilot_complete': raise ValueError('Estado não permite iniciar campanha')
    reduced.clean()
    print('V2: 65 UUIDs e hashes conferidos; nenhuma carga enviada. Estado: ' + ('congelado' if ready else 'piloto pendente; definitivos proibidos'))


if __name__ == '__main__': main()
