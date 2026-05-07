import os
from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.getenv("SECRET_KEY", "fluxo_caixa_individual_2026")

# CONEXÃO BANCO DE DADOS
URL_RESERVA = "mongodb+srv://adersonsoliveira55_db_user:MqSM10DQ5YNhyOpB@contasemdia.9iqz23o.mongodb.net/?appName=ContasEmDia"
MONGO_URI = os.getenv("MONGO_URI", URL_RESERVA)
client = MongoClient(MONGO_URI)
db = client.get_database('conta_em_dia_db')
movimentacoes_col = db.contas
usuarios_col = db.usuarios


@app.before_request
def verificar_acesso():
    rotas_livres = ['login', 'registrar', 'static']
    if 'user_id' not in session and request.endpoint not in rotas_livres:
        return redirect(url_for('login'))


@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        email = request.form.get('email').lower().strip()
        senha = request.form.get('senha')
        if usuarios_col.find_one({"email": email}):
            return render_template('registrar.html', erro="E-mail já cadastrado!")
        usuarios_col.insert_one({"email": email, "senha": generate_password_hash(senha)})
        return redirect(url_for('login'))
    return render_template('registrar.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').lower().strip()
        senha = request.form.get('senha')
        user = usuarios_col.find_one({"email": email})
        if user and check_password_hash(user['senha'], senha):
            session['user_id'] = str(user['_id'])
            session['email'] = user['email']
            return redirect(url_for('index'))
        return render_template('login.html', erro="Usuário ou senha inválidos!")
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
def index():
    try:
        hoje = datetime.now()
        mes_sel = int(request.args.get('mes', hoje.month))
        ano_sel = int(request.args.get('ano', hoje.year))

        inicio_mes = datetime(ano_sel, mes_sel, 1)
        fim_mes = datetime(ano_sel + 1, 1, 1) if mes_sel == 12 else datetime(ano_sel, mes_sel + 1, 1)

        # Filtra estritamente por mês/ano E pelo ID do usuário logado
        query = {
            "vencimento": {"$gte": inicio_mes, "$lt": fim_mes},
            "user_id": session['user_id']
        }

        movimentacoes = list(movimentacoes_col.find(query).sort("vencimento", 1))

        total_entradas = 0
        total_saidas = 0
        for item in movimentacoes:
            v = item.get('valor', 0)
            if not isinstance(v, (int, float)): v = 0

            if item.get('tipo') == 'entrada':
                total_entradas += v
            else:
                total_saidas += v

        saldo = total_entradas - total_saidas
        meses_nome = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                      "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

        return render_template('index.html',
                               movimentacoes=movimentacoes,
                               total_entradas=total_entradas,
                               total_saidas=total_saidas,
                               saldo=saldo,
                               mes_atual=mes_sel,
                               ano_atual=ano_sel,
                               meses_nome=meses_nome,
                               usuario_logado=session.get('email'))
    except Exception as e:
        return f"Erro interno do sistema: {str(e)}"


@app.route('/add', methods=['POST'])
def add():
    try:
        valor_raw = request.form.get('valor', '0').replace(',', '.')
        vencimento_str = request.form.get('vencimento')

        nova_mov = {
            "descricao": request.form.get('descricao'),
            "valor": float(valor_raw) if valor_raw else 0.0,
            "vencimento": datetime.strptime(vencimento_str, '%Y-%m-%d'),
            "tipo": request.form.get('tipo'),
            "pago": False,
            "user_id": session['user_id']  # Vincula ao dono do painel
        }
        movimentacoes_col.insert_one(nova_mov)
        data_obj = datetime.strptime(vencimento_str, '%Y-%m-%d')
        return redirect(url_for('index', mes=data_obj.month, ano=data_obj.year))
    except:
        return redirect(url_for('index'))


@app.route('/pagar/<id>')
def pagar(id):
    movimentacoes_col.update_one({"_id": ObjectId(id), "user_id": session['user_id']}, {"$set": {"pago": True}})
    return redirect(request.referrer or url_for('index'))


@app.route('/deletar/<id>')
def deletar(id):
    movimentacoes_col.delete_one({"_id": ObjectId(id), "user_id": session['user_id']})
    return redirect(request.referrer or url_for('index'))