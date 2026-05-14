# Configuração e Envio para o GitHub

## Pré-requisito: Personal Access Token

O GitHub não aceita senha comum. Antes de começar, gere um token:

1. Acesse: **GitHub > Settings > Developer settings > Personal access tokens > Tokens (classic)**
2. Clique em **Generate new token**
3. Marque a permissão **repo**
4. Copie o token gerado — você vai usá-lo no lugar da senha

---

## Passo 1 — Inicializar o repositório git

Abra o terminal na pasta do projeto e execute:

```powershell
cd "c:\Users\rpeli\Desktop\Desafio_t4humans\banco-agil"
git init
```

---

## Passo 2 — Configurar seu nome e e-mail (apenas na primeira vez)

```powershell
git config --global user.name "Rodrigo Simoes"
git config --global user.email "rodrigo.costa-ext@dex.co"
```

---

## Passo 3 — Verificar o que será enviado

```powershell
git status
```

Confirme que `.env` e `venv/` **não aparecem** na lista — eles estão no `.gitignore` e não devem ser enviados.

---

## Passo 4 — Adicionar os arquivos ao commit

```powershell
git add .
```

---

## Passo 5 — Criar o primeiro commit

```powershell
git commit -m "Initial commit: Banco Ágil — sistema multi-agente de atendimento bancário"
```

---

## Passo 6 — Conectar ao repositório remoto

```powershell
git remote add origin https://github.com/rodrigosimoescosta77/desafio-t4humans.git
git branch -M main
```

---

## Passo 7 — Enviar para o GitHub

```powershell
git push -u origin main
```

Quando solicitado:
- **Username:** seu usuário do GitHub (`rodrigosimoescosta77`)
- **Password:** cole o **Personal Access Token** gerado no pré-requisito

---

## Próximos commits (fluxo do dia a dia)

Após alterar arquivos:

```powershell
git add .
git commit -m "Descrição do que foi alterado"
git push
```

---

## Verificar o estado do repositório a qualquer momento

```powershell
git status        # arquivos modificados/novos
git log --oneline # histórico de commits
```
