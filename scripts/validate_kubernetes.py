#!/usr/bin/env python3
"""Valida OFFLINE (sem acesso ao cluster) tudo que o ArgoCD vai aplicar.

Para cada kubernetes/{addons,apps}/<nome>/application.yaml ele faz o que o ArgoCD faria:
  - chart de um repositório Helm  -> `helm template` com a mesma versão e os mesmos values
  - pasta deste repo com Chart.yaml        -> `helm template`
  - pasta deste repo com kustomization.yaml -> `kubectl kustomize`
  - pasta deste repo com YAMLs soltos      -> lê os arquivos
e valida o resultado com kubeconform (esquemas do Kubernetes 1.34 + CRDs conhecidos).

Também valida os próprios arquivos Application, o kubernetes/bootstrap/root-app.yaml e
confere que o filtro `include` do root-app enxerga EXATAMENTE os Applications que existem
(um application.yaml fora do padrão ficaria invisível para o ArgoCD).

Sources de OUTROS repositórios (ex.: baofeng-airsoft-docs) são ignorados: não dá para
renderizá-los daqui.

Uso local:  python3 scripts/validate_kubernetes.py
Requer:     helm, kubectl, kubeconform e PyYAML (pip install pyyaml).
Sai com código 1 se QUALQUER validação falhar.
"""
import glob
import hashlib
import os
import subprocess
import sys
import tempfile

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THIS_REPO = "juanozorio/oke-cluster"
K8S_VERSION = "1.34.0"
CRD_CATALOG = (
    "https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/"
    "{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json"
)

failures = []


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def kubeconform(text, label, strict):
    """Valida um texto YAML. strict=True rejeita campos desconhecidos (typos)."""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(text)
        path = f.name
    cmd = [
        "kubeconform", "-summary", "-ignore-missing-schemas",
        "-kubernetes-version", K8S_VERSION,
        "-schema-location", "default", "-schema-location", CRD_CATALOG,
    ]
    if strict:
        cmd.append("-strict")
    cmd.append(path)
    r = run(cmd)
    os.unlink(path)
    summary = (r.stdout.strip().splitlines() or [""])[-1]
    if r.returncode == 0:
        print(f"  OK    {label}  [{summary}]")
        return True
    print(f"  FALHA {label}  [{summary}]")
    for line in (r.stdout + r.stderr).strip().splitlines()[:12]:
        print(f"        {line}")
    failures.append(label)
    return False


def helm_template(release, chart, namespace, values_files, version=None, repo_alias=None):
    cmd = ["helm", "template", release, chart, "--namespace", namespace]
    if version:
        cmd += ["--version", version]
    for vf in values_files:
        cmd += ["-f", vf]
    r = run(cmd)
    return r.returncode == 0, (r.stdout if r.returncode == 0 else r.stderr)


def values_files_for(src, app_name, tmp, local_chart_dir=None):
    """Monta a lista de arquivos de values (valuesObject + valueFiles) de um source."""
    files = []
    h = src.get("helm", {}) or {}
    for vf in h.get("valueFiles", []) or []:
        if vf.startswith("$values/"):
            files.append(os.path.join(ROOT, vf[len("$values/"):]))
        elif local_chart_dir:
            files.append(os.path.join(local_chart_dir, vf))
    if h.get("valuesObject"):
        p = os.path.join(tmp, f"{app_name}-valuesObject.yaml")
        with open(p, "w") as f:
            yaml.safe_dump(h["valuesObject"], f)
        files.append(p)
    return files


def validate_source(app, src, tmp):
    name = app["metadata"]["name"]
    ns = app["spec"]["destination"].get("namespace", "default")
    h = src.get("helm", {}) or {}
    release = h.get("releaseName", name)

    if "chart" in src:  # chart de um repositório Helm (add-ons de terceiros)
        alias = "r" + hashlib.sha1(src["repoURL"].encode()).hexdigest()[:8]
        run(["helm", "repo", "add", alias, src["repoURL"], "--force-update"])
        ok, out = helm_template(
            release, f"{alias}/{src['chart']}", ns,
            values_files_for(src, name, tmp), version=src.get("targetRevision"),
        )
        label = f"{name}: chart {src['chart']} {src.get('targetRevision')}"
        if not ok:
            print(f"  FALHA {label}  (helm template)\n        {out.strip()[:600]}")
            failures.append(label)
            return
        kubeconform(out, label, strict=False)  # vendor: não-estrito
        return

    if "path" in src:
        if THIS_REPO not in src.get("repoURL", ""):
            print(f"  PULA  {name}: source de outro repositório ({src['repoURL']})")
            return
        d = os.path.join(ROOT, src["path"])
        label = f"{name}: {src['path']}"
        if os.path.exists(os.path.join(d, "Chart.yaml")):
            ok, out = helm_template(release, d, ns, values_files_for(src, name, tmp, d))
        elif os.path.exists(os.path.join(d, "kustomization.yaml")):
            r = run(["kubectl", "kustomize", d])
            ok, out = r.returncode == 0, (r.stdout if r.returncode == 0 else r.stderr)
        else:
            files = sorted(glob.glob(os.path.join(d, "*.y*ml")))
            ok, out = bool(files), "\n---\n".join(open(f).read() for f in files)
        if not ok:
            print(f"  FALHA {label}\n        {out.strip()[:600]}")
            failures.append(label)
            return
        kubeconform(out, label, strict=True)  # nosso: estrito (pega typos)


def check_root_discovery(apps):
    """O include do root-app tem que casar com todos os application.yaml (e só com eles)."""
    root = yaml.safe_load(open(os.path.join(ROOT, "kubernetes", "bootstrap", "root-app.yaml")))
    include = root["spec"]["source"]["directory"]["include"]
    base = os.path.join(ROOT, root["spec"]["source"]["path"])
    # {a,b}/*/application.yaml -> expande as chaves e usa glob do shell
    head, tail = include.split("}", 1) if include.startswith("{") else ("", include)
    alts = head[1:].split(",") if head else [""]
    seen = set()
    for alt in alts:
        for f in glob.glob(os.path.join(base, alt + tail)):
            seen.add(os.path.realpath(f))
    expected = {os.path.realpath(f) for f in apps}
    label = "root-app: include enxerga todos os application.yaml"
    if seen == expected:
        print(f"  OK    {label}  [{len(seen)} Applications]")
    else:
        print(f"  FALHA {label}")
        for f in sorted(expected - seen):
            print(f"        invisível para o root: {os.path.relpath(f, ROOT)}")
        for f in sorted(seen - expected):
            print(f"        inesperado: {os.path.relpath(f, ROOT)}")
        failures.append(label)


def main():
    apps = sorted(glob.glob(os.path.join(ROOT, "kubernetes", "*", "*", "application.yaml")))
    root_file = os.path.join(ROOT, "kubernetes", "bootstrap", "root-app.yaml")
    print(f"== Application files ({len(apps)} + root-app) ==")
    for f in apps + [root_file]:
        kubeconform(open(f).read(), os.path.relpath(f, ROOT), strict=True)
    check_root_discovery([f for f in apps if "/bootstrap/" not in f])

    print("\n== Conteúdo que cada Application aplica ==")
    with tempfile.TemporaryDirectory() as tmp:
        for f in apps:
            app = yaml.safe_load(open(f))
            if app.get("kind") != "Application":
                continue
            sources = app["spec"].get("sources") or [app["spec"]["source"]]
            for src in sources:
                if "ref" in src and "chart" not in src and "path" not in src:
                    continue  # source auxiliar só de values ($values)
                validate_source(app, src, tmp)

    print()
    if failures:
        print(f"{len(failures)} validação(ões) FALHARAM:")
        for x in failures:
            print(f"  - {x}")
        sys.exit(1)
    print("Tudo válido.")


if __name__ == "__main__":
    main()
