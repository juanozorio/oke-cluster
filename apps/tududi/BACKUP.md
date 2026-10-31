# Backup do tududi com Litestream

Backup **contínuo** do SQLite (`/app/db/production.sqlite3`) para o OCI Object
Storage (bucket `tududi-backups`), via streaming do WAL. Perda máxima em desastre:
**segundos**, não 24 horas.

## Arquitetura

O Litestream roda como **sidecar** no pod do tududi (`deployment.yaml`), lendo o
MESMO volume do banco. Não há CronJob, nem `kubectl exec`, nem RBAC extra.

```
pod tududi
 ├── container tududi      -> escreve em /app/db/production.sqlite3
 └── container litestream  -> lê o WAL e replica p/ s3://tududi-backups/litestream/tududi
```

## Setup (uma vez)

1. Gere uma **Customer Secret Key** na OCI (par Access/Secret estilo S3):
   ```sh
   oci iam customer-secret-key create --user-id <SEU_USER_OCID> \
     --display-name tududi-litestream --profile DEFAULT
   ```
   O `id` retornado é o Access Key; o Secret Key aparece SÓ na criação — copie.

2. Crie o Secret no cluster (fora do Git):
   ```sh
   kubectl create secret generic tududi-litestream-s3 -n tududi \
     --from-literal=LITESTREAM_ACCESS_KEY_ID='<access-key>' \
     --from-literal=LITESTREAM_SECRET_ACCESS_KEY='<secret-key>'
   ```

3. Aplique (ou deixe o ArgoCD sincronizar):
   ```sh
   kubectl apply -k apps/tududi
   ```

4. Confirme que o sidecar está replicando:
   ```sh
   kubectl logs -n tududi deploy/tududi -c litestream -f
   # procure "replicating" / "wal segment written"
   oci os object list --namespace idfrvl6pz5cq --bucket-name tududi-backups \
     --prefix litestream/tududi --profile DEFAULT
   ```

## Restore (quando precisar recuperar)

O restore tem que acontecer com o tududi **parado** (ninguém pode estar escrevendo
no banco). Fluxo:

1. Escale o tududi para 0 (o sidecar cai junto):
   ```sh
   kubectl scale deploy/tududi -n tududi --replicas=0
   ```
2. Rode um Job/pod temporário com a imagem do litestream, montando o PVC, e restaure:
   ```sh
   litestream restore -config /etc/litestream/litestream.yml /app/db/production.sqlite3
   ```
   (ou restaure para um ponto no tempo com `-timestamp`)
3. Suba o tududi de volta:
   ```sh
   kubectl scale deploy/tududi -n tududi --replicas=1
   ```

> Teste o restore pelo menos uma vez num banco de teste. Backup não testado não é
> backup. Com Litestream o restore é um comando, mas confirme que o Access/Secret
> Key tem permissão de LEITURA no bucket, além de escrita.

## Retenção

Definida no `litestream-config.yaml`: snapshot a cada 24h, histórico de 30 dias
(`retention: 720h`). O bucket tem versioning ligado como rede de segurança extra.
