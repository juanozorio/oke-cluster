# Monitoramento (kube-prometheus-stack enxuto, sem persistência)

Definido em [`infra/argocd-apps/kube-prometheus-stack.yaml`](../../infra/argocd-apps/kube-prometheus-stack.yaml).
Prometheus + Grafana + kube-state-metrics + node-exporter. **Sem** Alertmanager,
**sem** volume persistente e **sem** Ingress público.

## Acessar o Grafana (port-forward)

```sh
# senha do admin (fica só no cluster, no Secret grafana-admin)
kubectl get secret grafana-admin -n monitoring -o jsonpath='{.data.admin-password}' | base64 -d; echo

kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
# abra http://localhost:3000  (usuário: admin)
```

Dashboards úteis já vêm provisionados: *Kubernetes / Compute Resources / Cluster*,
*... / Namespace (Pods)*, *Node Exporter / Nodes*.

## Acessar o Prometheus

```sh
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
# http://localhost:9090  ->  Status > Targets mostra o que está sendo coletado
```

## O que NÃO existe (de propósito)

- **Histórico duradouro:** Prometheus usa `emptyDir` com `retention: 3d` e
  `retentionSize: 2GB`. Se o pod for recriado (nó trocado, update), as métricas
  somem e a coleta recomeça do zero. Um PVC custaria 50 GB de block volume (mínimo
  da OCI), e o free tier (200 GB) já está excedido.
- **Alertas:** sem Alertmanager não há notificação. As regras (`PrometheusRule`)
  existem e aparecem na UI do Prometheus em *Alerts*, mas ninguém é avisado.
- **Control plane:** etcd, scheduler e controller-manager são gerenciados pela
  Oracle (OKE) e não são acessíveis para scrape.
- **Metrics API:** quem serve `kubectl top`/HPA continua sendo o metrics-server.

## Expor o Grafana publicamente (se um dia quiser)

Exige criar o registro DNS `grafana.ozorio.dev.br` (não há wildcard hoje) e
adicionar em `valuesObject.grafana`: `ingress.enabled: true`, `ingressClassName:
nginx`, `hosts`, `tls` e a annotation `cert-manager.io/cluster-issuer:
letsencrypt-prod`. O Grafana não tem proteção contra força bruta de senha por
padrão: use a senha longa gerada e considere restringir por IP.

## Secret (fora do Git)

`grafana-admin` (chaves `admin-user` e `admin-password`) é criado à mão:

```sh
kubectl create secret generic grafana-admin -n monitoring \
  --from-literal=admin-user=admin \
  --from-literal=admin-password="$(openssl rand -base64 24 | tr -d '/+=')"
```
