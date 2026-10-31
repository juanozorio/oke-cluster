# Como expor um app na internet (DNS + Ingress + TLS)

Esta pasta só tem documentação e um modelo. Nada aqui é aplicado ao cluster.

Caminho do tráfego: `internet → NLB (129.213.129.75) → NodePort 30080/30443 → ingress-nginx → Service → pod`.
O TLS é emitido sozinho pelo cert-manager (Let's Encrypt) pelo `ClusterIssuer`
`letsencrypt-prod`, que está em [`addons/cluster-issuers/`](../addons/cluster-issuers/).
Custo zero: tudo dentro do free tier.

## Passo a passo para um app novo

1. **DNS (no registro.br):** crie um registro **A** para o host, apontando para o NLB.

   | Nome | Tipo | Valor |
   |---|---|---|
   | `meuapp` | A | `129.213.129.75` |

   **Não existe wildcard (`*`)**: cada hostname precisa do seu registro. Sem ele o
   desafio HTTP-01 falha e consome o limite de falhas do Let's Encrypt (5 por hora
   por hostname). Confira antes de seguir: `getent hosts meuapp.ozorio.dev.br`.

2. **Ingress:** copie [`ingress-template.yml`](ingress-template.yml) para a pasta do
   app (`kubernetes/apps/<app>/manifests/ingress.yaml` ou o template do chart), troque `MEUAPP`,
   `NAMESPACE`, `NOME-DO-SERVICE` e `PORTA`, e descomente.

3. **Publique pelo Git:** merge na `master`. O ArgoCD aplica e o cert-manager emite o
   certificado (leva cerca de 1 minuto).

## Verificar

```sh
kubectl get ingress -A          # host e endereço
kubectl get certificate -A      # READY deve ser True
```

## Se o certificado não sai

```sh
kubectl describe certificate <nome> -n <namespace>
kubectl get challenges -A       # desafio HTTP-01 pendente?
```

Causa mais comum: o registro DNS ainda não existe ou ainda não propagou.
