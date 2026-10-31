# infra/ — Add-ons do cluster via GitOps (ArgoCD)

Aqui ficam os add-ons de infraestrutura (ingress-nginx, cert-manager, ...) versionados
e gerenciados pelo **ArgoCD** que já roda no cluster. A fonte da verdade do "o que
está instalado" passa a ser este repositório, não o estado solto no cluster.

## Estrutura

```
infra/argocd-apps/
  cert-manager.yaml    # Application do cert-manager  (sync-wave -1, sobe primeiro)
  ingress-nginx.yaml   # Application do ingress-nginx (sync-wave 0)
  escalafacil.yaml     # Application do escalafacil (chart em charts/escala-servir)
  baofeng-airsoft.yaml # Application do baofeng (chart no repo baofeng-airsoft-docs)
  root-app.yaml        # App-of-Apps (Nível 3) — OPCIONAL, para bootstrap 1-comando
charts/escala-servir/  # chart Helm do escalafacil; produção em values-prod.yaml
```

## O que vai (e o que NÃO vai) para o Git

O ArgoCD guarda cada `Application` como um objeto dentro do cluster. **Criar ou
editar um app pela interface do ArgoCD não grava nada no Git.** Se o cluster for
recriado, tudo que só existe na UI some (foi o caso do `baofeng-airsoft` até ser
exportado para cá). Regras:

- Crie/edite `Application` como YAML nesta pasta e dê push. A UI serve para
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

## Como ADOTAR o que já está instalado (uma vez, com cuidado)

Hoje ingress-nginx foi instalado via Helm e cert-manager via manifesto estático.
Adotar significa o ArgoCD passar a gerenciá-los **sem recriar** nada. Faça assim:

1. Aplique os Applications (ainda em sync MANUAL — eles não têm `automated`):
   ```sh
   kubectl apply -f infra/argocd-apps/cert-manager.yaml
   kubectl apply -f infra/argocd-apps/ingress-nginx.yaml
   ```
2. No ArgoCD, abra cada app e clique em **App Diff / Diff**. Confirme que o diff é
   só **ownership/labels** — NUNCA recriação de CRD, Service NodePort ou Deployment.
   - Se o diff quiser recriar o Service do ingress → PARE (mudaria o NodePort que o
     NLB usa). Ajuste os values para bater com o atual antes de sincronizar.
   - Se quiser recriar CRDs do cert-manager → PARE (apagaria seus Certificates).
3. Com o diff seguro, clique **Sync**. O `ServerSideApply=true` adota os recursos.
4. Só DEPOIS de confirmar que ficou estável, ligue o modo automático: descomente o
   bloco `automated: { prune: true, selfHeal: true }` em cada arquivo e dê push.

## Adicionar um add-on novo (fluxo normal)

1. Crie `infra/argocd-apps/<novo>.yaml` (copie um existente como molde, pine a versão).
2. `git push`.
3. `kubectl apply -f infra/argocd-apps/<novo>.yaml` — ou, se já usar o App-of-Apps,
   nada: o `root-app` detecta o arquivo novo e cria o Application sozinho.

## Subir para Nível 3 (App-of-Apps) depois

Quando tiver vários add-ons e quiser bootstrap com um comando só:

```sh
kubectl apply -f infra/argocd-apps/root-app.yaml
```

A partir daí, add-on novo = só criar o YAML na pasta + push. O `root-app` reconcilia
o resto. A estrutura desta pasta **já está pronta** para isso — nada a refatorar.

## Por que parar aqui (Nível 2/3)

Cluster pessoal, 1 operador, Always Free (24 GB no total). ApplicationSet, Flux
self-managed, Crossplane/CAPI resolvem repetição entre múltiplos clusters/ambientes
— problema que este cluster não tem. Subir além daqui troca YAML a menos por partes
móveis e RAM a mais, sem retorno.
