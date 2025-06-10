from flask import Blueprint, render_template, session, redirect, url_for, request, flash, send_file, Response
from flask_login import login_required
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)
IBM_IAM_API_BASE = "https://iam.cloud.ibm.com/v2"  # Para Service IDs
IBM_IAM_IDM_API_BASE = "https://iam.cloud.ibm.com/identity/v1"  # Para Service ID Groups


@dashboard_bp.route('/')
@login_required
def home():
    return render_template('home.html')


# 🔐 SERVICE IDS
@dashboard_bp.route('/service-ids')
@login_required
def service_ids():
    token = session.get('access_token')
    account_id = session.get('account_id')

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }

    limit = int(request.args.get('limit', 25))
    offset = int(request.args.get('offset', 0))
    search = request.args.get('search', '').strip()
    state_filter = request.args.get('state', '').strip().lower()
    created_date = request.args.get('created', '')
    modified_date = request.args.get('modified', '')

    params = {
        'account_id': account_id,
        'limit': 1000,  # trazemos tudo e filtramos localmente
        'sort': 'name'
    }

    if search:
        params['name'] = search

    response = requests.get(f"{IBM_IAM_API_BASE}/serviceids", headers=headers, params=params)
    if response.status_code != 200:
        flash(f"Erro ao buscar Service IDs: {response.status_code}", "danger")
        return render_template('service_ids/list.html', service_ids=[], total=0, search=search, limit=limit, offset=offset)

    data = response.json()
    service_ids = data.get('serviceids', [])
    total = data.get('total_count', 0)

    # 🧠 Filtragem por estado
    if state_filter:
        service_ids = [sid for sid in service_ids if sid.get('state', '').lower() == state_filter]

    # 🧠 Filtros por datas
    def matches_date(sid, field, filter_date):
        if not filter_date:
            return True
        try:
            target = datetime.strptime(filter_date, '%Y-%m-%d').date()
            actual = datetime.strptime(sid.get(field, '')[:10], '%Y-%m-%d').date()
            return actual == target
        except Exception:
            return True

    if created_date:
        service_ids = [sid for sid in service_ids if matches_date(sid, 'created_at', created_date)]

    if modified_date:
        service_ids = [sid for sid in service_ids if matches_date(sid, 'modified_at', modified_date)]

    # Paginar após filtros
    total = len(service_ids)
    paginated = service_ids[offset:offset+limit]

    return render_template('service_ids/list.html', service_ids=paginated, total=total,
                           search=search, limit=limit, offset=offset)


@dashboard_bp.route('/create-service-id', methods=['POST'])
@login_required
def create_service_id():
    token = session.get('access_token')
    account_id = session.get('account_id')

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    payload = {
        "name": request.form['name'],
        "description": request.form['description'],
        "account_id": account_id
    }

    response = requests.post(f"{IBM_IAM_API_BASE}/serviceids", headers=headers, json=payload)

    if response.status_code == 201:
        flash("✅ Service ID criado com sucesso!", "success")
    else:
        flash(f"Erro ao criar Service ID: {response.status_code} - {response.text}", "danger")

    return redirect(url_for('dashboard.service_ids'))


@dashboard_bp.route('/edit-service-id/<sid_id>', methods=['POST'])
@login_required
def edit_service_id(sid_id):
    token = session.get('access_token')

    get_headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }

    get_resp = requests.get(f"{IBM_IAM_API_BASE}/serviceids/{sid_id}", headers=get_headers)

    if get_resp.status_code != 200:
        flash(f"Erro ao buscar ETag: {get_resp.status_code}", "danger")
        return redirect(url_for('dashboard.service_ids'))

    etag = get_resp.headers.get('ETag')
    description = request.form.get('description', '').strip()
    locked_checkbox = request.form.get('locked') == 'on'
    current_state = get_resp.json().get('state')

    if description:
        patch_headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'If-Match': etag
        }
        patch_payload = { "description": description }
        patch_resp = requests.patch(f"{IBM_IAM_API_BASE}/serviceids/{sid_id}", headers=patch_headers, json=patch_payload)
        if patch_resp.status_code != 200:
            flash(f"Erro ao atualizar descrição: {patch_resp.status_code}", "danger")

    lock_headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    if current_state == 'locked' and not locked_checkbox:
        requests.delete(f"{IBM_IAM_API_BASE}/serviceids/{sid_id}/lock", headers=lock_headers)
    elif current_state != 'locked' and locked_checkbox:
        requests.post(f"{IBM_IAM_API_BASE}/serviceids/{sid_id}/lock", headers=lock_headers)

    flash("✏️ Atualizado com sucesso!", "success")
    return redirect(url_for('dashboard.service_ids'))


@dashboard_bp.route('/delete-service-id/<sid_id>', methods=['POST'])
@login_required
def delete_service_id(sid_id):
    token = session.get('access_token')
    headers = { 'Authorization': f'Bearer {token}' }
    r = requests.delete(f"{IBM_IAM_API_BASE}/serviceids/{sid_id}", headers=headers)
    if r.status_code == 204:
        flash("🗑️ Excluído com sucesso!", "success")
    else:
        flash(f"Erro ao excluir: {r.status_code}", "danger")
    return redirect(url_for('dashboard.service_ids'))


@dashboard_bp.route('/export-csv')
@login_required
def export_csv():
    token = session.get('access_token')
    account_id = session.get('account_id')
    headers = {'Authorization': f'Bearer {token}'}
    params = {'account_id': account_id, 'limit': 1000}
    r = requests.get(f"{IBM_IAM_API_BASE}/serviceids", headers=headers, params=params)

    if r.status_code != 200:
        flash(f"Erro ao exportar: {r.status_code}", "danger")
        return redirect(url_for('dashboard.service_ids'))

    data = r.json().get('serviceids', [])
    df = pd.DataFrame(data)
    csv = df.to_csv(index=False)
    return send_file(BytesIO(csv.encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='service_ids.csv')


# 👥 SERVICE ID GROUPS
@dashboard_bp.route('/service-id-groups')
@login_required
def service_id_groups():
    token = session.get('access_token')
    account_id = session.get('account_id')

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }

    # 🔎 Filtros
    search = request.args.get('search', '').strip().lower()
    created_filter = request.args.get('created', '')

    # 📄 Export CSV
    if request.args.get('format') == 'csv':
        return export_groups_csv(token, account_id, headers, search, created_filter)

    # 📦 Paginação + Ordenação
    limit = int(request.args.get('limit', 25))
    offset = int(request.args.get('offset', 0))
    order_by = request.args.get('order_by', 'name')
    order_dir = request.args.get('order_dir', 'asc')

    # Buscar grupos
    response = requests.get(f"{IBM_IAM_API_BASE}/serviceidgroups", headers=headers, params={
        'account_id': account_id,
        'sort': 'name',
        'include_history': False
    })

    if response.status_code == 404:
        all_groups = []  # nenhum grupo existente ainda
    elif response.status_code != 200:
        flash(f"Erro ao buscar grupos: {response.status_code}", "danger")
        return render_template(
            'service_id_groups.html',
            groups=[],
            total=0,
            offset=0,
            limit=25,
            order_by='name',
            order_dir='asc',
            request=request,
            all_service_ids=[]
       )
    else:
        all_groups = response.json().get('service_id_groups', [])


    # Filtro por nome/descrição
    if search:
        all_groups = [g for g in all_groups if search in g['name'].lower() or search in (g.get('description') or '').lower()]

    # Filtro por data
    if created_filter:
        try:
            created_target = datetime.strptime(created_filter, '%Y-%m-%d').date()
            all_groups = [g for g in all_groups if datetime.strptime(g['created_at'][:10], '%Y-%m-%d').date() == created_target]
        except Exception:
            pass

    # Ordenação
    reverse = (order_dir == 'desc')
    all_groups.sort(key=lambda g: g.get(order_by, '').lower() if isinstance(g.get(order_by), str) else g.get(order_by), reverse=reverse)

    # Paginação
    total = len(all_groups)
    paginated_groups = all_groups[offset:offset + limit]

    # Buscar todos os Service IDs
    sid_resp = requests.get(f"{IBM_IAM_API_BASE}/serviceids", headers=headers, params={
        'account_id': account_id, 'limit': 1000
    })
    service_ids = sid_resp.json().get('serviceids', []) if sid_resp.status_code == 200 else []

    return render_template(
        'service_id_groups.html',
        groups=paginated_groups,
        total=total,
        offset=offset,
        limit=limit,
        order_by=order_by,
        order_dir=order_dir,
        request=request,
        all_service_ids=service_ids
    )


def export_groups_csv(token, account_id, headers, search, created_filter):
    r = requests.get(f"{IBM_IAM_API_BASE}/serviceidgroups", headers=headers, params={
        'account_id': account_id,
        'sort': 'name',
        'include_history': False
    })

    if r.status_code != 200:
        flash("Erro ao exportar grupos.", "danger")
        return redirect(url_for('dashboard.service_id_groups'))

    groups = r.json().get('service_id_groups', [])

    # Filtros
    if search:
        groups = [g for g in groups if search in g['name'].lower() or search in (g.get('description') or '').lower()]

    if created_filter:
        try:
            created_target = datetime.strptime(created_filter, '%Y-%m-%d').date()
            groups = [g for g in groups if datetime.strptime(g['created_at'][:10], '%Y-%m-%d').date() == created_target]
        except Exception:
            pass

    # CSV
    rows = []
    for g in groups:
        rows.append({
            'name': g['name'],
            'description': g.get('description', ''),
            'serviceids': ', '.join(g.get('serviceids', [])),
            'created_at': g['created_at']
        })

    df = pd.DataFrame(rows)
    csv_data = df.to_csv(index=False)
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment; filename=service_id_groups.csv"}
    )

@dashboard_bp.route('/service-id-groups/create', methods=['POST'])
@login_required
def create_service_id_group():
    import json  # garantir disponível
    token = session.get('access_token')
    account_id = session.get('account_id')

    # 🔒 Verificação de sessão
    if not token or not account_id:
        flash("❌ Sessão inválida. Faça login novamente.", "danger")
        return redirect(url_for('auth.logout'))

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    # 🎯 Dados do formulário
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    serviceids = request.form.getlist('serviceids')  # pode ser lista vazia

    # 🛡️ Validações
    if not name:
        flash("⚠️ O nome do grupo é obrigatório.", "warning")
        return redirect(url_for('dashboard.service_id_groups'))

    # 🧪 Construção segura do payload
    payload = {
        "account_id": account_id,
        "name": name
    }

    if description:
        payload["description"] = description

    if serviceids:
        payload["serviceids"] = serviceids

    # 📡 Debug opcional
    print("🔧 [DEBUG] Criando Service ID Group")
    print("🔐 Token (parcial):", token[:20], "...")
    print("🧾 Payload:", json.dumps(payload, indent=2))

    # 🚀 Envio da requisição
    url = "https://iam.cloud.ibm.com/v1/serviceidgroups"
    response = requests.post(url, headers=headers, json=payload)

    # 📣 Feedback
    if response.status_code == 201:
        flash("✅ Grupo criado com sucesso!", "success")
    elif response.status_code == 400:
        flash("❌ Erro de validação: verifique os dados informados.", "danger")
    elif response.status_code == 403:
        flash("⛔ Permissão negada. Verifique a API Key utilizada.", "danger")
    else:
        flash(f"Erro ao criar grupo: {response.status_code} - {response.text}", "danger")

    return redirect(url_for('dashboard.service_id_groups'))

@dashboard_bp.route('/service-id-groups/edit/<group_id>', methods=['POST'])
@login_required
def edit_service_id_group(group_id):
    import json

    token = session.get('access_token')
    account_id = session.get('account_id')

    if not token or not account_id:
        flash("❌ Sessão inválida. Faça login novamente.", "danger")
        return redirect(url_for('auth.logout'))

    # 🔎 Extração com fallback
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    serviceids = request.form.getlist('serviceids')

    if not name:
        flash("⚠️ O nome do grupo é obrigatório para editar.", "warning")
        return redirect(url_for('dashboard.service_id_groups'))

    payload = {
        "name": name,
        "description": description or None,
        "serviceids": serviceids if serviceids else None
    }

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    # 🧪 LOG seguro
    print(f"🛠️ Editando grupo {group_id} com dados:")
    print(json.dumps(payload, indent=2))

    url = f"{IBM_IAM_API_BASE}/serviceidgroups/{group_id}"
    response = requests.patch(url, headers=headers, json=payload)

    if response.status_code == 200:
        flash("✅ Grupo atualizado com sucesso!", "success")
    elif response.status_code == 400:
        flash("⚠️ Erro de validação. Verifique os campos.", "danger")
    elif response.status_code == 404:
        flash("❌ Grupo não encontrado. Verifique se ele ainda existe.", "danger")
    elif response.status_code == 403:
        flash("🚫 Sem permissão para editar este grupo.", "danger")
    else:
        flash(f"Erro inesperado: {response.status_code} - {response.text}", "danger")

    return redirect(url_for('dashboard.service_id_groups'))


@dashboard_bp.route('/service-id-groups/delete/<group_id>', methods=['POST'])
@login_required
def delete_service_id_group(group_id):
    token = session.get('access_token')

    if not token:
        flash("❌ Sessão inválida. Faça login novamente.", "danger")
        return redirect(url_for('auth.logout'))

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }

    print(f"🚨 Tentativa de exclusão do grupo ID: {group_id}")

    response = requests.delete(f"{IBM_IAM_API_BASE}/serviceidgroups/{group_id}", headers=headers)

    if response.status_code == 204:
        flash("🗑️ Grupo excluído com sucesso!", "success")
    elif response.status_code == 404:
        flash("❌ Grupo não encontrado. Já foi excluído?", "danger")
    elif response.status_code == 403:
        flash("🚫 Sem permissão para excluir esse grupo.", "danger")
    else:
        flash(f"Erro ao excluir: {response.status_code} - {response.text}", "danger")

    return redirect(url_for('dashboard.service_id_groups'))


