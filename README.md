# 🔐 IBM Cloud IAM Dashboard

Este é um painel de gerenciamento de Service IDs e Service ID Groups da IBM Cloud, desenvolvido com Flask e integração direta com a IBM IAM Identity API.  
Permite autenticação por API Key, criação, edição, exclusão e visualização de recursos IAM de forma segura e intuitiva.

---

## 🚀 Funcionalidades

- Login via API Key e Account ID
- Listagem com paginação e filtros (nome, estado, datas)
- Criação e exclusão de Service IDs
- Edição de descrição e bloqueio/desbloqueio de IDs
- Gerenciamento de grupos de Service ID (Service ID Groups)
- Exportação para CSV
- Dark mode com persistência (via localStorage)
- Interface com Bootstrap 5
- Lembrar Account ID no navegador (opcional)
- Controle de sessão via Flask-Login

---

## 🛠️ Tecnologias utilizadas

- Python 3.10+
- Flask
- Flask-Login
- Bootstrap 5
- IBM Cloud IAM API
- Requests
- Pandas

---

## 📁 Estrutura do projeto

pp/
├── init.py
├── models/
│ └── user.py
├── routes/
│ ├── auth.py
│ └── dashboard.py
├── templates/
│ ├── base.html
│ ├── login.html
│ ├── home.html
│ ├── service_ids/
│ │ └── list.html
│ └── service_id_groups/
│ └── list.html
run.py

---

## 🔧 Como rodar localmente

### 1. Clone o projeto
```bash
git clone https://github.com/oliverocr/iam_identity_services_dashboard.git
cd ibm-iam-dashboard

Crie um ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

Instale as dependências
pip install -r requirements.txt

Inicie o servidor
python run.py
Acesse em: http://127.0.0.1:5000

🔑 Autenticação
Você precisa de:
API Key da IBM Cloud
Account ID da sua conta IBM Cloud
Essas credenciais são inseridas na tela de login.

📦 Exportação CSV
Há um botão no topo da listagem de Service IDs para exportar os dados visíveis para .csv.
