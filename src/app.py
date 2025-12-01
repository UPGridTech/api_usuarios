import os
import logging
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

# ---------------------------
# OpenTelemetry / SigNoz
# ---------------------------
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

# ---------------------------
# CONFIGURAÇÃO APP
# ---------------------------
app = Flask(__name__, static_folder="static", template_folder="static")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

SIGNOZ_OTLP_URL = os.getenv("SIGNOZ_OTLP_URL")
SIGNOZ_INGEST_KEY = os.getenv("SIGNOZ_KEY2")

# ---------------------------
# LOGS ESTRUTURADOS
# ---------------------------
logger = logging.getLogger("supermercado")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(json.dumps({
    "time": "%(asctime)s",
    "level": "%(levelname)s",
    "message": "%(message)s"
}))
handler.setFormatter(formatter)
logger.addHandler(handler)

# ---------------------------
# OpenTelemetry - TRACE
# ---------------------------
resource = Resource.create({SERVICE_NAME: "supermercado-app"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer_provider = trace.get_tracer_provider()

otlp_exporter = OTLPSpanExporter(
    endpoint=SIGNOZ_OTLP_URL,
    insecure=False,
    headers=(("x-signoz-ingest-key", SIGNOZ_INGEST_KEY),)
)
tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

# ---------------------------
# MODELOS
# ---------------------------
class Categoria(db.Model):
    __tablename__ = "categorias"
    id = db.Column(db.String, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)

class Produto(db.Model):
    __tablename__ = "produtos"
    id = db.Column(db.String, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    estoque = db.Column(db.Integer, nullable=False)
    categoria_id = db.Column(db.String, db.ForeignKey("categorias.id"), nullable=True)

# ---------------------------
# FRONTEND
# ---------------------------
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

# ---------------------------
# API PRODUTOS
# ---------------------------
@app.route("/produtos", methods=["GET"])
def get_produtos():
    produtos = Produto.query.all()
    logger.info("Listando produtos")
    return jsonify([
        {
            "id": str(p.id),
            "nome": p.nome,
            "preco": p.preco,
            "estoque": p.estoque,
            "categoria_id": str(p.categoria_id) if p.categoria_id else None
        }
        for p in produtos
    ])

@app.route("/produtos", methods=["POST"])
def create_produto():
    data = request.json
    novo_id = db.session.execute(text("SELECT gen_random_uuid()")).scalar()

    p = Produto(
        id=str(novo_id),
        nome=data["nome"],
        preco=data["preco"],
        estoque=data["estoque"],
        categoria_id=str(data["categoria_id"]) if data.get("categoria_id") else None
    )

    db.session.add(p)
    db.session.commit()

    logger.info(f"Produto criado: {p.nome}")
    return jsonify({"message": "Produto criado", "id": p.id})

@app.route("/produtos/<id>", methods=["PUT"])
def update_produto(id):
    produto = Produto.query.get(str(id))
    if not produto:
        return jsonify({"error": "Produto não encontrado"}), 404

    data = request.json
    produto.nome = data["nome"]
    produto.preco = data["preco"]
    produto.estoque = data["estoque"]
    produto.categoria_id = str(data["categoria_id"]) if data.get("categoria_id") else None

    db.session.commit()
    logger.info(f"Produto atualizado: {produto.nome}")
    return jsonify({"message": "Atualizado"})

@app.route("/produtos/<id>", methods=["DELETE"])
def delete_produto(id):
    produto = Produto.query.get(str(id))
    if not produto:
        return jsonify({"error": "Produto não encontrado"}), 404

    db.session.delete(produto)
    db.session.commit()
    logger.info(f"Produto deletado: {produto.nome}")
    return jsonify({"message": "Deletado"})

# ---------------------------
# API CATEGORIAS
# ---------------------------
@app.route("/categorias", methods=["GET"])
def get_categorias():
    categorias = Categoria.query.all()
    logger.info("Listando categorias")
    return jsonify([{"id": str(c.id), "nome": c.nome} for c in categorias])

# ---------------------------
# PROMETHEUS / METRICS
# ---------------------------
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    "/metrics": make_wsgi_app()
})

# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    with app.app_context():
        # Cria tabelas
        db.create_all()
        # Instrumenta Flask e SQLAlchemy dentro do app context
        FlaskInstrumentor().instrument_app(app)
        SQLAlchemyInstrumentor().instrument(engine=db.engine)

    logger.info("Servidor iniciado com OTel + SigNoz")
    app.run(host="0.0.0.0", port=80)
