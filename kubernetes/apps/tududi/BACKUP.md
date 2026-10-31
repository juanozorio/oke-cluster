# Backup do tududi com Litestream

O banco SQLite (`/app/db/production.sqlite3`) vive no **disco do nó** (`emptyDir`),
**sem volume persistente**, e é replicado de forma contínua para o OCI Object
Storage (bucket `tududi-backups`) pelo Litestream. A cada início do pod, um
initContainer restaura o banco a partir dessa réplica.

## Por que sem PVC

O menor block volume da OCI é 50 GB. Somado aos 4 boot volumes dos nós (4 x 47 GB)
dava 238 GB contra os **200 GB do free tier**, e o excesso custava ~R$ 0,36/dia.
O banco tem poucos MB e não há uploads, então o volume foi removido.

## Como funciona

```
pod tududi
 ├── initContainer restore-db  -> litestream restore (se houver réplica)
 ├── container tududi          -> escreve em /app/db/production.sqlite3 (emptyDir)
 └── container litestream      -> replica o WAL p/ s3://tududi-backups/litestream/tududi (~1 s)
```

Comportamento do `restore-db` (testado):

| Situação | Resultado |
|---|---|
| Existe réplica | restaura o banco mais recente, pod sobe |
| Não existe nenhum backup (primeira instalação) | não faz nada, pod sobe com banco novo |
| Erro de rede ou credencial | **falha**: o pod fica em `Init:Error` e tenta de novo (nunca sobe vazio) |

Perda máxima de dados se o nó morrer: ~1 segundo de escritas.

## Setup (uma vez)

1. Gere uma **Customer Secret Key** na OCI (par Access/Secret estilo S3):
   ```sh
   oci iam customer-secret-key create --user-id <SEU_USER_OCID> \
     --display-name tududi-litestream --profile DEFAULT
   ```
   O Secret Key aparece SÓ na criação.
2. Crie o Secret no cluster (fora do Git):
   ```sh
   kubectl create secret generic tududi-litestream-s3 -n tududi \
     --from-literal=LITESTREAM_ACCESS_KEY_ID='<access-key>' \
     --from-literal=LITESTREAM_SECRET_ACCESS_KEY='<secret-key>'
   ```
3. O ArgoCD aplica o restante (`kubernetes/apps/tududi/application.yaml`).

## Verificar que está replicando

```sh
kubectl logs -n tududi deploy/tududi -c litestream --tail=5
oci os object list --namespace idfrvl6pz5cq --bucket-name tududi-backups \
  --prefix litestream/tududi --profile DEFAULT
```

## Restaurar para um ponto no tempo / para fora do cluster

Para inspecionar ou recuperar um estado anterior sem mexer no pod:

```sh
# com as credenciais do Secret exportadas em LITESTREAM_ACCESS_KEY_ID/SECRET_ACCESS_KEY
litestream restore -config litestream.yml -o /tmp/tududi.sqlite3 \
  -timestamp 2026-10-31T10:00:00Z /app/db/production.sqlite3
```

(o `litestream.yml` é o conteúdo do ConfigMap `tududi-litestream`).

## Observações

- Cada restore abre uma **nova geração** no Litestream. É normal: as antigas
  continuam no bucket até a retenção (`retention: 720h`) expirar.
- Há também uma cópia manual de segurança em
  `manual/tududi-pre-migracao-20261030.sqlite3.gz` no mesmo bucket.
- Se o Object Storage estiver fora do ar quando um pod reiniciar, o tududi
  espera (Init:Error) em vez de subir com um banco vazio.
