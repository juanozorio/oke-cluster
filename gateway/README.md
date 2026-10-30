# Ingress — ozorio.dev.br

Usa o **nginx-ingress** já existente no cluster (NodePort 30080/30443 → NLB OCI).
Sem custos adicionais — tudo free tier.

## DNS — adicione no registro.br

| Nome | Tipo | Valor |
|---|---|---|
| `@` | A | `129.213.129.75` |
| `*` | A | `129.213.129.75` |

## Aplicar rotas

```bash
kubectl apply -f gateway/httproutes.yml
```

O cert-manager emite os certificados TLS automaticamente via Let's Encrypt.

## Adicionar um novo serviço

1. Edite `gateway/httproutes.yml`
2. Copie o bloco do template comentado no final do arquivo
3. Substitua `MEUAPP`, `NAMESPACE`, `NOME-DO-SERVICE` e `PORTA`
4. Aplique: `kubectl apply -f gateway/httproutes.yml`

## Verificar status

```bash
# Listar ingresses e ver se TLS está emitido
kubectl get ingress -A

# Status dos certificados
kubectl get certificate -A
```
