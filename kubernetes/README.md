# kubernetes/ — tudo que roda DENTRO do cluster (GitOps com ArgoCD)

Aqui ficam os add-ons (ingress-nginx, cert-manager, ...) e os apps (tududi, escalafacil,
...), versionados e gerenciados pelo **ArgoCD** que já roda no cluster. A fonte da
verdade do "o que está instalado" é este repositório, não o estado solto no cluster.

## A regra: uma pasta por coisa

Para mexer no Grafana, no tududi ou no ingress, abra a pasta com o nome dele. O
`application.yaml` (o "ponteiro" para o ArgoCD) e a configuração ficam **lado a lado**.

```
kubernetes/
  bootstrap/root-app.yaml      # o ÚNICO arquivo que se aplica à mão (App-of-Apps)
  addons/                      # infraestrutura de terceiros (charts Helm pinados)
    argocd/                    # o próprio ArgoCD (self-managed)
    cert-manager/              # sync-wave -1  (CRDs com keep)
    cluster-issuers/           # sync-wave 0   (emissor Let's Encrypt; manifests/)
    ingress-nginx/             # sync-wave 0   (NodePort 30080/30443 do NLB)
    metrics-server/            # sync-wave 1   (kubectl top / HPA)
    kube-prometheus-stack/     # sync-wave 2   (Prometheus+Grafana, sem persistência)
      application.yaml         #   chart + versão + namespace + política de sync
      values.yaml              #   a configuração (o que você edita no dia a dia)
  apps/                        # seus aplicativos
    tududi/                    # manifests/ (kustomize) + BACKUP.md
    escalafacil/               # chart/ (Helm próprio); produção em chart/values-prod.yaml
    baofeng-airsoft/           # só o Application; o chart está no repo do app
  ingress/                     # guia + modelo para expor um app (nada é aplicado)
```

Padrão dentro de cada pasta:

| Arquivo | Para quê |
|---|---|
| `application.yaml` | O ponteiro: de onde vem (chart/versão ou pasta), namespace, política de sync. |
| `values.yaml` | A configuração do chart de terceiros. **Edite aqui** para mudar um add-on. |
| `manifests/` ou `chart/` | O conteúdo, quando é nosso (kustomize ou Helm próprio). |

O root enxerga só `addons/*/application.yaml` e `apps/*/application.yaml`. Os outros
arquivos são lidos pelo Application da própria pasta, não pelo root.

## Bootstrap de um cluster novo (um comando)

Com o ArgoCD instalado e os Secrets criados à mão (`tududi-secrets`,
`tududi-litestream-s3`, `grafana-admin`):

```sh
kubectl apply -f kubernetes/bootstrap/root-app.yaml
```

O root cria todos os Applications, na ordem das sync-waves.

### Cuidado ao REMOVER um app

O root roda com `prune: false` de propósito. Os Applications têm o finalizer
`resources-finalizer`: apagar um `Application` apaga todos os recursos dele
(inclusive PVCs). Por isso apagar a pasta daqui **não** desinstala nada; para
desinstalar, faça `kubectl delete application <nome> -n argocd` conscientemente.

## O que vai (e o que NÃO vai) para o Git

O ArgoCD guarda cada `Application` como um objeto dentro do cluster. **Criar ou
editar um app pela interface do ArgoCD não grava nada no Git.** Se o cluster for
recriado, tudo que só existe na UI some (foi o caso do `baofeng-airsoft` até ser
exportado para cá). Regras:

- Crie/edite `Application` como YAML nesta árvore e abra um PR. A UI serve para
  **ver** estado, diff e logs, e para disparar sync.
- Mudança manual em recurso vivo (`kubectl edit`, `kubectl set image`, UI) fica
  como *drift*: com `selfHeal` o ArgoCD desfaz; sem ele, o app aparece `OutOfSync`.
- Credenciais de repositório e `Secret`s também ficam só no cluster; o `Secret`
  não vai para o Git (veja os `*.example.yaml`).

As versões estão **pinadas** exatamente nas que já rodam hoje:
| Add-on | Chart | App version |
|---|---|---|
| ingress-nginx | `4.14.3` | `1.14.3` |
| cert-manager | `v1.19.2` | `v1.19.2` |

## Como ADOTAR algo que já está instalado (procedimento validado)

Foi assim que ingress-nginx, cert-manager, escalafacil e tududi entraram no
ArgoCD sem derrubar nada. Adotar = o ArgoCD passar a ser o dono, **sem recriar**.

1. **Use os values REAIS**, não chutados: `helm get values <release> -n <ns>`.
   (Os meus primeiros values do ingress-nginx perderiam as annotations do NLB da
   OCI.) Se não era Helm, leia os args/resources do objeto vivo.
2. **Renderize e compare o pod template INTEIRO** com o vivo, sem filtrar labels:
   `helm template ... | kubectl diff -f -` e, para Deployments, compare
   `spec.template` campo a campo. Ignore apenas padrões que o apiserver preenche
   (`restartPolicy`, `schedulerName`, `terminationMessage*`, `defaultMode`).
   - Diferença em `resources`/`args` = alguém mexeu à mão: **copie para os values**.
   - Labels novas no template (`helm.sh/chart`, `managed-by`) recriam os pods
     (cert-manager reiniciou por isso): inofensivo para controllers sem estado,
     mas planeje para o que está no caminho do tráfego.
3. **CRDs**: compare `spec` de cada um. Use `crds.keep` e `ServerSideApply=true`.
4. Aplique o Application **sem `automated`**, confira o status, faça o sync
   (`kubectl patch application <n> -n argocd --type merge -p
   '{"operation":{"sync":{"revision":"<rev>"}}}'`) e verifique pods, certificados
   e HTTP durante o sync.
5. Ligue `automated` (prune + selfHeal) no arquivo do repo e aplique-o.
6. Se era Helm: apague só os Secrets de registro do release
   (`kubectl delete secret -n <ns> -l owner=helm,name=<release>`), **nunca**
   `helm uninstall`.

## Adicionar um add-on ou app novo (fluxo normal)

1. Copie uma pasta existente como molde: `kubernetes/addons/<novo>/` (chart de terceiros:
   `application.yaml` + `values.yaml`) ou `kubernetes/apps/<novo>/` (conteúdo nosso).
   Pine a versão do chart.
2. Rode `python3 scripts/validate_kubernetes.py` e abra o PR.
3. Depois do merge, nada a aplicar: o `root-app` detecta a pasta nova e cria o
   Application sozinho.

## Por que parar aqui (Nível 2/3)

Cluster pessoal, 1 operador, Always Free (24 GB no total). ApplicationSet, Flux
self-managed, Crossplane/CAPI resolvem repetição entre múltiplos clusters/ambientes
— problema que este cluster não tem. Subir além daqui troca YAML a menos por partes
móveis e RAM a mais, sem retorno.
