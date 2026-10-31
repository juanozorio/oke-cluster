# Monitoramento (kube-prometheus-stack enxuto, sem persistência)

Definido em [`application.yaml`](application.yaml) (chart) e [`values.yaml`](values.yaml) (configuração).
Prometheus + Grafana + kube-state-metrics + node-exporter. **Sem** Alertmanager,
**sem** volume persistente e **sem** Ingress público.

## Acessar o Grafana

**Pela internet:** https://grafana.ozorio.dev.br (usuário `admin`).

Pré-requisito (uma vez, no registro.br): registro DNS **A** `grafana` ->
`129.213.129.75` (o IP do NLB). Não há wildcard no domínio; sem esse registro o
cert-manager não consegue emitir o certificado (o desafio HTTP-01 falha).

```sh
# senha do admin (fica só no cluster, no Secret grafana-admin)
kubectl get secret grafana-admin -n monitoring -o jsonpath='{.data.admin-password}' | base64 -d; echo
```

**Sem DNS / só local:** `kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80`
e abra http://localhost:3000.

Proteções: o Grafana bloqueia o login por 5 minutos após 5 tentativas erradas
(padrão `disable_brute_force_login_protection = false`), o cadastro público está
desligado (`allow_sign_up = false`), a senha é aleatória de 24 caracteres e o
nginx limita a 10 req/s por IP.

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

## Secret (fora do Git)

`grafana-admin` (chaves `admin-user` e `admin-password`) é criado à mão:

```sh
kubectl create secret generic grafana-admin -n monitoring \
  --from-literal=admin-user=admin \
  --from-literal=admin-password="$(openssl rand -base64 24 | tr -d '/+=')"
```
