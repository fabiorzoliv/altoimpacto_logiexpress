from datetime import date, timedelta
import os
from decimal import Decimal
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "logiexpress-dev-key")

# Render/PostgreSQL supplies DATABASE_URL. Locally we keep SQLite so students can
# run the project without installing a database server.
database_url = os.getenv("DATABASE_URL", "sqlite:///logiexpress.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    documento = db.Column(db.String(20), unique=True, nullable=False)
    cidade = db.Column(db.String(80), nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    pedidos = db.relationship("Pedido", backref="cliente", lazy=True)


class Motorista(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    cnh = db.Column(db.String(20), unique=True, nullable=False)
    telefone = db.Column(db.String(20))
    ativo = db.Column(db.Boolean, default=True)
    entregas = db.relationship("Entrega", backref="motorista", lazy=True)


class Veiculo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(10), unique=True, nullable=False)
    modelo = db.Column(db.String(80), nullable=False)
    tipo = db.Column(db.String(40), nullable=False)
    capacidade_kg = db.Column(db.Float, nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    entregas = db.relationship("Entrega", backref="veiculo", lazy=True)


class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), unique=True, nullable=False)
    descricao = db.Column(db.String(150), nullable=False)
    categoria = db.Column(db.String(80), nullable=False)
    estoque = db.Column(db.Integer, default=0)
    estoque_minimo = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True)
    itens = db.relationship("ItemPedido", backref="produto", lazy=True)


class CentroDistribuicao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cidade = db.Column(db.String(80), nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    capacidade = db.Column(db.Integer, nullable=False)
    ativo = db.Column(db.Boolean, default=True)


class Transportadora(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(150), nullable=False)
    cnpj = db.Column(db.String(20), unique=True, nullable=False)
    cidade = db.Column(db.String(80), nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    ativo = db.Column(db.Boolean, default=True)


class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(30), unique=True, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    data_pedido = db.Column(db.Date, nullable=False)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="ABERTO")
    itens = db.relationship("ItemPedido", backref="pedido", lazy=True, cascade="all, delete-orphan")
    entrega = db.relationship("Entrega", backref="pedido", uselist=False, cascade="all, delete-orphan")


class ItemPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    valor_unitario = db.Column(db.Numeric(12, 2), nullable=False)


class Rota(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    origem = db.Column(db.String(100), nullable=False)
    destino = db.Column(db.String(100), nullable=False)
    distancia_km = db.Column(db.Float, nullable=False)
    tempo_estimado_h = db.Column(db.Float, nullable=False)
    ativa = db.Column(db.Boolean, default=True)


class Entrega(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), nullable=False, unique=True)
    motorista_id = db.Column(db.Integer, db.ForeignKey("motorista.id"), nullable=False)
    veiculo_id = db.Column(db.Integer, db.ForeignKey("veiculo.id"), nullable=False)
    rota_id = db.Column(db.Integer, db.ForeignKey("rota.id"), nullable=True)
    data_prevista = db.Column(db.Date, nullable=False)
    data_entrega = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(30), nullable=False, default="EM TRANSITO")
    rota = db.relationship("Rota")


class Ocorrencia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entrega_id = db.Column(db.Integer, db.ForeignKey("entrega.id"), nullable=False)
    tipo = db.Column(db.String(80), nullable=False)
    descricao = db.Column(db.String(255), nullable=False)
    data = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), default="ABERTA")
    entrega = db.relationship("Entrega", backref=db.backref("ocorrencias", lazy=True))


MODEL_MAP = {
    "clientes": (Cliente, "Clientes"),
    "motoristas": (Motorista, "Motoristas"),
    "veiculos": (Veiculo, "Veículos"),
    "produtos": (Produto, "Produtos"),
    "centros": (CentroDistribuicao, "Centros de Distribuição"),
    "transportadoras": (Transportadora, "Transportadoras"),
    "pedidos": (Pedido, "Pedidos"),
    "rotas": (Rota, "Rotas"),
    "entregas": (Entrega, "Entregas"),
    "ocorrencias": (Ocorrencia, "Ocorrências"),
}


def seed_data():
    if Cliente.query.first():
        return
    clientes = [
        Cliente(nome="Mercado Central", documento="11.111.111/0001-01", cidade="São Paulo", uf="SP"),
        Cliente(nome="Comercial Horizonte", documento="22.222.222/0001-02", cidade="Campinas", uf="SP"),
        Cliente(nome="Rede Bom Preço", documento="33.333.333/0001-03", cidade="Santos", uf="SP"),
        Cliente(nome="Distribuidora Nova Era", documento="44.444.444/0001-04", cidade="Sorocaba", uf="SP"),
        Cliente(nome="Varejo Paulista", documento="55.555.555/0001-05", cidade="Guarulhos", uf="SP"),
    ]
    motoristas = [
        Motorista(nome="Carlos Almeida", cnh="SP1234567", telefone="11999990001"),
        Motorista(nome="João Martins", cnh="SP2345678", telefone="11999990002"),
        Motorista(nome="Mariana Souza", cnh="SP3456789", telefone="11999990003"),
        Motorista(nome="Ana Ribeiro", cnh="SP4567890", telefone="11999990004"),
    ]
    veiculos = [
        Veiculo(placa="ABC1A23", modelo="Sprinter 417", tipo="VAN", capacidade_kg=1500),
        Veiculo(placa="DEF2B34", modelo="Delivery 11.180", tipo="CAMINHÃO", capacidade_kg=5000),
        Veiculo(placa="GHI3C45", modelo="Master L2H2", tipo="VAN", capacidade_kg=1800),
        Veiculo(placa="JKL4D56", modelo="Fiorino", tipo="UTILITÁRIO", capacidade_kg=650),
    ]
    produtos = [
        Produto(codigo="P001", descricao="Caixa de bebidas", categoria="Bebidas", estoque=180, estoque_minimo=60),
        Produto(codigo="P002", descricao="Caixa de alimentos", categoria="Alimentos", estoque=95, estoque_minimo=40),
        Produto(codigo="P003", descricao="Material de limpeza", categoria="Limpeza", estoque=35, estoque_minimo=50),
        Produto(codigo="P004", descricao="Embalagens", categoria="Embalagens", estoque=240, estoque_minimo=80),
        Produto(codigo="P005", descricao="Produtos refrigerados", categoria="Refrigerados", estoque=70, estoque_minimo=30),
    ]
    centros = [
        CentroDistribuicao(nome="CD São Paulo", cidade="São Paulo", uf="SP", capacidade=10000),
        CentroDistribuicao(nome="CD Campinas", cidade="Campinas", uf="SP", capacidade=6000),
        CentroDistribuicao(nome="CD Santos", cidade="Santos", uf="SP", capacidade=5000),
    ]
    transportadoras = [
        Transportadora(razao_social="TransLog Paulista Ltda.", cnpj="12.345.678/0001-10", cidade="São Paulo", uf="SP"),
        Transportadora(razao_social="Rápido Brasil Transportes", cnpj="23.456.789/0001-20", cidade="Campinas", uf="SP"),
    ]
    rotas = [
        Rota(origem="São Paulo", destino="Campinas", distancia_km=98, tempo_estimado_h=1.8),
        Rota(origem="São Paulo", destino="Santos", distancia_km=75, tempo_estimado_h=1.6),
        Rota(origem="São Paulo", destino="Sorocaba", distancia_km=105, tempo_estimado_h=2.0),
        Rota(origem="Campinas", destino="Guarulhos", distancia_km=120, tempo_estimado_h=2.2),
    ]
    db.session.add_all(clientes + motoristas + veiculos + produtos + centros + transportadoras + rotas)
    db.session.flush()
    hoje = date.today()
    for i in range(1, 21):
        pedido = Pedido(numero=f"PED-{1000+i}", cliente_id=clientes[(i-1)%len(clientes)].id,
                        data_pedido=hoje-timedelta(days=i%12), valor=Decimal(str(350+i*47.5)),
                        status=["ABERTO","EM SEPARAÇÃO","EM TRANSPORTE","ENTREGUE"][i%4])
        db.session.add(pedido)
        db.session.flush()
        produto = produtos[(i-1)%len(produtos)]
        db.session.add(ItemPedido(pedido_id=pedido.id, produto_id=produto.id, quantidade=(i%5)+1,
                                  valor_unitario=Decimal(str(45+i))))
        entrega = Entrega(pedido_id=pedido.id, motorista_id=motoristas[(i-1)%len(motoristas)].id,
                          veiculo_id=veiculos[(i-1)%len(veiculos)].id, rota_id=rotas[(i-1)%len(rotas)].id,
                          data_prevista=hoje-timedelta(days=(i%4)-1),
                          data_entrega=hoje-timedelta(days=i%3) if i%4==0 else None,
                          status="ENTREGUE" if i%4==0 else ["EM TRANSITO","PENDENTE","EM TRANSITO"][i%3])
        db.session.add(entrega)
        db.session.flush()
        if i in (5, 9, 14, 18):
            db.session.add(Ocorrencia(entrega_id=entrega.id, tipo="ATRASO", descricao="Atraso identificado durante a operação.", data=hoje-timedelta(days=i%3), status="ABERTA"))
    db.session.commit()


@app.context_processor
def inject_globals():
    return {"today": date.today()}


@app.route("/")
def dashboard():
    """
    Dashboard principal da aplicação LOGIEXPRESS.

    Todos os indicadores apresentados nesta tela são
    calculados diretamente a partir dos dados do banco.
    """

    # =========================================================
    # OPERAÇÃO - PEDIDOS
    # =========================================================

    # Quantidade total de pedidos cadastrados
    total_pedidos = Pedido.query.count()

    # =========================================================
    # OPERAÇÃO - ENTREGAS
    # =========================================================

    # Busca todas as entregas cadastradas
    entregas = Entrega.query.all()

    # Quantidade total de entregas
    total_entregas = len(entregas)

    # Entregas concluídas
    entregues = sum(
        1
        for entrega in entregas
        if entrega.status == "ENTREGUE"
    )

    # Entregas em andamento
    em_andamento = sum(
        1
        for entrega in entregas
        if entrega.status != "ENTREGUE"
        and entrega.data_prevista >= date.today()
    )

    # Entregas atrasadas
    atrasadas = sum(
        1
        for entrega in entregas
        if entrega.data_prevista < date.today()
        and entrega.status != "ENTREGUE"
    )

    # Entregas consideradas críticas:
    # mais de 2 dias de atraso
    criticas = sum(
        1
        for entrega in entregas
        if entrega.data_prevista < date.today() - timedelta(days=2)
        and entrega.status != "ENTREGUE"
    )

    # =========================================================
    # OPERAÇÃO - OCORRÊNCIAS
    # =========================================================

    # Quantidade de ocorrências ainda abertas
    ocorrencias = Ocorrencia.query.filter_by(
        status="ABERTA"
    ).count()

    # =========================================================
    # RECURSOS - CLIENTES
    # =========================================================

    clientes_ativos = Cliente.query.filter_by(
        ativo=True
    ).count()

    # =========================================================
    # RECURSOS - MOTORISTAS
    # =========================================================

    motoristas_ativos = Motorista.query.filter_by(
        ativo=True
    ).count()

    # =========================================================
    # RECURSOS - VEÍCULOS
    # =========================================================

    veiculos_ativos = Veiculo.query.filter_by(
        ativo=True
    ).count()

    # =========================================================
    # RECURSOS - TRANSPORTADORAS
    # =========================================================

    transportadoras_ativas = Transportadora.query.filter_by(
        ativo=True
    ).count()

    # =========================================================
    # INFRAESTRUTURA - ROTAS
    # =========================================================

    rotas_ativas = Rota.query.filter_by(
        ativa=True
    ).count()

    # =========================================================
    # INFRAESTRUTURA - CENTROS DE DISTRIBUIÇÃO
    # =========================================================

    centros_ativos = CentroDistribuicao.query.filter_by(
        ativo=True
    ).count()

    # =========================================================
    # ESTOQUE
    # =========================================================

    # Produtos cujo estoque está abaixo do estoque mínimo
    estoque_baixo = Produto.query.filter(
        Produto.estoque < Produto.estoque_minimo
    ).count()

    # =========================================================
    # GRÁFICO 1 - STATUS DAS ENTREGAS
    # =========================================================

    grafico_status_labels = [
        "Entregues",
        "Em andamento",
        "Atrasadas"
    ]

    grafico_status_valores = [
        entregues,
        em_andamento,
        atrasadas
    ]

    # =========================================================
    # GRÁFICO 2 - ENTREGAS POR MOTORISTA
    # =========================================================

    # Dicionário que armazenará:
    #
    # Nome do motorista -> quantidade de entregas
    entregas_por_motorista = {}

    for entrega in entregas:

        # Obtém o nome do motorista relacionado à entrega
        nome_motorista = entrega.motorista.nome

        # Se o motorista ainda não estiver no dicionário,
        # inicia sua quantidade em zero
        if nome_motorista not in entregas_por_motorista:
            entregas_por_motorista[nome_motorista] = 0

        # Soma uma entrega para o motorista
        entregas_por_motorista[nome_motorista] += 1

    # Separa os nomes dos motoristas
    grafico_motorista_labels = list(
        entregas_por_motorista.keys()
    )

    # Separa as quantidades de entregas
    grafico_motorista_valores = list(
        entregas_por_motorista.values()
    )

    # =========================================================
    # ENVIO DOS DADOS PARA O TEMPLATE
    # =========================================================

    return render_template(
        "dashboard.html",

        # -------------------------
        # Operação
        # -------------------------
        total_pedidos=total_pedidos,
        total_entregas=total_entregas,
        entregues=entregues,
        em_andamento=em_andamento,
        atrasadas=atrasadas,
        criticas=criticas,
        ocorrencias=ocorrencias,

        # -------------------------
        # Recursos
        # -------------------------
        clientes_ativos=clientes_ativos,
        motoristas_ativos=motoristas_ativos,
        veiculos_ativos=veiculos_ativos,
        transportadoras_ativas=transportadoras_ativas,

        # -------------------------
        # Infraestrutura
        # -------------------------
        rotas_ativas=rotas_ativas,
        centros_ativos=centros_ativos,
        estoque_baixo=estoque_baixo,

        # -------------------------
        # Gráfico de status
        # -------------------------
        grafico_status_labels=grafico_status_labels,
        grafico_status_valores=grafico_status_valores,

        # -------------------------
        # Gráfico por motorista
        # -------------------------
        grafico_motorista_labels=grafico_motorista_labels,
        grafico_motorista_valores=grafico_motorista_valores
    )

@app.route("/cadastros/<entity>")
def list_entity(entity):
    """
    Listagem genérica dos cadastros.

    Para Clientes, utilizamos o CRUD completo desenvolvido
    para a atividade do dia 29/09.
    """
    if entity == "clientes":
        return redirect(url_for("clientes_list"))

    if entity not in MODEL_MAP:
        return "Recurso não encontrado", 404
    model, title = MODEL_MAP[entity]
    records = model.query.order_by(model.id.desc()).all()
    return render_template("list.html", entity=entity, title=title, records=records, model=model)



# =========================================================
# CRUD COMPLETO DE CLIENTES
# =========================================================

@app.route("/clientes")
def clientes_list():
    """
    Lista todos os clientes cadastrados.

    Esta é a operação READ do CRUD.
    """
    clientes = Cliente.query.order_by(Cliente.id.desc()).all()

    return render_template(
        "clientes/list.html",
        clientes=clientes
    )


@app.route("/clientes/novo", methods=["GET", "POST"])
def clientes_novo():
    """
    Cadastra um novo cliente.

    Operação CREATE do CRUD.
    """
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        documento = request.form.get("documento", "").strip()
        cidade = request.form.get("cidade", "").strip()
        uf = request.form.get("uf", "").strip().upper()
        ativo = "ativo" in request.form

        # -------------------------------------------------
        # Validações básicas
        # -------------------------------------------------

        if not nome or not documento or not cidade or not uf:
            flash(
                "Preencha todos os campos obrigatórios.",
                "warning"
            )
            return render_template(
                "clientes/form.html",
                cliente=None
            )

        if len(uf) != 2 or not uf.isalpha():
            flash(
                "A UF deve possuir exatamente 2 letras.",
                "warning"
            )
            return render_template(
                "clientes/form.html",
                cliente=None
            )

        # -------------------------------------------------
        # Verifica se o documento já está cadastrado
        # -------------------------------------------------

        cliente_existente = Cliente.query.filter_by(
            documento=documento
        ).first()

        if cliente_existente:
            flash(
                "Já existe um cliente cadastrado com este documento.",
                "danger"
            )
            return render_template(
                "clientes/form.html",
                cliente=None
            )

        try:
            cliente = Cliente(
                nome=nome,
                documento=documento,
                cidade=cidade,
                uf=uf,
                ativo=ativo
            )

            db.session.add(cliente)
            db.session.commit()

            flash(
                "Cliente cadastrado com sucesso.",
                "success"
            )

            return redirect(url_for("clientes_list"))

        except Exception as exc:
            db.session.rollback()

            flash(
                f"Não foi possível cadastrar o cliente: {exc}",
                "danger"
            )

    return render_template(
        "clientes/form.html",
        cliente=None
    )


@app.route("/clientes/<int:cliente_id>")
def clientes_view(cliente_id):
    """
    Exibe os detalhes de um cliente.

    Operação READ - visualização individual.
    """
    cliente = db.get_or_404(Cliente, cliente_id)

    return render_template(
        "clientes/view.html",
        cliente=cliente
    )


@app.route("/clientes/<int:cliente_id>/editar", methods=["GET", "POST"])
def clientes_editar(cliente_id):
    """
    Edita os dados de um cliente.

    Operação UPDATE do CRUD.
    """
    cliente = db.get_or_404(Cliente, cliente_id)

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        documento = request.form.get("documento", "").strip()
        cidade = request.form.get("cidade", "").strip()
        uf = request.form.get("uf", "").strip().upper()
        ativo = "ativo" in request.form

        # -------------------------------------------------
        # Validações
        # -------------------------------------------------

        if not nome or not documento or not cidade or not uf:
            flash(
                "Preencha todos os campos obrigatórios.",
                "warning"
            )
            return render_template(
                "clientes/form.html",
                cliente=cliente
            )

        if len(uf) != 2 or not uf.isalpha():
            flash(
                "A UF deve possuir exatamente 2 letras.",
                "warning"
            )
            return render_template(
                "clientes/form.html",
                cliente=cliente
            )

        # -------------------------------------------------
        # Verifica documento duplicado
        # -------------------------------------------------

        cliente_existente = Cliente.query.filter(
            Cliente.documento == documento,
            Cliente.id != cliente.id
        ).first()

        if cliente_existente:
            flash(
                "Outro cliente já utiliza este documento.",
                "danger"
            )
            return render_template(
                "clientes/form.html",
                cliente=cliente
            )

        try:
            cliente.nome = nome
            cliente.documento = documento
            cliente.cidade = cidade
            cliente.uf = uf
            cliente.ativo = ativo

            db.session.commit()

            flash(
                "Cliente atualizado com sucesso.",
                "success"
            )

            return redirect(
                url_for(
                    "clientes_view",
                    cliente_id=cliente.id
                )
            )

        except Exception as exc:
            db.session.rollback()

            flash(
                f"Não foi possível atualizar o cliente: {exc}",
                "danger"
            )

    return render_template(
        "clientes/form.html",
        cliente=cliente
    )


@app.route("/clientes/<int:cliente_id>/excluir", methods=["POST"])
def clientes_excluir(cliente_id):
    """
    Exclui um cliente.

    Operação DELETE do CRUD.

    Regra de negócio:
    um cliente que possui pedidos não pode ser excluído.
    """
    cliente = db.get_or_404(Cliente, cliente_id)

    # -----------------------------------------------------
    # REGRA DE NEGÓCIO
    # -----------------------------------------------------
    # Verificamos se existem pedidos relacionados ao cliente.
    # Se existir pelo menos um pedido, a exclusão é bloqueada.

    quantidade_pedidos = Pedido.query.filter_by(
        cliente_id=cliente.id
    ).count()

    if quantidade_pedidos > 0:
        flash(
            "Não é possível excluir este cliente porque "
            f"ele possui {quantidade_pedidos} pedido(s) relacionado(s).",
            "warning"
        )

        return redirect(
            url_for(
                "clientes_view",
                cliente_id=cliente.id
            )
        )

    try:
        db.session.delete(cliente)
        db.session.commit()

        flash(
            "Cliente excluído com sucesso.",
            "success"
        )

    except Exception as exc:
        db.session.rollback()

        flash(
            f"Não foi possível excluir o cliente: {exc}",
            "danger"
        )

    return redirect(url_for("clientes_list"))


@app.route("/cadastros/<entity>/novo", methods=["GET", "POST"])
def new_entity(entity):
    """
    Formulário genérico para inclusão de registros.

    Clientes possui um CRUD próprio e, por isso,
    qualquer acesso ao endereço genérico é direcionado
    para o cadastro completo de clientes.
    """
    if entity == "clientes":
        return redirect(url_for("clientes_novo"))

    if entity not in MODEL_MAP:
        return "Recurso não encontrado", 404
    model, title = MODEL_MAP[entity]
    if request.method == "POST":
        try:
            obj = build_entity_from_form(entity, model)
            db.session.add(obj)
            db.session.commit()
            flash(f"{title[:-1] if title.endswith('s') else title} cadastrado com sucesso.", "success")
            return redirect(url_for("list_entity", entity=entity))
        except Exception as exc:
            db.session.rollback()
            flash(f"Não foi possível salvar: {exc}", "danger")
    return render_template("form.html", entity=entity, title=title, record=None)


def build_entity_from_form(entity, model, record=None):
    data = request.form
    if entity == "clientes":
        return Cliente(nome=data["nome"], documento=data["documento"], cidade=data["cidade"], uf=data["uf"], ativo="ativo" in data)
    if entity == "motoristas":
        return Motorista(nome=data["nome"], cnh=data["cnh"], telefone=data.get("telefone"), ativo="ativo" in data)
    if entity == "veiculos":
        return Veiculo(placa=data["placa"], modelo=data["modelo"], tipo=data["tipo"], capacidade_kg=float(data["capacidade_kg"]), ativo="ativo" in data)
    if entity == "produtos":
        return Produto(codigo=data["codigo"], descricao=data["descricao"], categoria=data["categoria"], estoque=int(data["estoque"]), estoque_minimo=int(data["estoque_minimo"]), ativo="ativo" in data)
    if entity == "centros":
        return CentroDistribuicao(nome=data["nome"], cidade=data["cidade"], uf=data["uf"], capacidade=int(data["capacidade"]), ativo="ativo" in data)
    if entity == "transportadoras":
        return Transportadora(razao_social=data["razao_social"], cnpj=data["cnpj"], cidade=data["cidade"], uf=data["uf"], ativo="ativo" in data)
    if entity == "pedidos":
        return Pedido(numero=data["numero"], cliente_id=int(data["cliente_id"]), data_pedido=date.fromisoformat(data["data_pedido"]), valor=Decimal(data["valor"]), status=data["status"])
    if entity == "rotas":
        return Rota(origem=data["origem"], destino=data["destino"], distancia_km=float(data["distancia_km"]), tempo_estimado_h=float(data["tempo_estimado_h"]), ativa="ativa" in data)
    if entity == "entregas":
        return Entrega(pedido_id=int(data["pedido_id"]), motorista_id=int(data["motorista_id"]), veiculo_id=int(data["veiculo_id"]), rota_id=int(data["rota_id"]) if data.get("rota_id") else None, data_prevista=date.fromisoformat(data["data_prevista"]), data_entrega=date.fromisoformat(data["data_entrega"]) if data.get("data_entrega") else None, status=data["status"])
    if entity == "ocorrencias":
        return Ocorrencia(entrega_id=int(data["entrega_id"]), tipo=data["tipo"], descricao=data["descricao"], data=date.fromisoformat(data["data"]), status=data["status"])
    raise ValueError("Entidade não suportada")


@app.route("/relatorios")
def reports():
    motoristas = []
    for m in Motorista.query.all():
        entregas = Entrega.query.filter_by(motorista_id=m.id).all()
        total = len(entregas)
        ok = sum(1 for e in entregas if e.status == "ENTREGUE")
        motoristas.append({"nome": m.nome, "total": total, "entregues": ok, "taxa": round(ok/total*100,1) if total else 0})
    return render_template("reports.html", motoristas=motoristas)


# =========================================================
# PÁGINA DE INSTRUÇÕES - 29/09
# =========================================================

@app.route("/instrucoes")
def instrucoes():
    """
    Exibe as instruções da atividade do dia 29/09.

    Nesta etapa, o aluno irá:

    - acessar o GitHub;
    - acessar o repositório LOGIEXPRESS;
    - abrir o GitHub Codespaces;
    - conhecer o ambiente de desenvolvimento;
    - verificar os arquivos do projeto;
    - instalar as dependências;
    - executar a aplicação Flask;
    - acessar o sistema pelo navegador;
    - navegar pelas funcionalidades do LOGIEXPRESS;
    - compreender a estrutura básica da aplicação.

    Os procedimentos de desenvolvimento com Git,
    criação de branches, commits, push e Pull Request
    serão apresentados nas instruções do dia 30/09.
    """

    return render_template("instrucoes.html")

# =========================================================
# CONTROLE DE SLA DE ENTREGAS
# =========================================================

@app.route("/sla")
def controle_sla():
    hoje = date.today()
    todas_entregas = Entrega.query.order_by(Entrega.data_prevista.asc()).all()

    relatorio_sla = []

    for entrega in todas_entregas:
        # 1. Se já foi entregue
        if entrega.status == "ENTREGUE":
            if entrega.data_entrega and entrega.data_entrega > entrega.data_prevista:
                situacao = "Entregue com Atraso"
                classe_css = "warning"
            else:
                situacao = "Entregue no Prazo"
                classe_css = "success"

        # 2. Se ainda não foi entregue (em trânsito ou pendente)
        else:
            if entrega.data_prevista < hoje:
                dias_atraso = (hoje - entrega.data_prevista).days
                if dias_atraso > 2:
                    situacao = f"Crítico ({dias_atraso} dias de atraso)"
                    classe_css = "danger"
                else:
                    situacao = f"Atrasado ({dias_atraso} dia(s))"
                    classe_css = "warning"
            else:
                situacao = "No Prazo"
                classe_css = "info"

        relatorio_sla.append({
            "entrega": entrega,
            "situacao": situacao,
            "classe_css": classe_css
        })

    return render_template("sla.html", entregas=relatorio_sla)


# =========================================================
# DOCUMENTAÇÃO E ATIVIDADES
# =========================================================


@app.route("/documentacao")
def documentacao():
    """
    Menu principal de documentação.

    O menu pode apontar para este endpoint sem depender
    diretamente do nome de um template.
    A documentação técnica é a página de entrada.
    """
    return redirect(url_for("documentacao_tecnica"))


@app.route("/documentacao-tecnica")
def documentacao_tecnica():
    """Exibe a documentação técnica da versão atual do LOGIEXPRESS."""
    return render_template("documentacao_tecnica.html")


@app.route("/documentacao-auxiliar")
def documentacao_auxiliar():
    """Exibe os conceitos fundamentais para acompanhar o projeto."""
    return render_template("documentacao_auxiliar.html")


@app.route("/roteiro-desenvolvimento-3009")
def roteiro_desenvolvimento_3009():
    """Exibe o roteiro completo da prática de desenvolvimento do dia 30/09."""
    return render_template("roteiro_desenvolvimento_3009.html")


@app.route("/guia-git")
def guia_git():
    """Atalho para o guia de Git e integração."""
    return redirect(url_for("guia_git_integracao"))


@app.route("/guia-git-integracao")
def guia_git_integracao():
    """Exibe o fluxo Git, branches, commits, Pull Requests e integração."""
    return render_template("guia_git_integracao.html")


@app.route("/kanban-produto")
def kanban_produto():
    """Atalho para o Kanban do produto."""
    return redirect(url_for("kanban"))


@app.route("/kanban")
def kanban():
    """Exibe o fluxo Kanban utilizado no desenvolvimento colaborativo."""
    return render_template("kanban.html")


@app.route("/exercicios")
def exercicios():
    """
    Atalho oficial para os 20 exercícios da prática.
    """
    return redirect(url_for("desafios"))


@app.route("/desafios")
def desafios():
    """Exibe os 20 exercícios que formam o backlog do produto."""
    return render_template("desafios.html")


@app.route("/atividades-3009")
def atividades_3009():
    """Mantém compatibilidade com o endereço antigo."""
    return redirect(url_for("desafios"))


@app.route("/instrucoes-3009")
def instrucoes_3009():
    """Atalho para as instruções do dia 29/09."""
    return redirect(url_for("instrucoes"))


@app.route("/health")
def health():
    return {"status": "ok", "application": "LOGIEXPRESS", "database": "connected"}


with app.app_context():
    db.create_all()
    seed_data()


if __name__ == "__main__":
    app.run(debug=True)
