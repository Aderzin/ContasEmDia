import os
from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.getenv("SECRET_KEY", "chave_secreta_fluxo_2026")

# CONEXÃO BANCO
URL_RESERVA = "mongodb+srv://adersonsoliveira55_db_user:MqSM10DQ5YNhyOpB@contasemdia.9iqz23o.mongodb.net/?appName=ContasEmDia"
MONGO_URI = os.getenv("MONGO_URI", URL_RESERVA)
client = MongoClient(MONGO_URI)
db = client.get_database('conta_em_dia_db')
movimentacoes_col = db.contas
usuarios_col = db.usuarios  # Nova coleção para usuários


@app.before_request
def verificar_acesso():
    rotas_livres = ['login', 'registrar', 'static']
    if 'user_id' not in session and request.endpoint not in rotas_livres:
        return redirect(url_for('login'))


@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        email = request.form.get('email').lower()
        senha = request.form.get('senha')

        if usuarios_col.find_one({"email": email}):
            return render_template('registrar.html', erro="Este e-mail já está cadastrado!")

        # Criar usuário com senha criptografada
        novo_usuario = {
            "email": email,
            "senha": generate_password_hash(senha)
        }
        usuarios_col.insert_one(novo_usuario)
        return redirect(url_for('login'))
    return render_template('registrar.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').lower()
        senha = request.form.get('senha')
        user = usuarios_col.find_one({"email": email})

        if user and check_password_hash(user['senha'], senha):
            session['user_id'] = str(user['_id'])
            session['email'] = user['email']
            return redirect(url_for('index'))

        return render_template('login.html', erro="E-mail ou senha incorretos!")
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

        # Agora as contas são globais para a família, mas você poderia filtrar por user_id se quisesse
        query = {"vencimento": {"$gte": inicio_mes, "$lt": fim_mes}}
        movimentacoes = list(movimentacoes_col.find(query).sort("vencimento", 1))

        total_entradas = sum(item.get('valor', 0) for item in movimentacoes if item.get('tipo') == 'entrada')
        total_saidas = sum(item.get('valor', 0) for item in movimentacoes if item.get('tipo') == 'saida')

        meses_nome = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro",
                      "Outubro", "Novembro", "Dezembro"]

        return render_template('index.html', movimentacoes=movimentacoes, total_entradas=total_entradas,
                               total_saidas=total_saidas, saldo=total_entradas - total_saidas,
                               mes_atual=mes_sel, ano_atual=ano_sel, meses_nome=meses_nome,
                               usuario=session.get('email'))
    except Exception as e:
        return f"Erro: {str(e)}"

# As rotas /add, /pagar e /deletar continuam as mesmas da versão anterior